"""文献话题服务 — 论文按话题分组管理（多对多关系）"""

import json
from datetime import datetime
from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.paper import PaperResearchTopic, PaperResearchTopicLink, Paper


def create_topic(db: Session, name: str, description: str = "") -> dict:
    """创建话题"""
    import uuid
    topic = PaperResearchTopic(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return _topic_to_dict(db, topic)


def get_topics(db: Session) -> list[dict]:
    """获取所有话题（含论文数量）"""
    topics = db.query(PaperResearchTopic).order_by(PaperResearchTopic.updated_at.desc().nullslast(),
                                                    PaperResearchTopic.created_at.desc()).all()
    return [_topic_to_dict(db, t) for t in topics]


def get_topic(db: Session, topic_id: str) -> Optional[dict]:
    """获取单个话题"""
    topic = db.get(PaperResearchTopic, topic_id)
    if not topic:
        return None
    return _topic_to_dict(db, topic)


def get_topic_with_papers(db: Session, topic_id: str) -> Optional[dict]:
    """获取话题详情（含完整论文列表）"""
    topic = db.get(PaperResearchTopic, topic_id)
    if not topic:
        return None

    # 通过关联表查询论文
    links = db.query(PaperResearchTopicLink).filter(
        PaperResearchTopicLink.topic_id == topic_id
    ).all()

    paper_ids = [link.paper_id for link in links]
    papers = []
    if paper_ids:
        paper_list = db.query(Paper).filter(Paper.id.in_(paper_ids)).all()
        papers = [_paper_to_dict(p) for p in paper_list]

    result = _topic_to_dict(db, topic)
    result["papers"] = papers
    return result


def delete_topic(db: Session, topic_id: str) -> bool:
    """删除话题（同时删除所有关联关系）"""
    topic = db.get(PaperResearchTopic, topic_id)
    if not topic:
        return False
    # 先删除关联
    db.query(PaperResearchTopicLink).filter(
        PaperResearchTopicLink.topic_id == topic_id
    ).delete()
    db.delete(topic)
    db.commit()
    return True


def add_paper_to_topic(db: Session, topic_id: str, paper_id: str) -> bool:
    """添加单篇论文到话题（去重）"""
    # 检查是否已存在
    existing = db.get(PaperResearchTopicLink, {"topic_id": topic_id, "paper_id": paper_id})
    if existing:
        return False  # 重复

    link = PaperResearchTopicLink(topic_id=topic_id, paper_id=paper_id)
    db.add(link)
    # 更新话题的 updated_at
    topic = db.get(PaperResearchTopic, topic_id)
    if topic:
        topic.updated_at = datetime.now()
    db.commit()
    return True


def remove_paper_from_topic(db: Session, topic_id: str, paper_id: str) -> bool:
    """从话题中移除单篇论文（不删除论文本身）"""
    link = db.get(PaperResearchTopicLink, {"topic_id": topic_id, "paper_id": paper_id})
    if not link:
        return False
    db.delete(link)
    # 更新话题的 updated_at
    topic = db.get(PaperResearchTopic, topic_id)
    if topic:
        topic.updated_at = datetime.now()
    db.commit()
    return True


def add_papers_to_topic(db: Session, topic_id: str, paper_ids: list[str]) -> dict:
    """批量添加论文到话题（去重）"""
    # 查询已存在的关联
    existing = db.query(PaperResearchTopicLink.paper_id).filter(
        PaperResearchTopicLink.topic_id == topic_id,
        PaperResearchTopicLink.paper_id.in_(paper_ids)
    ).all()
    existing_ids = {row[0] for row in existing}

    added = 0
    skipped = 0
    for pid in paper_ids:
        if pid in existing_ids:
            skipped += 1
            continue
        db.add(PaperResearchTopicLink(topic_id=topic_id, paper_id=pid))
        added += 1

    if added > 0:
        # 更新话题的 updated_at
        topic = db.get(PaperResearchTopic, topic_id)
        if topic:
            topic.updated_at = datetime.now()

    db.commit()
    return {"added": added, "skipped": skipped}


def _topic_to_dict(db: Session, topic: PaperResearchTopic) -> dict:
    """话题转字典"""
    paper_count = db.query(func.count(PaperResearchTopicLink.paper_id)).filter(
        PaperResearchTopicLink.topic_id == topic.id
    ).scalar() or 0

    return {
        "id": topic.id,
        "name": topic.name,
        "description": topic.description,
        "paper_count": paper_count,
        "created_at": topic.created_at.isoformat() if topic.created_at else None,
        "updated_at": topic.updated_at.isoformat() if topic.updated_at else None,
    }


def _paper_to_dict(paper: Paper) -> dict:
    """论文转字典（与 PaperLibraryPage 卡片 UI 所需字段一致）"""
    authors = []
    if paper.authors:
        try:
            authors = json.loads(paper.authors)
        except (json.JSONDecodeError, TypeError):
            authors = []

    tags = []
    if paper.tags:
        try:
            tags = json.loads(paper.tags)
        except (json.JSONDecodeError, TypeError):
            tags = []

    return {
        "id": paper.id,
        "title": paper.title,
        "authors": authors,
        "year": paper.year,
        "doi": paper.doi or "",
        "abstract": paper.abstract or "",
        "journal": paper.journal or "",
        "source": paper.source or "",
        "url": paper.url or "",
        "citation": paper.citation or "",
        "paper_type": paper.paper_type or "未知",
        "has_fulltext": paper.has_fulltext or False,
        "star_rating": paper.star_rating or 0,
        "user_notes": paper.user_notes or "",
        "ai_summary": paper.ai_summary or "",
        "local_path": paper.local_path or "",
        "tags": tags,
        "review_id": paper.review_id or "",
        "created_at": paper.created_at.isoformat() if paper.created_at else None,
    }
