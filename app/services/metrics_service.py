"""行为埋点服务 — 记录阅读/搜索事件用于研究洞察"""

import json
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, Session
from app.db import Base


class MetricEvent(Base):
    """行为事件"""
    __tablename__ = "metric_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(20))  # "read" / "search" / "import"
    action: Mapped[str] = mapped_column(String(50))    # "view_paper" / "search_query" / "import_pdf"
    target_id: Mapped[str] = mapped_column(String(100), default="")   # paper_id / query text
    target_name: Mapped[str] = mapped_column(Text, default="")        # paper title / query text
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")    # 额外数据
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


def record_event(db: Session, category: str, action: str,
                 target_id: str = "", target_name: str = "", **meta):
    """记录一个行为事件"""
    event = MetricEvent(
        category=category,
        action=action,
        target_id=target_id,
        target_name=target_name[:500],
        metadata_json=json.dumps(meta, ensure_ascii=False),
    )
    db.add(event)
    db.commit()


def record_paper_view(db: Session, paper_id: str, paper_title: str):
    """记录论文阅读事件"""
    record_event(db, "read", "view_paper", paper_id, paper_title)


def record_search(db: Session, query: str, source: str = "", result_count: int = 0):
    """记录搜索事件"""
    record_event(db, "search", "search_query", query[:200], query[:200],
                 source=source, result_count=result_count)


def record_import(db: Session, paper_id: str, paper_title: str, method: str = "pdf"):
    """记录导入事件"""
    record_event(db, "import", f"import_{method}", paper_id, paper_title)


def get_hot_keywords(db: Session, top_k: int = 20) -> list[dict]:
    """获取热门搜索关键词"""
    # 停用词列表
    stopwords = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人",
                 "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
                 "你", "会", "着", "没有", "看", "好", "自己", "这", "他", "她",
                 "the", "a", "an", "is", "are", "was", "were", "be", "been",
                 "being", "have", "has", "had", "do", "does", "did", "will",
                 "would", "could", "should", "may", "might", "can", "shall",
                 "of", "in", "to", "for", "with", "on", "at", "from", "by",
                 "and", "or", "not", "but", "if", "then", "so", "as", "than"}

    rows = db.query(MetricEvent.target_name).filter(
        MetricEvent.category == "search",
        MetricEvent.action == "search_query"
    ).order_by(MetricEvent.created_at.desc()).limit(500).all()

    # 统计词频
    word_count: dict[str, int] = {}
    for (query,) in rows:
        words = query.lower().split()
        for w in words:
            w = w.strip(".,;:!?()[]{}\"'")
            if len(w) >= 2 and w not in stopwords:
                word_count[w] = word_count.get(w, 0) + 1

    # 排序取 top_k
    sorted_words = sorted(word_count.items(), key=lambda x: -x[1])[:top_k]
    return [{"keyword": w, "count": c} for w, c in sorted_words]


def get_most_read_papers(db: Session, top_k: int = 10) -> list[dict]:
    """获取高频阅读论文"""
    rows = db.query(
        MetricEvent.target_id,
        MetricEvent.target_name,
        func.count(MetricEvent.id).label("read_count")
    ).filter(
        MetricEvent.category == "read",
        MetricEvent.action == "view_paper",
        MetricEvent.target_id != ""
    ).group_by(MetricEvent.target_id).order_by(
        func.count(MetricEvent.id).desc()
    ).limit(top_k).all()

    return [
        {"paper_id": r[0], "title": r[1], "read_count": r[2]}
        for r in rows
    ]


def get_weekly_read_trend(db: Session, weeks: int = 12) -> list[dict]:
    """获取每周阅读趋势"""
    rows = db.query(
        func.strftime("%Y-%W", MetricEvent.created_at).label("week"),
        func.count(MetricEvent.id).label("count")
    ).filter(
        MetricEvent.category == "read",
        MetricEvent.action == "view_paper"
    ).group_by("week").order_by("week").all()

    return [{"week": r[0], "count": r[1]} for r in rows[-weeks:]]


def get_recent_reads(db: Session, limit: int = 20) -> list[dict]:
    """获取最近阅读记录"""
    rows = db.query(MetricEvent).filter(
        MetricEvent.category == "read",
        MetricEvent.action == "view_paper"
    ).order_by(MetricEvent.created_at.desc()).limit(limit).all()

    return [
        {
            "paper_id": r.target_id,
            "title": r.target_name,
            "read_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
