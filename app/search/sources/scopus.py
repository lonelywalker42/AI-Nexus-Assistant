"""Scopus 搜索引擎 — 移植自 ai-researchers"""

import requests
import time
from typing import List
from .base import SearchEngine, PaperData


class ScopusSearch(SearchEngine):
    """Scopus API 搜索"""

    BASE_URL = "https://api.elsevier.com/content/search/scopus"

    def __init__(self, api_key: str, openalex_email: str = ""):
        super().__init__("scopus")
        self.api_key = api_key
        self.openalex_email = openalex_email
        self.min_request_interval = 0.5

    def search(self, query: str, max_results: int = 10) -> List[PaperData]:
        self._rate_limit()
        headers = {"X-ELS-APIKey": self.api_key, "Accept": "application/json"}
        params = {"query": query, "count": min(max_results, 25), "view": "STANDARD"}

        try:
            resp = requests.get(self.BASE_URL, headers=headers, params=params, timeout=15)
            if resp.status_code == 400:
                print(f"❌ Scopus 请求参数错误")
                return []
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"❌ Scopus 搜索错误: {e}")
            return []

        papers = []
        for item in data.get("search-results", {}).get("entry", []):
            paper = self._parse(item)
            if paper:
                papers.append(paper)
        return papers

    def _parse(self, item: dict) -> PaperData | None:
        title = (item.get("dc:title", "")).strip()
        if not title or title == "N/A":
            return None

        author_field = item.get("dc:creator", "Unknown")
        if isinstance(author_field, str):
            authors = [author_field.strip()]
        else:
            authors = ["Unknown"]

        year = self._extract_year(item.get("prism:coverDate", ""))
        doi = (item.get("prism:doi", "") or "")
        if doi == "N/A":
            doi = ""
        journal = item.get("prism:publicationName", "") or ""
        abstract = ""

        url = ""
        for link in item.get("link", []):
            if link.get("@ref") == "scopus":
                url = link.get("@href", "")
                break

        subtype = (item.get("subtype", "") or "").lower()
        type_map = {"ar": "期刊文章", "cp": "会议论文", "re": "综述"}
        ptype = type_map.get(subtype, "未知")

        time.sleep(0.2)
        return PaperData(
            title=title, authors=authors, year=year, doi=doi,
            journal=journal, abstract=abstract, source="scopus",
            url=url, paper_type=ptype,
        )
