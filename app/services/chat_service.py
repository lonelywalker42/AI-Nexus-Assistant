"""AI对话服务层 — 会话管理 + 消息持久化"""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models.chat import ChatSession, ChatMessage


def get_sessions(db: Session) -> list[ChatSession]:
    """获取所有对话会话"""
    return db.query(ChatSession).order_by(ChatSession.created_at.desc()).all()


def create_session(db: Session, title: str = "新对话", category: str = "general", model_name: str = "") -> ChatSession:
    """创建对话会话"""
    session = ChatSession(title=title, category=category, model_name=model_name)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session_by_id(db: Session, session_id: str) -> Optional[ChatSession]:
    """获取单个会话"""
    return db.get(ChatSession, session_id)


def delete_session(db: Session, session_id: str) -> bool:
    """删除对话会话"""
    session = db.get(ChatSession, session_id)
    if not session:
        return False
    db.delete(session)
    db.commit()
    return True


def update_session_title(db: Session, session_id: str, title: str) -> Optional[ChatSession]:
    """更新会话标题"""
    session = db.get(ChatSession, session_id)
    if not session:
        return None
    session.title = title
    db.commit()
    db.refresh(session)
    return session


def get_messages(db: Session, session_id: str) -> list[ChatMessage]:
    """获取会话的所有消息"""
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )


def add_message(db: Session, session_id: str, role: str, content: str,
                thinking_content: str = "") -> ChatMessage:
    """添加消息"""
    msg = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        thinking_content=thinking_content,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def clear_session(db: Session, session_id: str) -> bool:
    """清空会话的所有消息"""
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.commit()
    return True


def get_message_count(db: Session, session_id: str) -> int:
    """获取会话消息数量"""
    from sqlalchemy import func
    return db.query(func.count(ChatMessage.id)).filter(
        ChatMessage.session_id == session_id
    ).scalar() or 0


def build_messages_for_ai(db: Session, session_id: str,
                          system_prompt: str = "") -> list[dict]:
    """构建发送给 AI 的消息列表"""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    db_messages = get_messages(db, session_id)
    for msg in db_messages:
        messages.append({"role": msg.role, "content": msg.content})

    return messages
