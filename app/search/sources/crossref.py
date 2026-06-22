"""CrossRef 搜索引擎"""

import requests
from typing import List
from .base import SearchEngine, PaperData


class CrossRefSearch(SearchEngine):
    """CrossRef API 搜索"""

    BASE_URL = "https://api.crossref.org/works"

    def __init__(self):
        super().__init__("crossref")
        self.min_request_interval = 1.0

    def search(self, query: str, max_results: int = 10) -> List[PaperData]:
        self._rate_limit()
        params = {
            "query": query,
            "rows": min(max_results, 50),
            "sort": "relevance",
        }
        headers = {"User-Agent": "AI-Nexus-Assistant/0.1 (mailto:user@example.com)"}
        try:
            resp = requests.get(self.BASE_URL, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[ERROR] CrossRef 搜索错误: {e}")
            return []

        papers = []
        for item in data.get("message", {}).get("items", []):
            paper = self._parse(item)
            if paper:
                papers.append(paper)
        return papers

    def _parse(self, item: dict) -> PaperData | None:
        title_list = item.get("title", [])
        title = title_list[0].strip() if title_list else ""
        if not title:
            return None

        authors = []
        for auth in (item.get("author") or [])[:5]:
            name = f"{auth.get('given', '')} {auth.get('family', '')}".strip()
            if name:
                authors.append(name)

        year = 0
        for date_field in ["published-print", "published-online", "created"]:
            dp = item.get(date_field, {}).get("date-parts", [[]])
            if dp and dp[0] and dp[0][0]:
                year = dp[0][0]
                break

        doi = item.get("DOI", "")
        journal_list = item.get("container-title", [])
        journal = journal_list[0] if journal_list else ""
        abstract = item.get("abstract", "").strip()
        url = item.get("URL", "")

        ptype_map = {"journal-article": "期刊文章", "proceedings-article": "会议论文", "book-chapter": "书籍章节"}
        ptype = ptype_map.get(item.get("type", ""), "未知")

        return PaperData(
            title=title, authors=authors, year=year, doi=doi,
            journal=journal, abstract=abstract, source="crossref",
            url=url, paper_type=ptype,
            citation_count=item.get("is-referenced-by-count", 0),
        )
