"""arXiv 搜索引擎 — 移植自 ai-researchers"""

import datetime
from typing import List
from .base import SearchEngine, PaperData


class ArxivSearch(SearchEngine):
    """arXiv API 搜索"""

    def __init__(self):
        super().__init__("arxiv")
        self.min_request_interval = 1.0

    def search(self, query: str, max_results: int = 10) -> List[PaperData]:
        self._rate_limit()
        try:
            import arxiv
        except ImportError:
            print("[ERROR] 未安装 arxiv 库")
            return []

        try:
            client = arxiv.Client()
            search = arxiv.Search(query=query, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance)
            papers = []
            for result in client.results(search):
                paper = self._parse(result)
                if paper:
                    papers.append(paper)
            return papers
        except Exception as e:
            print(f"[ERROR] arXiv 搜索错误: {e}")
            return []

    def _parse(self, result) -> PaperData | None:
        import arxiv as arxiv_mod
        title = result.title.strip()
        if not title:
            return None

        authors = [str(a) for a in result.authors]
        year = result.published.year if result.published else datetime.datetime.now().year
        doi = f"arXiv:{result.entry_id.split('/')[-1]}"
        abstract = result.summary.strip()
        url = result.entry_id

        categories = result.categories
        ptype = "预印本"
        if any(c.startswith("cs.") for c in categories):
            ptype = "计算机科学预印本"
        elif any(c.startswith("physics.") for c in categories):
            ptype = "物理学预印本"

        return PaperData(
            title=title, authors=authors, year=year, doi=doi,
            journal="arXiv", abstract=abstract, source="arxiv",
            url=url, paper_type=ptype, has_fulltext=True,
        )
