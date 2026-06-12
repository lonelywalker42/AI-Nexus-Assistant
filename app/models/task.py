"""任务与周计划数据模型"""

import uuid
from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import String, Text, Integer, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class WeeklyPlan(Base):
    """周计划"""
    __tablename__ = "weekly_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), default="default", index=True)
    week_start: Mapped[date] = mapped_column(Date)
    week_end: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    tasks: Mapped[List["Task"]] = relationship(back_populates="plan", cascade="all, delete-orphan")


class Task(Base):
    """任务/待办事项 — 整合 ai-todo + ai-research-manager"""
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("weekly_plans.id", ondelete="CASCADE"), nullable=True)
    date: Mapped[str] = mapped_column(String(10), index=True)  # "YYYY-MM-DD"
    content: Mapped[str] = mapped_column(Text)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[str] = mapped_column(String(10), default="normal")  # low/normal/high/urgent
    category: Mapped[str] = mapped_column(String(20), default="general")  # general/literature/experiment/writing
    paper_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)  # FK -> papers
    experiment_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)  # FK -> experiments
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    plan: Mapped[Optional["WeeklyPlan"]] = relationship(back_populates="tasks")
