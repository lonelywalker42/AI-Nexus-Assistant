"""统一搜索引擎 — 融合 8 个数据源"""

import concurrent.futures
from typing import List, Optional
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

        # 并行搜索
        all_papers: List[PaperData] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                executor.submit(self._search_one, engine, query, max_results): name
                for name, engine in engines.items()
            }
            for future in concurrent.futures.as_completed(futures):
                name = futures[future]
                try:
                    papers = future.result()
                    all_papers.extend(papers)
                except Exception as e:
                    print(f"❌ {name} 搜索异常: {e}")

        # 去重
        unique = self._deduplicate(all_papers)

        # 摘要补全
        if enrich and unique:
            unique = self.enricher.batch_enrich(unique)

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
        """标题归一化去重"""
        seen: set[str] = set()
        unique: List[PaperData] = []
        for paper in papers:
            norm = "".join(c for c in paper.title.lower().strip() if c.isalnum() or c.isspace())
            if norm and norm not in seen:
                seen.add(norm)
                unique.append(paper)
        return unique

    def score_results(self, query: str, papers: List[PaperData]) -> List[PaperData]:
        """对搜索结果进行相似度评分并排序"""
        for paper in papers:
            paper._score = sim_score(query, paper.title)
        papers.sort(key=lambda p: getattr(p, "_score", 0), reverse=True)
        return papers
