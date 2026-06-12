"""AI 模型配置数据模型"""

import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class ModelConfig(Base):
    """AI 模型配置 — 支持 OpenAI 和 Anthropic 协议"""
    __tablename__ = "model_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100))  # 显示名称
    base_url: Mapped[str] = mapped_column(String(500))  # API 端点
    api_key: Mapped[str] = mapped_column(String(500), default="")
    model_name: Mapped[str] = mapped_column(String(100))  # 模型标识
    protocol: Mapped[str] = mapped_column(String(20), default="openai")  # "openai" / "anthropic"
    purpose: Mapped[str] = mapped_column(String(20), default="all")  # summary/review/chat/all
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
