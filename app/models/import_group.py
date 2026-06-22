"""导入分组模型 — DeepSeek 对话导入的分组管理"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class ImportGroup(Base):
    """导入分组 — 一次 JSON 导入对应一个分组"""
    __tablename__ = "import_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str] = mapped_column(Text, default="")
    source_type: Mapped[str] = mapped_column(String(20), default="deepseek")  # deepseek/chatgpt/mimo
    original_filename: Mapped[str] = mapped_column(Text, default="")
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str] = mapped_column(Text, default="")
    knowledge_domain: Mapped[str] = mapped_column(Text, default="[]")  # JSON array
    card_count: Mapped[int] = mapped_column(Integer, default=0)
    chat_session_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)  # FK -> chat_sessions
    status: Mapped[str] = mapped_column(String(20), default="processing")  # processing/completed/failed
    error: Mapped[str] = mapped_column(Text, default="")
    progress: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
