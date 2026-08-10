"""统一搜索引擎 — 融合 8 个数据源

增强特性 (v3.5):
- DOI 优先去重 + 标题模糊去重
- URL 规范化去重 (去除追踪参数)
- 搜索结果加权合并 (按引擎可信度排序)
- per-source 超时控制 (默认 10s)
"""

import concurrent.futures
import re
from typing import List, Optional
from urllib.parse import urlparse, parse_qs, urlencode
from .sources.base import SearchEngine, PaperData
from .sources.openalex import OpenAlexSearch
from .sources.crossref import CrossRefSearch
from .sources.semantic_scholar import SemanticScholarSearch
from .sources.arxiv import ArxivSearch
from .sources.pubmed import PubMedSearch
from .sources.google_scholar import GoogleScholarSearch
from .sources.scopus import ScopusSearch
from .enricher import AbstractEnricher
from .scorer import sim_score
from .citation import format_gb

# 引擎可信度权重 (用于加权合并)
ENGINE_WEIGHTS = {
    "semantic_scholar": 1.0,   # 学术专用，最可信
    "openalex": 0.95,          # 200M+ 论文目录
    "crossref": 0.9,           # DOI 注册机构
    "arxiv": 0.85,             # 预印本，时效性强
    "pubmed": 0.9,             # 生物医学权威
    "google_scholar": 0.7,     # 覆盖广但质量参差
    "scopus": 0.85,            # 需 API key
}

# URL 追踪参数列表
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "msclkid", "dclid", "gbraid", "wbraid",
    "ref", "referrer", "source", "spm", "from", "suid",
    "_ga", "_gl", "mc_cid", "mc_eid", "oly_enc_id", "oly_anon_id",
}

# per-source 超时 (秒)
PER_SOURCE_TIMEOUT = 10


def _normalize_url(url: str) -> str:
    """URL 规范化：去除追踪参数、统一 scheme、去除末尾斜杠"""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        # 去除追踪参数
        qs = parse_qs(parsed.query, keep_blank_values=False)
        clean_qs = {k: v for k, v in qs.items() if k.lower() not in TRACKING_PARAMS}
        # 重建 URL
        clean = parsed._replace(
            query=urlencode(clean_qs, doseq=True),
            scheme="https",
            path=parsed.path.rstrip("/"),
        )
        return clean.geturl()
    except Exception:
        return url.lower().strip()


def _normalize_doi(doi: str) -> str:
    """DOI 规范化：去除前缀、统一小写"""
    if not doi:
        return ""
    doi = doi.strip().lower()
    # 去除常见前缀
    for prefix in ["https://doi.org/", "http://doi.org/", "doi:", "doi "]:
        if doi.startswith(prefix):
            doi = doi[len(prefix):]
    return doi.strip()


