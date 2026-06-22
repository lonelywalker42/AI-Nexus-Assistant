"""文献数据模型 — 整合 ai-literature + ai-researchers"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class PaperNote(Base):
    """论文笔记（持久化，跨会话）"""
    __tablename__ = "paper_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    paper_id: Mapped[str] = mapped_column(String(36), index=True)
    content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class PaperCategory(Base):
    """论文分类"""
    __tablename__ = "paper_categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100))
    parent_id: Mapped[str] = mapped_column(String(36), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    system_key: Mapped[str] = mapped_column(String(50), default="")  # all/recent/uncategorized/favorites


class PaperCategoryLink(Base):
    """论文-分类关联"""
    __tablename__ = "paper_category_links"

    paper_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    category_id: Mapped[str] = mapped_column(String(36), primary_key=True)


class Attachment(Base):
    """论文附件"""
    __tablename__ = "attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    paper_id: Mapped[str] = mapped_column(String(36), index=True)
    kind: Mapped[str] = mapped_column(String(50), default="pdf")  # pdf/supplement/code/data
    original_path: Mapped[str] = mapped_column(Text, default="")
    stored_path: Mapped[str] = mapped_column(Text, default="")
    file_name: Mapped[str] = mapped_column(Text, default="")
    mime_type: Mapped[str] = mapped_column(String(100), default="")
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    content_hash: Mapped[str] = mapped_column(String(64), default="")  # SHA-256
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


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
    fulltext: Mapped[str] = mapped_column(Text, default="")  # 提取的全文文本
    star_rating: Mapped[int] = mapped_column(Integer, default=0)  # 0-5
    user_notes: Mapped[str] = mapped_column(Text, default="")
    ai_summary: Mapped[str] = mapped_column(Text, default="")
    local_path: Mapped[str] = mapped_column(Text, default="")  # PDF 本地路径
    tags: Mapped[str] = mapped_column(Text, default="[]")  # JSON 标签数组
    review_id: Mapped[str] = mapped_column(String(36), default="")  # 关联综述 ID
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
