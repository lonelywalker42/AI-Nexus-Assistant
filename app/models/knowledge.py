"""知识库数据模型 — 整合 ai-literature 知识库 + DeepseekManager 知识卡片"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class KnowledgeCard(Base):
    """知识卡片"""
    __tablename__ = "knowledge_cards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text, default="")
    key_points: Mapped[str] = mapped_column(Text, default="[]")  # JSON array
    source_type: Mapped[str] = mapped_column(String(20), default="manual")  # deepseek/literature/manual
    paper_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)  # FK -> papers
    embedding_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # ChromaDB vector ID
    category_path: Mapped[str] = mapped_column(Text, default="")  # e.g. "控制/飞行控制/PID"
    star_rating: Mapped[int] = mapped_column(Integer, default=0)  # 0-5
    user_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class Tag(Base):
    """标签"""
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(50), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="confirmed")  # suggested/confirmed
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class CardTag(Base):
    """知识卡片-标签关联表"""
    __tablename__ = "card_tags"

    card_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_cards.id", ondelete="CASCADE"))
    tag_name: Mapped[str] = mapped_column(String(50), ForeignKey("tags.name", ondelete="CASCADE"))

    __table_args__ = (
        PrimaryKeyConstraint("card_id", "tag_name"),
    )
