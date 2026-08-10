"""Regression guards for bounded hot paths."""

from datetime import datetime, timedelta
import uuid


def test_ai_context_is_bounded_to_recent_messages():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    import app.models  # noqa: F401 - register every mapped table
    from app.db import Base
    from app.models.chat import ChatMessage, ChatSession
    from app.services.chat_service import (
        MAX_AI_CONTEXT_CHARS,
        MAX_AI_CONTEXT_MESSAGES,
        build_messages_for_ai,
    )

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    session_id = str(uuid.uuid4())
    try:
        db.add(ChatSession(id=session_id, title="performance-context-test"))
        start = datetime(2026, 1, 1)
        for index in range(MAX_AI_CONTEXT_MESSAGES + 10):
            db.add(ChatMessage(
                session_id=session_id,
                role="user" if index % 2 == 0 else "assistant",
                content=f"message-{index}",
                created_at=start + timedelta(seconds=index),
            ))
        db.commit()

        messages = build_messages_for_ai(db, session_id, system_prompt="system")

        assert len(messages) == MAX_AI_CONTEXT_MESSAGES + 1
        assert messages[0] == {"role": "system", "content": "system"}
        assert messages[1]["content"] == "message-10"
        assert messages[-1]["content"] == "message-29"

        db.add(ChatMessage(
            session_id=session_id,
            role="user",
            content="x" * (MAX_AI_CONTEXT_CHARS * 2),
            created_at=start + timedelta(seconds=100),
        ))
        db.commit()
        bounded = build_messages_for_ai(db, session_id, system_prompt="system")
        assert sum(len(item["content"]) for item in bounded[1:]) <= MAX_AI_CONTEXT_CHARS
    finally:
        db.close()
        engine.dispose()
