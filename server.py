"""AI Nexus Assistant — FastAPI 后端 API

为 Tauri 2 前端提供 REST API 接口。
启动方式: python server.py 或 uvicorn server:app --port 8765
"""

import sys
import os
import json
import asyncio
from datetime import date, datetime
from typing import Optional
from pathlib import Path

# 确保 app 包可导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.db import init_db, get_session
from app.models import Task, WeeklyPlan, Paper, ModelConfig, SearchHistory
from app.models import Experiment, ExperimentResult
from app.models import KnowledgeCard, Tag, CardTag
from app.models import ChatSession, ChatMessage
from app.services import task_service, experiment_service, knowledge_service, chat_service
from app.ai.router import AIRouter

# 初始化
init_db()
app = FastAPI(title="AI Nexus Assistant API", version="0.1.0")

# CORS（Tauri 前端需要）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# AI 路由器（延迟初始化）
_ai_router: AIRouter | None = None


def get_ai() -> AIRouter:
    global _ai_router
    if _ai_router is None:
        _ai_router = AIRouter()
    return _ai_router


# ══════════════════════════════════════════════════════════════
#  仪表盘
# ══════════════════════════════════════════════════════════════

@app.get("/api/dashboard")
def get_dashboard():
    db = get_session()
    try:
        today = date.today()
        task_stats = task_service.get_task_stats(db, today.isoformat())
        m_total, m_done = task_service.get_month_stats(db, today.year, today.month)
        exp_stats = experiment_service.get_experiment_stats(db)
        kb_stats = knowledge_service.get_card_stats(db)

        # 最近活动
        recent_tasks = db.query(Task).filter(
            Task.completed == True, Task.completed_at.isnot(None)
        ).order_by(Task.completed_at.desc()).limit(5).all()

        recent_searches = db.query(SearchHistory).order_by(
            SearchHistory.created_at.desc()
        ).limit(3).all()

        activities = []
        for t in recent_tasks:
            activities.append({
                "type": "task",
                "text": f"完成: {t.content[:40]}",
                "time": t.completed_at.strftime("%H:%M") if t.completed_at else "",
            })
        for s in recent_searches:
            activities.append({
                "type": s.history_type,
                "text": f"{s.query[:40]}",
                "time": s.created_at.strftime("%H:%M"),
            })

        return {
            "tasks": task_stats,
            "monthly": {"total": m_total, "done": m_done},
            "experiments": exp_stats,
            "knowledge": kb_stats,
            "activities": activities[:10],
        }
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════
#  任务
# ══════════════════════════════════════════════════════════════

class TaskCreate(BaseModel):
    date: str
    content: str
    priority: str = "normal"
    category: str = "general"


class TaskUpdate(BaseModel):
    content: Optional[str] = None
    completed: Optional[bool] = None
    priority: Optional[str] = None
    category: Optional[str] = None


@app.get("/api/tasks")
def list_tasks(date: str = Query(default_factory=lambda: date.today().isoformat())):
    db = get_session()
    try:
        tasks = task_service.get_all_todos_by_date(db, date)
        return [_task_to_dict(t) for t in tasks]
    finally:
        db.close()


@app.post("/api/tasks")
def create_task(body: TaskCreate):
    db = get_session()
    try:
        task = task_service.add_standalone_task(db, body.date, body.content, body.priority, body.category)
        return _task_to_dict(task)
    finally:
        db.close()


@app.patch("/api/tasks/{task_id}")
def update_task(task_id: str, body: TaskUpdate):
    db = get_session()
    try:
        kwargs = {k: v for k, v in body.dict().items() if v is not None}
        task = task_service.update_task(db, task_id, **kwargs)
        if not task:
            raise HTTPException(404, "Task not found")
        return _task_to_dict(task)
    finally:
        db.close()


@app.post("/api/tasks/{task_id}/toggle")
def toggle_task(task_id: str):
    db = get_session()
    try:
        task = task_service.toggle_complete(db, task_id)
        if not task:
            raise HTTPException(404, "Task not found")
        return _task_to_dict(task)
    finally:
        db.close()


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: str):
    db = get_session()
    try:
        ok = task_service.delete_task(db, task_id)
        if not ok:
            raise HTTPException(404, "Task not found")
        return {"ok": True}
    finally:
        db.close()


@app.get("/api/tasks/dates")
def get_task_dates(year: int, month: int):
    db = get_session()
    try:
        start = f"{year:04d}-{month:02d}-01"
        end = f"{year:04d}-{month + 1:02d}-01" if month < 12 else f"{year + 1:04d}-01-01"
        marks = task_service.get_dates_with_todos(db, start, end)
        return marks
    finally:
        db.close()


def _task_to_dict(t: Task) -> dict:
    return {
        "id": t.id,
        "date": t.date,
        "content": t.content,
        "completed": t.completed,
        "priority": t.priority,
        "category": t.category,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
    }


