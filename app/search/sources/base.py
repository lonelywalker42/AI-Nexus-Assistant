"""搜索引擎抽象基类 — 来自 ai-researchers"""

import abc
import time
import datetime
import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class PaperData:
    """搜索结果的轻量数据类（区别于 SQLAlchemy 模型）"""
    title: str = ""
    authors: List[str] = field(default_factory=list)
    year: int = 0
    doi: str = ""
    journal: str = ""
    abstract: str = ""
    source: str = ""
    url: str = ""
    paper_type: str = "未知"
    has_fulltext: bool = False
    citation_count: int = 0

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "doi": self.doi,
            "journal": self.journal,
            "abstract": self.abstract,
            "source": self.source,
            "url": self.url,
            "paper_type": self.paper_type,
            "has_fulltext": self.has_fulltext,
            "citation_count": self.citation_count,
        }


class SearchEngine(abc.ABC):
    """搜索引擎抽象基类"""

    def __init__(self, name: str):
        self.name = name
        self.last_request_time = 0.0
        self.min_request_interval = 1.0

    @abc.abstractmethod
    def search(self, query: str, max_results: int = 10) -> List[PaperData]:
        pass

    def _rate_limit(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def _extract_year(self, date_str: str) -> int:
        if not date_str:
            return datetime.datetime.now().year
        for pattern in [r'(\d{4})-\d{2}-\d{2}', r'(\d{4})/\d{2}/\d{2}', r'(\d{4})']:
            m = re.search(pattern, date_str)
            if m:
                try:
                    return int(m.group(1))
                except ValueError:
                    continue
        return datetime.datetime.now().year
