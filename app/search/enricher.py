"""摘要补充器 — 通过 OpenAlex 补全缺失摘要，移植自 ai-researchers"""

import time
import requests
from typing import List, Optional
from .sources.base import PaperData


def reconstruct_abstract(inverted_index: dict) -> Optional[str]:
    """将 OpenAlex 倒排索引摘要还原为纯文本"""
    if not inverted_index:
        return None
    try:
        max_idx = max(max(indices) for indices in inverted_index.values() if indices)
        words = [""] * (max_idx + 1)
        for word, indices in inverted_index.items():
            for i in indices:
                words[i] = word
        return " ".join(words)
    except Exception:
        return None


def fetch_abstract_from_openalex(doi: str, email: str = "") -> Optional[str]:
    """通过 DOI 向 OpenAlex 请求摘要"""
    if not doi or doi.startswith("arXiv:"):
        return None

    url = f"https://api.openalex.org/works/doi:{doi}"
    headers = {"User-Agent": f"mailto:{email}"} if email else {"User-Agent": "Mozilla/5.0"}

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            abstract = reconstruct_abstract(data.get("abstract_inverted_index"))
            if abstract:
                return abstract
            return data.get("abstract")
        return None
    except Exception:
        return None


class AbstractEnricher:
    """摘要补充器"""

    def __init__(self, email: str = "", rate_limit: float = 0.2):
        self.email = email
        self.rate_limit = rate_limit
        self.last_request_time = 0.0

    def batch_enrich(self, papers: List[PaperData], batch_size: int = 10) -> List[PaperData]:
        """批量补充摘要"""
        enriched = []
        for i in range(0, len(papers), batch_size):
            batch = papers[i:i + batch_size]
            for paper in batch:
                if not paper.abstract or paper.abstract in ["", "暂无", "N/A"]:
                    if paper.doi and not paper.doi.startswith("arXiv:"):
                        abstract = self._fetch_with_limit(paper.doi)
                        if abstract and abstract not in ["OpenAlex未收录", "OpenAlex中无摘要"]:
                            paper.abstract = abstract
                enriched.append(paper)
            if i + batch_size < len(papers):
                time.sleep(1)
        return enriched

    def _fetch_with_limit(self, doi: str) -> Optional[str]:
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request_time = time.time()
        return fetch_abstract_from_openalex(doi, self.email)