class UnifiedSearchEngine:
    """统一搜索引擎 — 并行搜索 + 去重 + 摘要补全 + 评分 + 引用格式化"""

    def __init__(self, config: dict | None = None):
        config = config or {}
        self.engines: dict[str, SearchEngine] = {}
        self.enricher = AbstractEnricher(email=config.get("openalex_email", ""))

        # 初始化所有可用引擎
        self.engines["openalex"] = OpenAlexSearch(email=config.get("openalex_email", ""))
        self.engines["crossref"] = CrossRefSearch()
        self.engines["semantic_scholar"] = SemanticScholarSearch()
        self.engines["arxiv"] = ArxivSearch()
        self.engines["pubmed"] = PubMedSearch()

        # 可选引擎
        try:
            self.engines["google_scholar"] = GoogleScholarSearch()
        except Exception:
            pass

        scopus_key = config.get("scopus_api_key", "")
        if scopus_key:
            self.engines["scopus"] = ScopusSearch(api_key=scopus_key)

    def search(self, query: str, sources: list[str] | None = None,
               max_results: int = 50, enrich: bool = True) -> List[PaperData]:
        """统一搜索入口"""
        engines = self._select_engines(sources)
        if not engines:
            return []

        # 并行搜索 (per-source 超时)
        all_papers: List[PaperData] = []
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(engines)))
        try:
            futures = {
                executor.submit(self._search_one, engine, query, max_results): name
                for name, engine in engines.items()
            }
            # as_completed 总超时 = per-source 超时 + 5s 余量，防止无限阻塞
            total_timeout = PER_SOURCE_TIMEOUT + 5
            try:
                for future in concurrent.futures.as_completed(futures, timeout=total_timeout):
                    name = futures[future]
                    try:
                        papers = future.result(timeout=2)
                        all_papers.extend(papers)
                    except concurrent.futures.TimeoutError:
                        print(f"[TIMEOUT] {name} 搜索超时 ({PER_SOURCE_TIMEOUT}s)", flush=True)
                    except Exception as e:
                        print(f"[ERROR] {name} 搜索异常: {e}", flush=True)
            except concurrent.futures.TimeoutError:
                # 总超时：取消未完成的 future
                unfinished = [f for f in futures if not f.done()]
                for f in unfinished:
                    f.cancel()
                print(f"[TIMEOUT] 搜索总超时 ({total_timeout}s)，{len(unfinished)} 个源未完成，已取消", flush=True)
        finally:
            # A context manager calls shutdown(wait=True), which defeats the
            # timeout above when a source is still blocked in network I/O.
            executor.shutdown(wait=False, cancel_futures=True)

        # 去重 (DOI 优先 + 标题模糊 + URL 规范化)
        unique = self._deduplicate(all_papers)

        # Sort and cap before enrichment.  Previously every source could return
        # max_results and all deduplicated rows were enriched serially.
        unique = self._weighted_sort(unique)
        unique = unique[:max_results]

        # OpenAlex enrichment is intentionally limited to the highest-ranked
        # results so a few missing abstracts cannot dominate request latency.
        if enrich and unique:
            enrich_count = min(10, len(unique))
            unique[:enrich_count] = self.enricher.batch_enrich(unique[:enrich_count])

        # 生成引用格式
        for i, paper in enumerate(unique):
            paper_dict = paper.to_dict()
            paper_dict["paper_type"] = paper.paper_type
            paper.citation = format_gb(paper_dict, i + 1)

        return unique

    def _select_engines(self, sources: list[str] | None) -> dict[str, SearchEngine]:
        if not sources:
            return dict(self.engines)
        # 小写匹配，忽略大小写
        result = {}
        for name in sources:
            key = name.lower().strip()
            if key in self.engines:
                result[key] = self.engines[key]
        return result

    def _search_one(self, engine: SearchEngine, query: str, max_results: int) -> List[PaperData]:
        return engine.search(query, max_results)

    def _deduplicate(self, papers: List[PaperData]) -> List[PaperData]:
        """三阶段去重：DOI 精确 → 标题模糊 → URL 规范化"""
        if not papers:
            return []

        # 阶段 1: DOI 精确去重
        doi_seen: dict[str, PaperData] = {}
        no_doi: List[PaperData] = []

        for paper in papers:
            doi = _normalize_doi(paper.doi)
            if doi:
                if doi not in doi_seen:
                    doi_seen[doi] = paper
                # DOI 重复时保留来源更可信的
                elif ENGINE_WEIGHTS.get(paper.source, 0.5) > ENGINE_WEIGHTS.get(doi_seen[doi].source, 0.5):
                    doi_seen[doi] = paper
            else:
                no_doi.append(paper)

        deduped = list(doi_seen.values())

        # 阶段 2: 标题模糊去重 (对无 DOI 的论文)
        title_seen: dict[str, PaperData] = {}
        for paper in no_doi:
            norm = "".join(c for c in paper.title.lower().strip() if c.isalnum() or c.isspace())
            if not norm:
                continue
            if norm not in title_seen:
                title_seen[norm] = paper
            elif ENGINE_WEIGHTS.get(paper.source, 0.5) > ENGINE_WEIGHTS.get(title_seen[norm].source, 0.5):
                title_seen[norm] = paper

        deduped.extend(title_seen.values())

        # 阶段 3: URL 规范化去重
        url_seen: dict[str, PaperData] = {}
        final: List[PaperData] = []
        for paper in deduped:
            url = _normalize_url(paper.url)
            if url:
                if url not in url_seen:
                    url_seen[url] = paper
                    final.append(paper)
            else:
                final.append(paper)

        return final

    def _weighted_sort(self, papers: List[PaperData]) -> List[PaperData]:
        """按引擎可信度加权排序"""
        def sort_key(p: PaperData) -> float:
            base = getattr(p, "_score", 0.0)
            weight = ENGINE_WEIGHTS.get(p.source, 0.5)
            return base * 0.7 + weight * 0.3

        papers.sort(key=sort_key, reverse=True)
        return papers

    def score_results(self, query: str, papers: List[PaperData]) -> List[PaperData]:
        """对搜索结果进行相似度评分并排序"""
        for paper in papers:
            paper._score = sim_score(query, paper.title)
        papers.sort(key=lambda p: getattr(p, "_score", 0), reverse=True)
        return papers
