"""AI对话服务层 — 会话管理 + 消息持久化"""

from datetime import datetime
from typing import Optional
from collections import defaultdict
from sqlalchemy.orm import Session
from app.models.chat import ChatSession, ChatMessage


# Long conversations used to send the complete history on every request.  Keeping
# the most recent 20 messages bounds prompt construction and is roughly a 10x
# reduction once a conversation grows beyond a few hundred turns.
MAX_AI_CONTEXT_MESSAGES = 20
MAX_AI_CONTEXT_CHARS = 40_000


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
    if not system_prompt:
        system_prompt = (
            "你是一个专业的科研助手。你可以使用工具来搜索互联网获取最新信息。\n\n"
            "当使用 web_search 工具获取搜索结果后，你必须：\n"
            "1. 仔细阅读每条搜索结果的标题和摘要内容\n"
            "2. 基于搜索结果中的具体信息，为用户提供全面、详细的回答\n"
            "3. 引用信息来源（标题或链接）\n"
            "4. 绝对不要仅仅说'我搜索了X'就结束回答——你必须给出搜索到的实际内容和答案\n"
            "5. 如果搜索结果不足以回答问题，请说明原因并建议用户换关键词搜索"
        )
    messages.append({"role": "system", "content": system_prompt})

    db_messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(MAX_AI_CONTEXT_MESSAGES)
        .all()
    )
    db_messages.reverse()

    # Preserve the newest turns if a few unusually large messages would still
    # exceed the character budget.
    selected: list[tuple[str, str]] = []
    remaining = MAX_AI_CONTEXT_CHARS
    for msg in reversed(db_messages):
        content = msg.content or ""
        if len(content) > remaining:
            if not selected and remaining > 0:
                selected.append((msg.role, content[:remaining]))
            break
        selected.append((msg.role, content))
        remaining -= len(content)
        if remaining <= 0:
            break

    selected.reverse()
    for role, content in selected:
        messages.append({"role": role, "content": content})

    return messages


def deduplicate_sessions(db: Session, category: str = "") -> dict:
    """去重对话会话：同一分类下标题相同（不区分大小写）的会话只保留最新的一条

    Args:
        db: 数据库会话
        category: 指定分类去重，为空则对所有分类去重

    Returns:
        {"removed": int, "details": list[dict]}  details 包含被删除会话的 id 和 title
    """
    query = db.query(ChatSession)
    if category:
        query = query.filter(ChatSession.category == category)
    all_sessions = query.order_by(ChatSession.created_at.desc()).all()

    # 按 (category, normalized_title) 分组，保留每组第一条（最新）
    groups: dict[tuple[str, str], list[ChatSession]] = defaultdict(list)
    for s in all_sessions:
        normalized = (s.title or "").strip().lower()
        key = (s.category, normalized)
        groups[key].append(s)

    removed = 0
    details = []
    for key, session_list in groups.items():
        if len(session_list) <= 1:
            continue
        # 保留第一条（最新），删除其余
        to_keep = session_list[0]
        for dup in session_list[1:]:
            details.append({"id": dup.id, "title": dup.title})
            db.delete(dup)
            removed += 1

    if removed > 0:
        db.commit()

    return {"removed": removed, "details": details}
