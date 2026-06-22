"""Semantic Scholar 搜索引擎"""

import requests
from typing import List
from .base import SearchEngine, PaperData


class SemanticScholarSearch(SearchEngine):
    """Semantic Scholar API 搜索"""

    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

    def __init__(self):
        super().__init__("semantic_scholar")
        self.min_request_interval = 1.0

    def search(self, query: str, max_results: int = 10) -> List[PaperData]:
        self._rate_limit()
        params = {
            "query": query,
            "limit": min(max_results, 100),
            "fields": "title,authors,year,abstract,journal,externalIds,url,citationCount,publicationTypes",
        }
        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[ERROR] Semantic Scholar 搜索错误: {e}")
            return []

        papers = []
        for item in data.get("data", []):
            paper = self._parse(item)
            if paper:
                papers.append(paper)
        return papers

    def _parse(self, item: dict) -> PaperData | None:
        title = (item.get("title") or "").strip()
        if not title:
            return None

        authors = [a.get("name", "") for a in (item.get("authors") or [])[:5]]
        year = item.get("year") or 0
        ext = item.get("externalIds") or {}
        doi = ext.get("DOI", "")
        abstract = item.get("abstract") or ""
        journal_data = item.get("journal") or {}
        journal = journal_data.get("name", "")
        url = item.get("url", "")

        pub_types = item.get("publicationTypes") or []
        ptype = "期刊文章" if "JournalArticle" in pub_types else "会议论文" if "Conference" in pub_types else "未知"

        return PaperData(
            title=title, authors=authors, year=year, doi=doi,
            journal=journal, abstract=abstract, source="semantic_scholar",
            url=url, paper_type=ptype,
            citation_count=item.get("citationCount", 0),
        )
