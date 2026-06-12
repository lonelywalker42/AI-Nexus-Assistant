"""Google Scholar 搜索引擎 — 移植自 ai-researchers"""

import datetime
from typing import List
from .base import SearchEngine, PaperData


class GoogleScholarSearch(SearchEngine):
    """Google Scholar 搜索（通过 scholarly 库）"""

    def __init__(self, openalex_email: str = ""):
        super().__init__("google_scholar")
        self.openalex_email = openalex_email
        self.min_request_interval = 2.0

    def search(self, query: str, max_results: int = 10) -> List[PaperData]:
        try:
            from scholarly import scholarly
        except ImportError:
            print("❌ 未安装 scholarly 库")
            return []

        self._rate_limit()
        try:
            search_query = scholarly.search_pubs(query)
            papers = []
            count = 0
            while count < max_results:
                try:
                    pub = next(search_query)
                    paper = self._parse(pub)
                    if paper:
                        papers.append(paper)
                        count += 1
                    self._rate_limit()
                except StopIteration:
                    break
                except Exception:
                    continue
            return papers
        except Exception as e:
            print(f"❌ Google Scholar 搜索错误: {e}")
            return []

    def _parse(self, pub: dict) -> PaperData | None:
        title = (pub.get("bib", {}).get("title", "")).strip()
        if not title:
            return None

        authors = pub.get("bib", {}).get("author", [])
        if isinstance(authors, str):
            authors = [authors]
        elif not isinstance(authors, list):
            authors = []

        year_str = pub.get("bib", {}).get("pub_year", "") or pub.get("bib", {}).get("year", "")
        try:
            year = int(year_str) if year_str and str(year_str).isdigit() else self._extract_year(str(year_str))
        except (ValueError, TypeError):
            year = datetime.datetime.now().year

        journal = pub.get("bib", {}).get("venue", "") or pub.get("bib", {}).get("journal", "")
        abstract = pub.get("bib", {}).get("abstract", "")
        doi = ""
        url = pub.get("pub_url", "") or pub.get("eprint_url", "")

        ptype = "期刊文章"
        jl = journal.lower()
        if "arxiv" in jl or "preprint" in jl:
            ptype = "预印本"
        elif any(x in jl for x in ["conference", "proc.", "symposium"]):
            ptype = "会议论文"

        return PaperData(
            title=title, authors=authors, year=year, doi=doi,
            journal=journal, abstract=abstract, source="google_scholar",
            url=url, paper_type=ptype,
        )
