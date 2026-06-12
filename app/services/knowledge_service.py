"""知识库服务层 — 整合 ai-literature 知识库 + DeepseekManager 知识卡片"""

import json
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.models.knowledge import KnowledgeCard, Tag, CardTag
from app.models.paper import Paper


def get_cards(db: Session, search: str = "", category: str = "",
              tag: str = "", source_type: str = "") -> list[KnowledgeCard]:
    """获取知识卡片列表"""
    q = db.query(KnowledgeCard)
    if search:
        q = q.filter(or_(
            KnowledgeCard.title.ilike(f"%{search}%"),
            KnowledgeCard.summary.ilike(f"%{search}%"),
            KnowledgeCard.user_notes.ilike(f"%{search}%"),
        ))
    if category:
        q = q.filter(KnowledgeCard.category_path.ilike(f"{category}%"))
    if source_type:
        q = q.filter(KnowledgeCard.source_type == source_type)
    if tag:
        # Filter by tag through association table
        card_ids = db.query(CardTag.card_id).filter(CardTag.tag_name == tag).subquery()
        q = q.filter(KnowledgeCard.id.in_(card_ids))
    return q.order_by(KnowledgeCard.updated_at.desc()).all()


def get_card(db: Session, card_id: str) -> Optional[KnowledgeCard]:
    """获取单个知识卡片"""
    return db.get(KnowledgeCard, card_id)


def create_card(db: Session, title: str, summary: str = "",
                key_points: list | None = None, source_type: str = "manual",
                paper_id: str | None = None, category_path: str = "",
                tags: list[str] | None = None) -> KnowledgeCard:
    """创建知识卡片"""
    card = KnowledgeCard(
        title=title,
        summary=summary,
        key_points=json.dumps(key_points or [], ensure_ascii=False),
        source_type=source_type,
        paper_id=paper_id,
        category_path=category_path,
    )
    db.add(card)
    db.flush()

    if tags:
        add_tags_to_card(db, card.id, tags)

    db.commit()
    db.refresh(card)
    return card


def update_card(db: Session, card_id: str, **kwargs) -> Optional[KnowledgeCard]:
    """更新知识卡片"""
    card = db.get(KnowledgeCard, card_id)
    if not card:
        return None
    for key, value in kwargs.items():
        if key == "key_points" and isinstance(value, list):
            value = json.dumps(value, ensure_ascii=False)
        if hasattr(card, key):
            setattr(card, key, value)
    card.updated_at = datetime.now()
    db.commit()
    db.refresh(card)
    return card


def delete_card(db: Session, card_id: str) -> bool:
    """删除知识卡片"""
    card = db.get(KnowledgeCard, card_id)
    if not card:
        return False
    # Delete tag associations
    db.query(CardTag).filter(CardTag.card_id == card_id).delete()
    db.delete(card)
    db.commit()
    return True


def add_tags_to_card(db: Session, card_id: str, tag_names: list[str]):
    """为卡片添加标签（自动创建不存在的标签）"""
    for name in tag_names:
        name = name.strip()
        if not name:
            continue
        # Ensure tag exists
        tag = db.get(Tag, name)
        if not tag:
            tag = Tag(name=name, status="confirmed", usage_count=0)
            db.add(tag)
            db.flush()
        tag.usage_count = (tag.usage_count or 0) + 1
        # Create association if not exists
        existing = db.query(CardTag).filter(
            CardTag.card_id == card_id, CardTag.tag_name == name
        ).first()
        if not existing:
            db.add(CardTag(card_id=card_id, tag_name=name))


def remove_tag_from_card(db: Session, card_id: str, tag_name: str):
    """从卡片移除标签"""
    db.query(CardTag).filter(
        CardTag.card_id == card_id, CardTag.tag_name == tag_name
    ).delete()
    tag = db.get(Tag, tag_name)
    if tag and tag.usage_count > 0:
        tag.usage_count -= 1
    db.commit()


def get_tags(db: Session, status: str = "") -> list[Tag]:
    """获取所有标签"""
    q = db.query(Tag)
    if status:
        q = q.filter(Tag.status == status)
    return q.order_by(Tag.usage_count.desc()).all()


def get_card_tags(db: Session, card_id: str) -> list[Tag]:
    """获取卡片的所有标签"""
    tag_names = db.query(CardTag.tag_name).filter(CardTag.card_id == card_id).subquery()
    return db.query(Tag).filter(Tag.name.in_(tag_names)).all()


def get_categories(db: Session) -> list[str]:
    """获取所有分类路径"""
    rows = db.query(KnowledgeCard.category_path).filter(
        KnowledgeCard.category_path != ""
    ).distinct().all()
    return sorted(set(r[0] for r in rows))


def get_card_stats(db: Session) -> dict:
    """获取知识库统计"""
    total = db.query(func.count(KnowledgeCard.id)).scalar() or 0
    by_source = {}
    for stype in ["manual", "literature", "deepseek"]:
        count = db.query(func.count(KnowledgeCard.id)).filter(
            KnowledgeCard.source_type == stype
        ).scalar() or 0
        by_source[stype] = count
    tag_count = db.query(func.count(Tag.name)).scalar() or 0
    return {"total": total, "by_source": by_source, "tag_count": tag_count}


def create_card_from_paper(db: Session, paper_id: str) -> Optional[KnowledgeCard]:
    """从文献创建知识卡片"""
    paper = db.get(Paper, paper_id)
    if not paper:
        return None

    authors = json.loads(paper.authors) if paper.authors else []
    key_points = []
    if paper.ai_summary:
        key_points = [paper.ai_summary[:200]]

    return create_card(
        db,
        title=paper.title,
        summary=paper.abstract[:500] if paper.abstract else "",
        key_points=key_points,
        source_type="literature",
        paper_id=paper_id,
        category_path="",
        tags=[],
    )
