"""试验管理数据模型 — 来自 ai-research-manager，扩展版本化结果"""

import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class Experiment(Base):
    """试验记录"""
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), default="default", index=True)
    title: Mapped[str] = mapped_column(Text)
    background: Mapped[str] = mapped_column(Text, default="")
    objective: Mapped[str] = mapped_column(Text, default="")
    setup: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="planning")  # planning/running/completed/suspended
    related_paper_ids: Mapped[str] = mapped_column(Text, default="[]")  # JSON array of paper IDs
    ai_analysis: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    results: Mapped[List["ExperimentResult"]] = relationship(back_populates="experiment", cascade="all, delete-orphan")


class ExperimentResult(Base):
    """试验结果（版本化）"""
    __tablename__ = "experiment_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_id: Mapped[str] = mapped_column(String(36), ForeignKey("experiments.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[str] = mapped_column(Text, default="")
    parameters: Mapped[str] = mapped_column(Text, default="{}")  # JSON key-value
    code_snippets: Mapped[str] = mapped_column(Text, default="[]")  # JSON array of {file, code, diff}
    result_data: Mapped[str] = mapped_column(Text, default="")
    conclusion: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    experiment: Mapped["Experiment"] = relationship(back_populates="results")
