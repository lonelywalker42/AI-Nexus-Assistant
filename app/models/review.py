"""文献综述数据模型"""

import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class Review(Base):
    """文献综述"""
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text, default="")  # Markdown 内容
    paper_ids: Mapped[str] = mapped_column(Text, default="[]")  # JSON array of paper IDs
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
