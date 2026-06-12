"""OpenAlex 搜索引擎"""

import requests
from typing import List
from .base import SearchEngine, PaperData


class OpenAlexSearch(SearchEngine):
    """OpenAlex API 搜索"""

    BASE_URL = "https://api.openalex.org/works"

    def __init__(self, email: str = ""):
        super().__init__("openalex")
        self.email = email
        self.min_request_interval = 0.3

    def search(self, query: str, max_results: int = 10) -> List[PaperData]:
        self._rate_limit()
        headers = {"User-Agent": f"mailto:{self.email}"} if self.email else {"User-Agent": "Mozilla/5.0"}
        params = {
            "search": query,
            "per_page": min(max_results, 50),
            "sort": "relevance_score:desc",
        }

        try:
            resp = requests.get(self.BASE_URL, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"❌ OpenAlex 搜索错误: {e}")
            return []

        papers = []
        for item in data.get("results", []):
            paper = self._parse(item)
            if paper:
                papers.append(paper)
        return papers

    def _parse(self, item: dict) -> PaperData | None:
        title = (item.get("title") or "").strip()
        if not title:
            return None

        # 作者
        authors = []
        for auth in (item.get("authorships") or [])[:5]:
            name = auth.get("author", {}).get("display_name", "")
            if name:
                authors.append(name)

        # 年份
        year = self._extract_year(item.get("publication_date", ""))

        # DOI
        doi = (item.get("doi") or "").replace("https://doi.org/", "")

        # 摘要（从倒排索引重建）
        abstract = self._reconstruct_abstract(item.get("abstract_inverted_index"))

        # 期刊
        loc = item.get("primary_location") or {}
        source = loc.get("source") or {}
        journal = source.get("display_name") or ""

        # URL
        url = item.get("id", "")

        # 类型
        ptype = item.get("type", "journal-article")

        return PaperData(
            title=title, authors=authors, year=year, doi=doi,
            journal=journal, abstract=abstract or "", source="openalex",
            url=url, paper_type=ptype,
            citation_count=item.get("cited_by_count", 0),
        )

    @staticmethod
    def _reconstruct_abstract(inverted_index: dict | None) -> str | None:
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