# ══════════════════════════════════════════════════════════════
#  文献搜索
# ══════════════════════════════════════════════════════════════

class SearchRequest(BaseModel):
    query: str
    sources: list[str] = ["openalex", "arxiv", "semantic_scholar"]
    max_results: int = 50


# 搜索引擎延迟加载
_search_engine = None


def get_search_engine():
    global _search_engine
    if _search_engine is None:
        from app.search.engine import UnifiedSearchEngine
        _search_engine = UnifiedSearchEngine()
    return _search_engine


@app.post("/api/search")
def search_literature(body: SearchRequest):
    engine = get_search_engine()
    try:
        results = engine.search(body.query, sources=body.sources, max_results=body.max_results)
        papers = [p.to_dict() for p in results]

        # 保存历史
        db = get_session()
        try:
            record = SearchHistory(
                query=body.query[:200],
                history_type="search",
                result_count=len(papers),
                data=json.dumps(papers, ensure_ascii=False)[:5000],
            )
            db.add(record)
            db.commit()
        finally:
            db.close()

        return {"papers": papers, "count": len(papers)}
    except Exception as e:
        raise HTTPException(500, str(e))


# ══════════════════════════════════════════════════════════════
#  试验管理
# ══════════════════════════════════════════════════════════════

class ExperimentCreate(BaseModel):
    title: str
    background: str = ""
    objective: str = ""
    setup: str = ""


class ResultCreate(BaseModel):
    description: str = ""
    parameters: dict = {}
    code_snippets: list = []
    result_data: str = ""
    conclusion: str = ""


@app.get("/api/experiments")
def list_experiments(search: str = "", status: str = ""):
    db = get_session()
    try:
        exps = experiment_service.get_experiments(db, search, status)
        return [{
            "id": e.id, "title": e.title, "status": e.status,
            "background": e.background, "objective": e.objective, "setup": e.setup,
            "created_at": e.created_at.isoformat(),
            "updated_at": e.updated_at.isoformat(),
            "results": [{
                "id": r.id, "version": r.version, "description": r.description,
                "parameters": json.loads(r.parameters) if r.parameters else {},
                "code_snippets": json.loads(r.code_snippets) if r.code_snippets else [],
                "result_data": r.result_data, "conclusion": r.conclusion,
                "created_at": r.created_at.isoformat(),
            } for r in e.results],
        } for e in exps]
    finally:
        db.close()


@app.post("/api/experiments")
def create_experiment(body: ExperimentCreate):
    db = get_session()
    try:
        exp = experiment_service.create_experiment(db, body.title, body.background, body.objective, body.setup)
        return {"id": exp.id, "title": exp.title, "status": exp.status}
    finally:
        db.close()


@app.post("/api/experiments/{exp_id}/results")
def add_result(exp_id: str, body: ResultCreate):
    db = get_session()
    try:
        result = experiment_service.add_result(
            db, exp_id, body.description, body.parameters,
            body.code_snippets, body.result_data, body.conclusion
        )
        if not result:
            raise HTTPException(404, "Experiment not found")
        return {"id": result.id, "version": result.version}
    finally:
        db.close()


@app.delete("/api/experiments/{exp_id}")
def delete_experiment(exp_id: str):
    db = get_session()
    try:
        ok = experiment_service.delete_experiment(db, exp_id)
        if not ok:
            raise HTTPException(404)
        return {"ok": True}
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════
#  知识库
# ══════════════════════════════════════════════════════════════

class CardCreate(BaseModel):
    title: str
    summary: str = ""
    key_points: list = []
    source_type: str = "manual"
    category_path: str = ""
    tags: list[str] = []


@app.get("/api/knowledge/cards")
def list_cards(search: str = "", category: str = "", tag: str = "", source_type: str = ""):
    db = get_session()
    try:
        cards = knowledge_service.get_cards(db, search, category, tag, source_type)
        return [{
            "id": c.id, "title": c.title, "summary": c.summary,
            "key_points": json.loads(c.key_points) if c.key_points else [],
            "source_type": c.source_type, "category_path": c.category_path,
            "star_rating": c.star_rating, "user_notes": c.user_notes,
            "created_at": c.created_at.isoformat(),
        } for c in cards]
    finally:
        db.close()


@app.post("/api/knowledge/cards")
def create_card(body: CardCreate):
    db = get_session()
    try:
        card = knowledge_service.create_card(
            db, body.title, body.summary, body.key_points,
            body.source_type, category_path=body.category_path, tags=body.tags
        )
        return {"id": card.id, "title": card.title}
    finally:
        db.close()


@app.patch("/api/knowledge/cards/{card_id}")
def update_card(card_id: str, body: dict):
    db = get_session()
    try:
        card = knowledge_service.update_card(db, card_id, **body)
        if not card:
            raise HTTPException(404)
        return {"id": card.id}
    finally:
        db.close()


