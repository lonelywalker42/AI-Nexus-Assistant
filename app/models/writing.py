"""写作工作台数据模型"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class WritingDocument(Base):
    """写作文档"""
    __tablename__ = "writing_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(Text, default="无标题文档")
    content: Mapped[str] = mapped_column(Text, default="")  # Markdown content
    outline: Mapped[str] = mapped_column(Text, default="[]")  # JSON array of sections
    linked_paper_ids: Mapped[str] = mapped_column(Text, default="[]")  # JSON array of paper IDs
    document_type: Mapped[str] = mapped_column(String(20), default="paper")  # paper/report/notes
    word_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
