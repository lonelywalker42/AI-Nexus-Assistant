"""搜索历史数据模型"""

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class SearchHistory(Base):
    """搜索/综述/选题历史记录"""
    __tablename__ = "search_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    query: Mapped[str] = mapped_column(Text, default="")
    history_type: Mapped[str] = mapped_column(String(20))  # search/review/topic
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    model_name: Mapped[str] = mapped_column(String(100), default="")
    review_text: Mapped[str] = mapped_column(Text, default="")
    data: Mapped[str] = mapped_column(Text, default="{}")  # JSON blob
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