@app.delete("/api/knowledge/cards/{card_id}")
def delete_card(card_id: str):
    db = get_session()
    try:
        ok = knowledge_service.delete_card(db, card_id)
        if not ok:
            raise HTTPException(404)
        return {"ok": True}
    finally:
        db.close()


@app.get("/api/knowledge/tags")
def list_tags():
    db = get_session()
    try:
        tags = knowledge_service.get_tags(db)
        return [{"name": t.name, "usage_count": t.usage_count, "status": t.status} for t in tags]
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════
#  AI 对话
# ══════════════════════════════════════════════════════════════

class SessionCreate(BaseModel):
    title: str = "新对话"


class MessageCreate(BaseModel):
    content: str
    role: str = "user"


class ChatRequest(BaseModel):
    session_id: str
    model_id: str | None = None


@app.get("/api/chat/sessions")
def list_sessions():
    db = get_session()
    try:
        sessions = chat_service.get_sessions(db)
        return [{"id": s.id, "title": s.title, "model_name": s.model_name,
                 "created_at": s.created_at.isoformat()} for s in sessions]
    finally:
        db.close()


@app.post("/api/chat/sessions")
def create_session(body: SessionCreate):
    db = get_session()
    try:
        s = chat_service.create_session(db, body.title)
        return {"id": s.id, "title": s.title}
    finally:
        db.close()


@app.delete("/api/chat/sessions/{session_id}")
def delete_session(session_id: str):
    db = get_session()
    try:
        ok = chat_service.delete_session(db, session_id)
        if not ok:
            raise HTTPException(404)
        return {"ok": True}
    finally:
        db.close()


@app.get("/api/chat/sessions/{session_id}/messages")
def get_messages(session_id: str):
    db = get_session()
    try:
        messages = chat_service.get_messages(db, session_id)
        return [{"id": m.id, "role": m.role, "content": m.content,
                 "thinking_content": m.thinking_content,
                 "created_at": m.created_at.isoformat()} for m in messages]
    finally:
        db.close()


@app.post("/api/chat/sessions/{session_id}/messages")
def add_message(session_id: str, body: MessageCreate):
    db = get_session()
    try:
        msg = chat_service.add_message(db, session_id, body.role, body.content)
        return {"id": msg.id, "role": msg.role, "content": msg.content}
    finally:
        db.close()


@app.post("/api/chat/stream")
async def stream_chat(body: ChatRequest):
    """流式 AI 对话（SSE）"""
    db = get_session()
    try:
        messages = chat_service.build_messages_for_ai(db, body.session_id)
    finally:
        db.close()

    ai = get_ai()

    async def generate():
        full_thinking = ""
        full_content = ""
        for chunk in ai.stream_chat(messages, model_id=body.model_id):
            data = json.dumps(chunk, ensure_ascii=False)
            yield f"data: {data}\n\n"
            if chunk["type"] == "thinking":
                full_thinking += chunk["data"]
            elif chunk["type"] == "content":
                full_content += chunk["data"]

        # 保存 AI 回复
        db = get_session()
        try:
            chat_service.add_message(db, body.session_id, "assistant", full_content, full_thinking)
        finally:
            db.close()

        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ══════════════════════════════════════════════════════════════
#  AI 模型配置
# ══════════════════════════════════════════════════════════════

class ModelCreate(BaseModel):
    name: str
    base_url: str
    api_key: str
    model_name: str
    protocol: str = "openai"
    purpose: str = "all"


@app.get("/api/models")
def list_models():
    db = get_session()
    try:
        models = db.query(ModelConfig).all()
        return [{"id": m.id, "name": m.name, "base_url": m.base_url,
                 "model_name": m.model_name, "protocol": m.protocol,
                 "purpose": m.purpose, "is_active": m.is_active} for m in models]
    finally:
        db.close()


@app.post("/api/models")
def create_model(body: ModelCreate):
    db = get_session()
    try:
        model = ModelConfig(**body.dict(), is_active=True)
        db.add(model)
        db.commit()
        return {"id": model.id, "name": model.name}
    finally:
        db.close()


@app.delete("/api/models/{model_id}")
def delete_model(model_id: str):
    db = get_session()
    try:
        model = db.get(ModelConfig, model_id)
        if not model:
            raise HTTPException(404)
        db.delete(model)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════
#  搜索历史
# ══════════════════════════════════════════════════════════════

@app.get("/api/history")
def list_history(limit: int = 50):
    db = get_session()
    try:
        records = db.query(SearchHistory).order_by(
            SearchHistory.created_at.desc()
        ).limit(limit).all()
        return [{"id": r.id, "query": r.query, "type": r.history_type,
                 "result_count": r.result_count, "data": r.data,
                 "created_at": r.created_at.isoformat()} for r in records]
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════
#  启动
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    print(f"NEXUS_SERVER_READY:{args.port}", flush=True)
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
