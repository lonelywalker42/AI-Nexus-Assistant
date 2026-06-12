"""文献数据模型 — 整合 ai-literature + ai-researchers"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class Paper(Base):
    """学术文献"""
    __tablename__ = "papers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(Text)
    authors: Mapped[str] = mapped_column(Text, default="[]")  # JSON array
    year: Mapped[int] = mapped_column(Integer, default=0)
    doi: Mapped[str] = mapped_column(String(200), default="")
    abstract: Mapped[str] = mapped_column(Text, default="")
    journal: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(50), default="")  # openalex/arxiv/scopus/...
    url: Mapped[str] = mapped_column(Text, default="")
    citation: Mapped[str] = mapped_column(Text, default="")  # GB/T 7714 格式
    paper_type: Mapped[str] = mapped_column(String(50), default="未知")  # journal/conference/preprint
    has_fulltext: Mapped[bool] = mapped_column(Boolean, default=False)
    star_rating: Mapped[int] = mapped_column(Integer, default=0)  # 0-5
    user_notes: Mapped[str] = mapped_column(Text, default="")
    ai_summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
