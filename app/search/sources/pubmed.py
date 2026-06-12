"""PubMed 搜索引擎"""

import requests
import xml.etree.ElementTree as ET
from typing import List
from .base import SearchEngine, PaperData


class PubMedSearch(SearchEngine):
    """PubMed E-utilities API 搜索"""

    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def __init__(self):
        super().__init__("pubmed")
        self.min_request_interval = 0.5

    def search(self, query: str, max_results: int = 10) -> List[PaperData]:
        self._rate_limit()

        # Step 1: esearch 获取 ID 列表
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": min(max_results, 100),
            "retmode": "json",
            "sort": "relevance",
        }
        try:
            resp = requests.get(self.ESEARCH_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            ids = data.get("esearchresult", {}).get("idlist", [])
        except Exception as e:
            print(f"❌ PubMed esearch 错误: {e}")
            return []

        if not ids:
            return []

        # Step 2: efetch 获取详细信息
        self._rate_limit()
        fetch_params = {
            "db": "pubmed",
            "id": ",".join(ids),
            "retmode": "xml",
        }
        try:
            resp = requests.get(self.EFETCH_URL, params=fetch_params, timeout=15)
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
        except Exception as e:
            print(f"❌ PubMed efetch 错误: {e}")
            return []

        papers = []
        for article in root.findall(".//PubmedArticle"):
            paper = self._parse_article(article)
            if paper:
                papers.append(paper)
        return papers

    def _parse_article(self, article) -> PaperData | None:
        try:
            medline = article.find(".//MedlineCitation")
            art = medline.find(".//Article")

            title = (art.findtext(".//ArticleTitle") or "").strip()
            if not title:
                return None

            authors = []
            for auth in art.findall(".//Author")[:5]:
                last = auth.findtext("LastName", "")
                first = auth.findtext("ForeName", "")
                if last:
                    authors.append(f"{first} {last}".strip())

            year_text = art.findtext(".//PubDate/Year") or art.findtext(".//PubDate/MedlineDate") or ""
            year = self._extract_year(year_text)

            # DOI
            doi = ""
            for eid in article.findall(".//ArticleIdList/ArticleId"):
                if eid.get("IdType") == "doi":
                    doi = eid.text or ""
                    break

            journal = (art.findtext(".//Journal/Title") or "").strip()
            abstract_parts = []
            for at in art.findall(".//Abstract/AbstractText"):
                text = "".join(at.itertext()).strip()
                if text:
                    abstract_parts.append(text)
            abstract = " ".join(abstract_parts)

            pmid = medline.findtext("PMID", "")
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

            return PaperData(
                title=title, authors=authors, year=year, doi=doi,
                journal=journal, abstract=abstract, source="pubmed",
                url=url, paper_type="期刊文章",
            )
        except Exception:
            return None
