"""AI对话数据模型 — 来自 DeepseekManager"""

import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class ChatSession(Base):
    """对话会话"""
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(Text, default="新对话")
    model_name: Mapped[str] = mapped_column(String(100), default="")
    category: Mapped[str] = mapped_column(String(20), default="general")  # general/writing/review/topic/import
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    import_group_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("import_groups.id", ondelete="SET NULL"), nullable=True
    )

    messages: Mapped[List["ChatMessage"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    import_group: Mapped[Optional["ImportGroup"]] = relationship(foreign_keys=[import_group_id])


class ChatMessage(Base):
    """对话消息"""
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(20))  # user/assistant/system
    content: Mapped[str] = mapped_column(Text, default="")
    thinking_content: Mapped[str] = mapped_column(Text, default="")  # DeepSeek/R1 thinking
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")
