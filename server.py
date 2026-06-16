"""AI Nexus Assistant — FastAPI 后端 API

为 Tauri 2 前端提供 REST API 接口。
启动方式: python server.py 或 uvicorn server:app --port 8765
"""

import sys
import os
import json
import asyncio
import logging
from datetime import date, datetime
from typing import Optional
from pathlib import Path

# 冻结模式（PyInstaller）下将 stderr 重定向到日志文件，方便排查启动问题
if getattr(sys, 'frozen', False):
    _log_dir = Path(sys.executable).parent / "data"
    _log_dir.mkdir(parents=True, exist_ok=True)
    _log_path = _log_dir / "server.log"
    _fh = open(_log_path, "a", encoding="utf-8")
    sys.stderr = _fh
    sys.stdout = _fh
    logging.basicConfig(stream=_fh, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    print(f"[server] Starting frozen exe, log at {_log_path}", flush=True)

# 确保 app 包可导入（兼容 PyInstaller frozen 模式）
try:
    if getattr(sys, 'frozen', False):
        # NEXUS_APP_DIR 由 Tauri 壳设置，指向 Tauri exe 所在目录
        _env_app_dir = os.environ.get("NEXUS_APP_DIR")
        base_dir = Path(_env_app_dir) if _env_app_dir else Path(sys.executable).parent
        meipass = getattr(sys, '_MEIPASS', None)
        print(f"[server] base_dir={base_dir}, _MEIPASS={meipass}", flush=True)
        if meipass:
            sys.path.insert(0, str(Path(meipass)))
        else:
            print("[server] WARNING: _MEIPASS not set!", flush=True)
    else:
        base_dir = Path(__file__).parent
        sys.path.insert(0, str(base_dir))
except Exception as e:
    print(f"[server] ERROR in path setup: {e}", flush=True)
    import traceback; traceback.print_exc()
    sys.exit(1)

# 确保 data 目录存在（exe 旁边，不在临时目录）
data_dir = base_dir / "data"
data_dir.mkdir(parents=True, exist_ok=True)
print(f"[server] data_dir={data_dir}", flush=True)

try:
    from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel

    from app.db import init_db, get_session
    from app.models import Task, WeeklyPlan, Paper, ModelConfig, SearchHistory
    from app.models import Experiment, ExperimentResult
    from app.models import KnowledgeCard, Tag, CardTag
    from app.models import ChatSession, ChatMessage
    from app.services import task_service, experiment_service, knowledge_service, chat_service, paper_service
    from app.ai.router import AIRouter
    from app.ai.search_service import start_search_service

    # 初始化数据库
    init_db()

    # 启动 open-webSearch 聚合搜索服务（后台子进程）
    try:
        _search_ok = start_search_service()
        if _search_ok:
            print("[server] open-webSearch 聚合搜索服务已启动", flush=True)
        else:
            print("[server] 搜索服务未启动，请确保 Node.js 已安装", flush=True)
    except Exception as _e:
        print(f"[server] 搜索服务启动异常: {_e}", flush=True)

    app = FastAPI(title="AI Nexus Assistant API", version="0.1.0")
except Exception as e:
    print(f"[server] FATAL import/init error: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

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


@app.get("/api/system/info")
def get_system_info():
    """系统信息（数据库大小等）"""
    db_path = Path(data_dir) / "nexus.db"
    db_size = db_path.stat().st_size if db_path.exists() else 0
    if db_size > 1024 * 1024:
        size_str = f"{db_size / 1024 / 1024:.1f} MB"
    elif db_size > 1024:
        size_str = f"{db_size / 1024:.1f} KB"
    else:
        size_str = f"{db_size} B"
    return {"db_size": db_size, "db_size_str": size_str, "db_path": str(db_path), "data_dir": str(data_dir)}


# ══════════════════════════════════════════════════════════════
#  任务
# ══════════════════════════════════════════════════════════════

class TaskCreate(BaseModel):
    date: str
    content: str
    priority: str = "normal"
    category: str = "general"  # general/main/literature/experiment


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


@app.get("/api/tasks/main")
def list_main_tasks():
    """获取所有主线任务（不分日期）"""
    db = get_session()
    try:
        tasks = task_service.get_main_tasks(db)
        return [_task_to_dict(t) for t in tasks]
    finally:
        db.close()


@app.get("/api/tasks/incomplete")
def list_incomplete_tasks():
    """获取所有未完成的非主线任务（不分日期）"""
    db = get_session()
    try:
        tasks = task_service.get_all_incomplete_tasks(db)
        return [_task_to_dict(t) for t in tasks]
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
        "category": t.category or "general",
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

        # 保存历史（精简数据：只保留必要字段，避免截断）
        slim_papers = []
        for p in papers:
            slim_papers.append({
                "title": p.get("title", ""),
                "authors": p.get("authors", [])[:3],
                "year": p.get("year"),
                "journal": p.get("journal", ""),
                "source": p.get("source", ""),
                "abstract": (p.get("abstract", "") or "")[:200],
                "doi": p.get("doi", ""),
                "url": p.get("url", ""),
            })

        db = get_session()
        try:
            record = SearchHistory(
                query=body.query[:200],
                history_type="search",
                result_count=len(papers),
                data=json.dumps(slim_papers, ensure_ascii=False),
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


class ExperimentUpdate(BaseModel):
    title: Optional[str] = None
    background: Optional[str] = None
    objective: Optional[str] = None
    setup: Optional[str] = None
    status: Optional[str] = None
    local_path: Optional[str] = None
    repo_url: Optional[str] = None
    readme_content: Optional[str] = None


class ResultCreate(BaseModel):
    description: str = ""
    parameters: dict = {}
    code_snippets: list = []
    result_data: str = ""
    conclusion: str = ""


class ResultUpdate(BaseModel):
    description: Optional[str] = None
    parameters: Optional[dict] = None
    code_snippets: Optional[list] = None
    result_data: Optional[str] = None
    conclusion: Optional[str] = None


@app.get("/api/experiments")
def list_experiments(search: str = "", status: str = ""):
    db = get_session()
    try:
        exps = experiment_service.get_experiments(db, search, status)
        return [{
            "id": e.id, "title": e.title, "status": e.status,
            "background": e.background, "objective": e.objective, "setup": e.setup,
            "local_path": e.local_path, "repo_url": e.repo_url,
            "readme_content": e.readme_content,
            "related_paper_ids": json.loads(e.related_paper_ids) if e.related_paper_ids else [],
            "ai_analysis": e.ai_analysis,
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


@app.patch("/api/experiments/{exp_id}")
def update_experiment(exp_id: str, body: ExperimentUpdate):
    db = get_session()
    try:
        exp = db.get(Experiment, exp_id)
        if not exp:
            raise HTTPException(404)
        for key, value in body.dict().items():
            if value is not None and hasattr(exp, key):
                setattr(exp, key, value)
        exp.updated_at = datetime.now()
        db.commit()
        db.refresh(exp)
        return {"id": exp.id, "title": exp.title, "status": exp.status}
    finally:
        db.close()


@app.put("/api/experiments/results/{result_id}")
def update_result(result_id: str, body: ResultUpdate):
    db = get_session()
    try:
        result = db.get(ExperimentResult, result_id)
        if not result:
            raise HTTPException(404)
        for key, value in body.dict().items():
            if value is not None:
                if key in ("parameters", "code_snippets") and isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                if hasattr(result, key):
                    setattr(result, key, value)
        db.commit()
        db.refresh(result)
        return {"id": result.id, "version": result.version}
    finally:
        db.close()


@app.delete("/api/experiments/results/{result_id}")
def delete_result(result_id: str):
    db = get_session()
    try:
        result = db.get(ExperimentResult, result_id)
        if not result:
            raise HTTPException(404)
        db.delete(result)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@app.get("/api/experiments/{exp_id}/params-table")
def get_params_table(exp_id: str):
    """获取参数对比表格数据"""
    db = get_session()
    try:
        exp = db.get(Experiment, exp_id)
        if not exp:
            raise HTTPException(404)
        results = experiment_service.get_results(db, exp_id)
        rows = []
        all_param_keys = set()
        for r in results:
            params = json.loads(r.parameters) if r.parameters else {}
            all_param_keys.update(params.keys())
            rows.append({
                "result_id": r.id,
                "version": r.version,
                "description": r.description,
                "params": params,
                "result_data": r.result_data,
                "conclusion": r.conclusion,
                "created_at": r.created_at.isoformat(),
            })
        return {
            "experiment_id": exp_id,
            "param_keys": sorted(all_param_keys),
            "rows": rows,
        }
    finally:
        db.close()


@app.post("/api/experiments/{exp_id}/ai-analysis")
def generate_experiment_analysis(exp_id: str):
    """AI 分析试验结果"""
    db = get_session()
    try:
        exp = db.get(Experiment, exp_id)
        if not exp:
            raise HTTPException(404)
        results = experiment_service.get_results(db, exp_id)

        # 构建分析上下文
        context = f"试验: {exp.title}\n背景: {exp.background}\n目标: {exp.objective}\n\n结果:\n"
        for r in results:
            params = json.loads(r.parameters) if r.parameters else {}
            context += f"v{r.version}: {r.description}\n"
            if params:
                context += f"  参数: {json.dumps(params, ensure_ascii=False)}\n"
            if r.result_data:
                context += f"  数据: {r.result_data[:500]}\n"
            if r.conclusion:
                context += f"  结论: {r.conclusion}\n"
            context += "\n"

        ai = get_ai()
        result = ai.chat([
            {"role": "system", "content": "你是科研试验分析助手。请分析以下试验数据，提供：1) 趋势分析 2) 异常检测 3) 优化建议。使用中文，Markdown格式。"},
            {"role": "user", "content": context[:6000]}
        ])

        analysis = result.get("content", "")
        exp.ai_analysis = analysis
        exp.updated_at = datetime.now()
        db.commit()
        return {"analysis": analysis}
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


@app.get("/api/knowledge/cards/{card_id}")
def get_card(card_id: str):
    db = get_session()
    try:
        card = knowledge_service.get_card(db, card_id)
        if not card:
            raise HTTPException(404, "Card not found")
        return {
            "id": card.id, "title": card.title, "summary": card.summary,
            "key_points": json.loads(card.key_points) if card.key_points else [],
            "source_type": card.source_type, "category_path": card.category_path,
            "star_rating": card.star_rating, "user_notes": card.user_notes,
            "created_at": card.created_at.isoformat(),
        }
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
#  文献库
# ══════════════════════════════════════════════════════════════

class PaperCreate(BaseModel):
    title: str
    authors: list[str] = []
    year: int = 0
    doi: str = ""
    abstract: str = ""
    journal: str = ""
    source: str = ""
    url: str = ""
    paper_type: str = "未知"
    star_rating: int = 0
    user_notes: str = ""
    tags: list[str] = []


class PaperUpdate(BaseModel):
    title: Optional[str] = None
    authors: Optional[list[str]] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    abstract: Optional[str] = None
    journal: Optional[str] = None
    star_rating: Optional[int] = None
    user_notes: Optional[str] = None
    tags: Optional[list[str]] = None


@app.get("/api/papers")
def list_papers(search: str = "", sort_by: str = "created_at",
                sort_order: str = "desc", year_from: int = 0,
                year_to: int = 0, star_min: int = 0):
    db = get_session()
    try:
        papers = paper_service.get_papers(db, search, sort_by, sort_order, year_from, year_to, star_min)
        return [_paper_to_dict(p) for p in papers]
    finally:
        db.close()


@app.post("/api/papers")
def create_paper(body: PaperCreate):
    db = get_session()
    try:
        from app.search.citation import format_gb
        citation = format_gb({
            "title": body.title, "authors": body.authors,
            "year": body.year, "doi": body.doi, "journal": body.journal,
            "paper_type": body.paper_type,
        }, 1)
        paper = paper_service.create_paper(
            db,
            title=body.title,
            authors=json.dumps(body.authors, ensure_ascii=False),
            year=body.year, doi=body.doi, abstract=body.abstract,
            journal=body.journal, source=body.source, url=body.url,
            paper_type=body.paper_type, star_rating=body.star_rating,
            user_notes=body.user_notes, citation=citation,
            tags=json.dumps(body.tags, ensure_ascii=False),
        )
        return _paper_to_dict(paper)
    finally:
        db.close()


@app.get("/api/papers/{paper_id}")
def get_paper(paper_id: str):
    db = get_session()
    try:
        paper = paper_service.get_paper(db, paper_id)
        if not paper:
            raise HTTPException(404, "Paper not found")
        return _paper_to_dict(paper)
    finally:
        db.close()


@app.patch("/api/papers/{paper_id}")
def update_paper(paper_id: str, body: PaperUpdate):
    db = get_session()
    try:
        kwargs = {k: v for k, v in body.dict().items() if v is not None}
        paper = paper_service.update_paper(db, paper_id, **kwargs)
        if not paper:
            raise HTTPException(404, "Paper not found")
        return _paper_to_dict(paper)
    finally:
        db.close()


@app.delete("/api/papers/{paper_id}")
def delete_paper(paper_id: str):
    db = get_session()
    try:
        ok = paper_service.delete_paper(db, paper_id)
        if not ok:
            raise HTTPException(404)
        return {"ok": True}
    finally:
        db.close()


@app.post("/api/papers/batch-delete")
def batch_delete_papers(body: dict):
    ids = body.get("ids", [])
    if not ids:
        raise HTTPException(400, "No IDs provided")
    db = get_session()
    try:
        count = paper_service.delete_papers_batch(db, ids)
        return {"deleted": count}
    finally:
        db.close()


@app.post("/api/papers/from-search")
def save_paper_from_search(body: dict):
    """从搜索结果入库"""
    db = get_session()
    try:
        paper = paper_service.save_from_search(db, body)
        return _paper_to_dict(paper)
    finally:
        db.close()


@app.get("/api/papers/{paper_id}/citation")
def get_paper_citation(paper_id: str, format: str = "gb7714", index: int = 1):
    """获取引用格式"""
    db = get_session()
    try:
        citation = paper_service.get_citation(db, paper_id, format, index)
        if not citation:
            raise HTTPException(404, "Paper not found")
        return {"citation": citation, "format": format}
    finally:
        db.close()


@app.post("/api/papers/{paper_id}/ai-summary")
def generate_paper_summary(paper_id: str):
    """生成 AI 摘要"""
    db = get_session()
    try:
        paper = paper_service.generate_ai_summary(db, paper_id, get_ai())
        if not paper:
            raise HTTPException(404, "Paper not found")
        return {"ai_summary": paper.ai_summary}
    finally:
        db.close()


@app.post("/api/papers/import-pdf")
async def import_paper_pdf(request: Request):
    """导入 PDF 到文献库"""
    import urllib.parse
    import tempfile
    import fitz

    filename_raw = request.headers.get("x-filename", "paper.pdf")
    filename = urllib.parse.unquote(filename_raw)
    file_bytes = await request.body()

    if not file_bytes or len(file_bytes) < 100:
        return {"error": f"File too small ({len(file_bytes) if file_bytes else 0} bytes)"}

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        doc = fitz.open(tmp_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()

        lines = [l.strip() for l in text.split("\n") if l.strip()]
        title = lines[0][:200] if lines else filename.replace(".pdf", "")

        # AI 提取元数据
        ai = get_ai()
        result = ai.chat([
            {"role": "system", "content": "你是学术文献分析助手。请从以下文本中提取文献元数据，用JSON返回：{\"title\":\"...\",\"authors\":[...],\"year\":2024,\"journal\":\"...\",\"doi\":\"...\",\"abstract\":\"...\",\"summary\":\"200字中文摘要\"}"},
            {"role": "user", "content": text[:4000]}
        ])

        import re
        json_match = re.search(r'\{[\s\S]*\}', result.get("content", ""))
        meta = {}
        if json_match:
            try:
                meta = json.loads(json_match.group())
            except:
                pass

        if not meta.get("title"):
            meta["title"] = title

        # 保存 PDF 文件
        pdf_dir = data_dir / "pdfs"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        import shutil
        import uuid as _uuid
        pdf_filename = f"{_uuid.uuid4().hex[:8]}_{filename}"
        pdf_path = pdf_dir / pdf_filename
        with open(pdf_path, "wb") as f:
            f.write(file_bytes)

        # 生成引用
        from app.search.citation import format_gb
        citation = format_gb(meta, 1)

        db = get_session()
        try:
            paper = paper_service.create_paper(
                db,
                title=meta.get("title", title)[:200],
                authors=json.dumps(meta.get("authors", []), ensure_ascii=False),
                year=meta.get("year", 0),
                doi=meta.get("doi", ""),
                abstract=meta.get("abstract", text[:1000]),
                journal=meta.get("journal", ""),
                source="pdf_import",
                paper_type="journal",
                citation=citation,
                ai_summary=meta.get("summary", ""),
                local_path=str(pdf_path),
            )
            return _paper_to_dict(paper)
        finally:
            db.close()
    except Exception as e:
        return {"error": str(e)}
    finally:
        os.unlink(tmp_path)


@app.get("/api/papers/stats")
def get_paper_stats():
    db = get_session()
    try:
        return paper_service.get_paper_stats(db)
    finally:
        db.close()


@app.get("/api/papers/search")
def search_papers_for_mention(q: str = "", limit: int = 10):
    """供 @引用使用的文献搜索"""
    db = get_session()
    try:
        papers = paper_service.get_papers(db, search=q)
        return [{"id": p.id, "title": p.title,
                 "authors": json.loads(p.authors) if p.authors else [],
                 "year": p.year} for p in papers[:limit]]
    finally:
        db.close()


def _paper_to_dict(p: Paper) -> dict:
    return {
        "id": p.id, "title": p.title,
        "authors": json.loads(p.authors) if p.authors else [],
        "year": p.year, "doi": p.doi, "abstract": p.abstract,
        "journal": p.journal, "source": p.source, "url": p.url,
        "citation": p.citation, "paper_type": p.paper_type,
        "has_fulltext": p.has_fulltext, "star_rating": p.star_rating,
        "user_notes": p.user_notes, "ai_summary": p.ai_summary,
        "local_path": p.local_path,
        "tags": json.loads(p.tags) if p.tags else [],
        "review_id": p.review_id,
        "created_at": p.created_at.isoformat(),
    }


# ══════════════════════════════════════════════════════════════
#  综述
# ══════════════════════════════════════════════════════════════

from app.models.review import Review


class ReviewGenerate(BaseModel):
    paper_ids: list[str]
    title: str = ""


@app.get("/api/reviews")
def list_reviews():
    db = get_session()
    try:
        reviews = db.query(Review).order_by(Review.created_at.desc()).all()
        return [{"id": r.id, "title": r.title, "content": r.content,
                 "paper_ids": json.loads(r.paper_ids) if r.paper_ids else [],
                 "created_at": r.created_at.isoformat()} for r in reviews]
    finally:
        db.close()


@app.get("/api/reviews/{review_id}")
def get_review(review_id: str):
    db = get_session()
    try:
        review = db.get(Review, review_id)
        if not review:
            raise HTTPException(404)
        return {"id": review.id, "title": review.title, "content": review.content,
                "paper_ids": json.loads(review.paper_ids) if review.paper_ids else [],
                "created_at": review.created_at.isoformat()}
    finally:
        db.close()


@app.post("/api/reviews/generate")
async def generate_review(body: ReviewGenerate):
    """AI 生成结构化综述"""
    db = get_session()
    try:
        papers = []
        for pid in body.paper_ids:
            p = db.get(Paper, pid)
            if p:
                papers.append({
                    "title": p.title,
                    "authors": json.loads(p.authors) if p.authors else [],
                    "year": p.year, "abstract": p.abstract,
                    "journal": p.journal, "ai_summary": p.ai_summary,
                })
    finally:
        db.close()

    if not papers:
        raise HTTPException(400, "No valid papers found")

    # 构建 prompt
    paper_texts = []
    for i, p in enumerate(papers, 1):
        text = f"[{i}] {p['title']}"
        if p.get("authors"):
            text += f" ({', '.join(p['authors'][:3])})"
        if p.get("year"):
            text += f", {p['year']}"
        if p.get("journal"):
            text += f" - {p['journal']}"
        if p.get("ai_summary"):
            text += f"\n摘要: {p['ai_summary']}"
        elif p.get("abstract"):
            text += f"\n摘要: {p['abstract'][:300]}"
        paper_texts.append(text)

    papers_context = "\n\n".join(paper_texts)
    title = body.title or "文献综述"

    prompt = f"""请基于以下 {len(papers)} 篇文献，撰写一篇结构化的文献综述。

文献列表：
{papers_context}

请按以下结构撰写（使用 Markdown 格式）：
## 引言
简述研究背景和本综述的范围

## 研究现状
概括各文献的主要研究内容和发现，引用时使用 [1] [2] 等标注

## 方法对比
对比各文献使用的研究方法

## 研究趋势
总结该领域的发展趋势和未来方向

## 结论
概括主要发现和研究意义

要求：
1. 每个部分都要引用具体文献（使用 [序号] 格式）
2. 语言学术、逻辑清晰
3. 使用中文撰写"""

    ai = get_ai()

    async def generate():
        full_content = ""
        for chunk in ai.stream_chat([
            {"role": "system", "content": "你是学术文献综述写作助手，擅长撰写结构化的文献综述。"},
            {"role": "user", "content": prompt}
        ]):
            if chunk["type"] == "content":
                full_content += chunk["data"]
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

        # 保存综述
        db = get_session()
        try:
            review = Review(
                title=title,
                content=full_content,
                paper_ids=json.dumps(body.paper_ids, ensure_ascii=False),
            )
            db.add(review)
            db.commit()

            # 更新关联文献的 review_id
            for pid in body.paper_ids:
                paper = db.get(Paper, pid)
                if paper:
                    paper.review_id = review.id
            db.commit()

            yield f"data: {json.dumps({'type': 'review_id', 'data': review.id}, ensure_ascii=False)}\n\n"
        finally:
            db.close()

        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.delete("/api/reviews/{review_id}")
def delete_review(review_id: str):
    db = get_session()
    try:
        review = db.get(Review, review_id)
        if not review:
            raise HTTPException(404)
        # 清除关联文献的 review_id
        papers = db.query(Paper).filter(Paper.review_id == review_id).all()
        for p in papers:
            p.review_id = ""
        db.delete(review)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════
#  AI 对话
# ══════════════════════════════════════════════════════════════

class SessionCreate(BaseModel):
    title: str = "新对话"
    category: str = "general"


class MessageCreate(BaseModel):
    content: str
    role: str = "user"


class ChatRequest(BaseModel):
    session_id: str
    model_id: str | None = None


@app.get("/api/chat/sessions")
def list_sessions(category: str = ""):
    db = get_session()
    try:
        sessions = chat_service.get_sessions(db)
        result = []
        for s in sessions:
            if category and s.category != category:
                continue
            result.append({"id": s.id, "title": s.title, "model_name": s.model_name,
                           "category": s.category,
                           "created_at": s.created_at.isoformat()})
        return result
    finally:
        db.close()


@app.post("/api/chat/sessions")
def create_session(body: SessionCreate):
    db = get_session()
    try:
        s = chat_service.create_session(db, body.title, body.category)
        return {"id": s.id, "title": s.title, "category": s.category}
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
        models = db.query(ModelConfig).filter(ModelConfig.is_active == True).all()
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
        # 重新加载 AI 路由器缓存
        get_ai().reload()
        return {"id": model.id, "name": model.name}
    finally:
        db.close()


@app.put("/api/models/{model_id}")
def update_model(model_id: str, body: dict):
    db = get_session()
    try:
        model = db.get(ModelConfig, model_id)
        if not model:
            raise HTTPException(404)
        for key in ["name", "base_url", "api_key", "model_name", "protocol", "purpose"]:
            if key in body and body[key]:
                setattr(model, key, body[key])
        db.commit()
        get_ai().reload()
        return {"id": model.id}
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
        get_ai().reload()
        return {"ok": True}
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════
#  搜索历史
# ══════════════════════════════════════════════════════════════

@app.post("/api/history")
def create_history(body: dict):
    """创建历史记录（综述/选题等）"""
    db = get_session()
    try:
        record = SearchHistory(
            query=body.get("query", "")[:200],
            history_type=body.get("type", "search"),
            result_count=body.get("result_count", 0),
            data=body.get("data", "{}"),
        )
        db.add(record)
        db.commit()
        return {"id": record.id}
    finally:
        db.close()


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


@app.delete("/api/history/{record_id}")
def delete_history(record_id: str):
    db = get_session()
    try:
        record = db.get(SearchHistory, record_id)
        if not record:
            raise HTTPException(404)
        db.delete(record)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════
#  启动
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
#  备份
# ══════════════════════════════════════════════════════════════

@app.post("/api/backup")
def manual_backup():
    from app.services.backup_service import create_backup
    result = create_backup("manual")
    return {"path": str(result) if result else None, "ok": bool(result)}


@app.get("/api/backups")
def list_backups():
    from app.services.backup_service import list_backups as _list
    return _list()


@app.post("/api/backups/restore")
def restore_backup(body: dict):
    path = body.get("path", "")
    if not path:
        raise HTTPException(status_code=400, detail="path is required")
    from app.services.backup_service import restore_backup as _restore
    result = _restore(path)
    if result:
        # 恢复后重新加载 AI 路由器（模型配置可能已变）
        get_ai().reload()
    return {"ok": bool(result)}


# ══════════════════════════════════════════════════════════════
#  导入
# ══════════════════════════════════════════════════════════════

@app.post("/api/knowledge/import/json")
def import_json(data: dict):
    """导入 JSON 数据（ai-literature 或 DeepSeek 格式）"""
    imported = 0
    db = get_session()
    try:
        # ai-literature 格式: {kbPapers: [...]}
        papers = data.get("kbPapers", data.get("papers", []))
        for p in papers:
            existing = db.query(KnowledgeCard).filter(KnowledgeCard.title == p.get("title", "")).first()
            if not existing:
                # 支持 ai-literature 完整字段
                summary = p.get("detailSummary", p.get("summary", p.get("abstract", "")))[:1000]
                key_points = p.get("key_points", p.get("keywords", []))
                # 构建 user_notes（包含元数据）
                notes_parts = []
                if p.get("authors"): notes_parts.append(f"作者: {', '.join(p['authors'][:5])}")
                if p.get("year"): notes_parts.append(f"年份: {p['year']}")
                if p.get("journal"): notes_parts.append(f"期刊: {p['journal']}")
                if p.get("doi"): notes_parts.append(f"DOI: {p['doi']}")
                if p.get("citation"): notes_parts.append(f"引用: {p['citation']}")
                user_notes = "\n".join(notes_parts)
                if p.get("userNotes"): user_notes += f"\n笔记: {p['userNotes']}"

                card = KnowledgeCard(
                    title=p.get("title", "")[:200],
                    summary=summary,
                    key_points=json.dumps(key_points, ensure_ascii=False),
                    source_type="literature",
                    star_rating=p.get("starRating", 0),
                    user_notes=user_notes[:2000],
                )
                db.add(card)
                imported += 1

        # DeepSeek 格式: {topics: [{sessions: [...]}]}
        topics = data.get("topics", [])
        for topic in topics:
            sessions = topic.get("sessions", []) if isinstance(topic, dict) else []
            for session in sessions:
                messages = session.get("messages", [])
                if not messages:
                    continue
                title = session.get("title", topic.get("title", "DeepSeek对话"))[:200]
                summary_parts = [m.get("content", "")[:300] for m in messages if m.get("role") == "assistant"]
                card = KnowledgeCard(
                    title=title,
                    summary="\n\n".join(summary_parts)[:2000],
                    source_type="deepseek",
                )
                db.add(card)
                imported += 1

        db.commit()
        return {"imported": imported}
    finally:
        db.close()


@app.post("/api/knowledge/import/pdf")
async def import_pdf(request: Request):
    """导入 PDF 文件，提取文本生成知识卡片"""
    import urllib.parse
    print("[pdf] import request received", flush=True)
    try:
        filename_raw = request.headers.get("x-filename", "document.pdf")
        filename = urllib.parse.unquote(filename_raw)
        file_bytes = await request.body()
        print(f"[pdf] received {len(file_bytes)} bytes for {filename}", flush=True)
    except Exception as e:
        print(f"[pdf] read error: {e}", flush=True)
        return {"error": f"Failed to read request: {type(e).__name__}: {e}"}
    if not file_bytes or len(file_bytes) < 100:
        return {"error": f"File too small or empty ({len(file_bytes) if file_bytes else 0} bytes)"}

    import tempfile
    import fitz  # PyMuPDF

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        doc = fitz.open(tmp_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()

        lines = [l.strip() for l in text.split("\n") if l.strip()]
        title = lines[0][:200] if lines else "导入的PDF"

        # 用 AI 生成摘要和关键点
        ai = get_ai()
        summary_result = ai.chat([
            {"role": "system", "content": "你是一个学术文献分析助手。请从以下文本中提取：1) 简短摘要(200字以内) 2) 3-5个关键点 3) 5个标签关键词。用JSON格式返回：{\"summary\": \"...\", \"key_points\": [...], \"tags\": [...]}"},
            {"role": "user", "content": text[:3000]}
        ])
        summary_content = summary_result.get("content", "")

        # 尝试解析 AI 返回的 JSON
        import re
        json_match = re.search(r'\{[\s\S]*\}', summary_content)
        ai_data = {}
        if json_match:
            try:
                ai_data = json.loads(json_match.group())
            except:
                pass

        db = get_session()
        try:
            card = KnowledgeCard(
                title=title,
                summary=ai_data.get("summary", text[:500]),
                key_points=json.dumps(ai_data.get("key_points", []), ensure_ascii=False),
                source_type="literature",
            )
            db.add(card)

            # 添加标签
            tags = ai_data.get("tags", [])
            for tag_name in tags:
                tag = db.get(Tag, tag_name)
                if not tag:
                    tag = Tag(name=tag_name, status="suggested", usage_count=0)
                    db.add(tag)
                tag.usage_count = (tag.usage_count or 0) + 1
                db.add(CardTag(card_id=card.id, tag_name=tag_name))

            db.commit()
            return {"imported": 1, "title": title, "tags": tags}
        finally:
            db.close()
    except Exception as e:
        return {"error": str(e)}
    finally:
        os.unlink(tmp_path)


@app.post("/api/knowledge/import/md")
async def import_markdown(data: dict):
    """导入 Markdown 文件，按 ## 标题分割生成知识卡片"""
    content = data.get("content", "")
    filename = data.get("filename", "导入的Markdown")

    if not content:
        return {"error": "No content provided"}

    # 按 ## 标题分割
    sections = []
    current_title = filename
    current_content = []

    for line in content.split("\n"):
        if line.startswith("## ") or line.startswith("# "):
            if current_content:
                sections.append({"title": current_title, "content": "\n".join(current_content)})
            current_title = line.lstrip("#").strip()
            current_content = []
        else:
            current_content.append(line)

    if current_content:
        sections.append({"title": current_title, "content": "\n".join(current_content)})

    # 为每个 section 创建知识卡片
    db = get_session()
    try:
        imported = 0
        for section in sections:
            if len(section["content"].strip()) < 50:  # 跳过太短的段落
                continue
            card = KnowledgeCard(
                title=section["title"][:200],
                summary=section["content"][:1000],
                source_type="manual",
            )
            db.add(card)
            imported += 1

        db.commit()
        return {"imported": imported}
    finally:
        db.close()


@app.post("/api/knowledge/generate")
def generate_card_from_text(data: dict):
    """从文本生成知识卡片（AI 处理）"""
    text = data.get("text", "")
    source_type = data.get("source_type", "manual")

    if not text:
        return {"error": "No text provided"}

    ai = get_ai()
    result = ai.chat([
        {"role": "system", "content": "你是一个知识管理助手。请从以下文本中提取：1) 标题 2) 简短摘要(200字以内) 3) 3-5个关键点 4) 5个标签。用JSON格式返回：{\"title\": \"...\", \"summary\": \"...\", \"key_points\": [...], \"tags\": [...]}"},
        {"role": "user", "content": text[:3000]}
    ])

    import re
    json_match = re.search(r'\{[\s\S]*\}', result.get("content", ""))
    ai_data = {}
    if json_match:
        try:
            ai_data = json.loads(json_match.group())
        except:
            pass

    if not ai_data:
        ai_data = {"title": text[:60], "summary": text[:300], "key_points": [], "tags": []}

    db = get_session()
    try:
        card = KnowledgeCard(
            title=ai_data.get("title", text[:60])[:200],
            summary=ai_data.get("summary", text[:300])[:1000],
            key_points=json.dumps(ai_data.get("key_points", []), ensure_ascii=False),
            source_type=source_type,
        )
        db.add(card)

        for tag_name in ai_data.get("tags", []):
            tag = db.get(Tag, tag_name)
            if not tag:
                tag = Tag(name=tag_name, status="suggested", usage_count=0)
                db.add(tag)
            tag.usage_count = (tag.usage_count or 0) + 1
            db.add(CardTag(card_id=card.id, tag_name=tag_name))

        db.commit()
        return {"id": card.id, "title": card.title, "tags": ai_data.get("tags", [])}
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    print(f"NEXUS_SERVER_READY:{args.port}", flush=True)
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
