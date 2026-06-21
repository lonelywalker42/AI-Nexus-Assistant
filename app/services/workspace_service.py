"""工作区服务 — 论文子集管理"""

import json
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, Session
from app.db import Base


class Workspace(Base):
    """工作区"""
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    paper_ids: Mapped[str] = mapped_column(Text, default="[]")  # JSON array
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


def create_workspace(db: Session, name: str, description: str = "",
                     paper_ids: list[str] = None) -> dict:
    """创建工作区"""
    import uuid
    ws = Workspace(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        paper_ids=json.dumps(paper_ids or []),
    )
    db.add(ws)
    db.commit()
    db.refresh(ws)
    return _workspace_to_dict(ws)


def get_workspaces(db: Session) -> list[dict]:
    """获取所有工作区"""
    workspaces = db.query(Workspace).order_by(Workspace.updated_at.desc()).all()
    return [_workspace_to_dict(ws) for ws in workspaces]


def get_workspace(db: Session, workspace_id: str) -> Optional[dict]:
    """获取单个工作区"""
    ws = db.get(Workspace, workspace_id)
    if not ws:
        return None
    return _workspace_to_dict(ws)


def update_workspace(db: Session, workspace_id: str, **kwargs) -> Optional[dict]:
    """更新工作区"""
    ws = db.get(Workspace, workspace_id)
    if not ws:
        return None

    for key, value in kwargs.items():
        if key == "paper_ids" and isinstance(value, list):
            value = json.dumps(value)
        if hasattr(ws, key):
            setattr(ws, key, value)

    db.commit()
    db.refresh(ws)
    return _workspace_to_dict(ws)


def delete_workspace(db: Session, workspace_id: str) -> bool:
    """删除工作区"""
    ws = db.get(Workspace, workspace_id)
    if not ws:
        return False
    db.delete(ws)
    db.commit()
    return True


def add_papers_to_workspace(db: Session, workspace_id: str,
                            paper_ids: list[str]) -> Optional[dict]:
    """向工作区添加论文"""
    ws = db.get(Workspace, workspace_id)
    if not ws:
        return None

    current_ids = json.loads(ws.paper_ids) if ws.paper_ids else []
    new_ids = list(set(current_ids + paper_ids))
    ws.paper_ids = json.dumps(new_ids)
    db.commit()
    db.refresh(ws)
    return _workspace_to_dict(ws)


def remove_papers_from_workspace(db: Session, workspace_id: str,
                                 paper_ids: list[str]) -> Optional[dict]:
    """从工作区移除论文"""
    ws = db.get(Workspace, workspace_id)
    if not ws:
        return None

    current_ids = json.loads(ws.paper_ids) if ws.paper_ids else []
    remove_set = set(paper_ids)
    new_ids = [pid for pid in current_ids if pid not in remove_set]
    ws.paper_ids = json.dumps(new_ids)
    db.commit()
    db.refresh(ws)
    return _workspace_to_dict(ws)


def get_workspace_papers(db: Session, workspace_id: str) -> list[dict]:
    """获取工作区中的论文"""
    from app.models.paper import Paper

    ws = db.get(Workspace, workspace_id)
    if not ws:
        return []

    paper_ids = json.loads(ws.paper_ids) if ws.paper_ids else []
    papers = []
    for pid in paper_ids:
        paper = db.get(Paper, pid)
        if paper:
            papers.append({
                "id": paper.id,
                "title": paper.title,
                "authors": paper.authors,
                "year": paper.year,
                "journal": paper.journal,
                "doi": paper.doi,
                "star_rating": paper.star_rating,
            })
    return papers


def _workspace_to_dict(ws: Workspace) -> dict:
    """转换为字典"""
    paper_ids = json.loads(ws.paper_ids) if ws.paper_ids else []
    return {
        "id": ws.id,
        "name": ws.name,
        "description": ws.description,
        "paper_ids": paper_ids,
        "paper_count": len(paper_ids),
        "created_at": ws.created_at.isoformat() if ws.created_at else None,
        "updated_at": ws.updated_at.isoformat() if ws.updated_at else None,
    }
