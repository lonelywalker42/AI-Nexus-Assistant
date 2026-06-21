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

    # 自动迁移：对比模型定义与实际数据库 schema，自动添加缺失列
    def _auto_migrate():
        import sqlite3
        try:
            from app.utils.paths import get_data_dir
            db_path = get_data_dir() / "nexus.db"
            if not db_path.exists():
                return
            conn = sqlite3.connect(str(db_path))

            # 导入所有模型，获取 ORM 定义的表结构
            from app.models.paper import Paper
            from app.models.chat import ChatSession, ChatMessage
            from app.models.experiment import Experiment, ExperimentResult

            models = [Paper, ChatSession, ChatMessage, Experiment, ExperimentResult]
            for model in models:
                try:
                    cursor = conn.execute(f"PRAGMA table_info({model.__tablename__})")
                    existing = {row[1] for row in cursor.fetchall()}
                    for col in model.__table__.columns:
                        if col.name not in existing:
                            typedef = str(col.type)
                            conn.execute(f"ALTER TABLE {model.__tablename__} ADD COLUMN {col.name} {typedef}")
                            print(f"[server] 迁移: 添加 {model.__tablename__}.{col.name}", flush=True)
                except Exception:
                    pass  # 表不存在时忽略

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[server] 自动迁移警告: {e}", flush=True)

    _auto_migrate()

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
#  行为埋点 & 研究洞察
# ══════════════════════════════════════════════════════════════

@app.post("/api/metrics/event")
def record_metric_event(data: dict):
    """记录行为事件"""
    from app.services import metrics_service
    db = get_session()
    try:
        metrics_service.record_event(
            db,
            category=data.get("category", ""),
            action=data.get("action", ""),
            target_id=data.get("target_id", ""),
            target_name=data.get("target_name", ""),
            **{k: v for k, v in data.items() if k not in ("category", "action", "target_id", "target_name")}
        )
        return {"status": "ok"}
    finally:
        db.close()


@app.get("/api/insights")
def get_insights():
    """获取研究洞察数据"""
    from app.services import metrics_service
    db = get_session()
    try:
        return {
            "hot_keywords": metrics_service.get_hot_keywords(db, top_k=15),
            "most_read": metrics_service.get_most_read_papers(db, top_k=10),
            "weekly_trend": metrics_service.get_weekly_read_trend(db, weeks=12),
            "recent_reads": metrics_service.get_recent_reads(db, limit=15),
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


# ── 周计划 API ──

@app.get("/api/plans/current")
def get_current_plan():
    """获取当前周计划"""
    from app.services.task_service import get_current_plan as _get_current
    db = get_session()
    try:
        plan = _get_current(db)
        if not plan:
            return {"exists": False}
        tasks = [{
            "id": t.id, "date": t.date, "content": t.content,
            "completed": t.completed, "priority": t.priority,
            "category": t.category, "sort_order": t.sort_order,
        } for t in sorted(plan.tasks, key=lambda t: (t.sort_order, t.created_at))]
        return {
            "exists": True,
            "id": plan.id,
            "week_start": plan.week_start.isoformat(),
            "week_end": plan.week_end.isoformat(),
            "tasks": tasks,
            "total": len(tasks),
            "done": sum(1 for t in plan.tasks if t.completed),
        }
    finally:
        db.close()


@app.post("/api/plans")
def create_plan(data: dict):
    """创建周计划"""
    from app.services.task_service import create_plan as _create
    db = get_session()
    try:
        week_start_str = data.get("week_start")
        if week_start_str:
            week_start = date.fromisoformat(week_start_str)
        else:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
        tasks_data = data.get("tasks", [])
        plan = _create(db, week_start, tasks_data if tasks_data else None)
        return {"id": plan.id, "week_start": plan.week_start.isoformat()}
    finally:
        db.close()


@app.post("/api/plans/{plan_id}/copy")
def copy_plan(plan_id: str):
    """复制周计划到下一周"""
    from app.services.task_service import copy_plan_to_next_week
    db = get_session()
    try:
        new_plan = copy_plan_to_next_week(db, plan_id)
        if not new_plan:
            return {"error": "Plan not found"}
        return {"id": new_plan.id, "week_start": new_plan.week_start.isoformat()}
    finally:
        db.close()


@app.post("/api/tasks/{task_id}/complete-with-date")
def complete_task_with_date(task_id: str, data: dict):
    """用指定日期完成任务（确认完成日期）"""
    db = get_session()
    try:
        task = db.get(Task, task_id)
        if not task:
            return {"error": "Task not found"}
        complete_date = data.get("date", date.today().isoformat())
        task.completed = True
        task.completed_at = datetime.fromisoformat(complete_date + "T00:00:00") if isinstance(complete_date, str) else datetime.now()
        db.commit()
        db.refresh(task)
        return {
            "id": task.id, "completed": task.completed,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }
    finally:
        db.close()


@app.patch("/api/tasks/{task_id}")
def update_task(task_id: str, data: dict):
    """更新任务字段"""
    db = get_session()
    try:
        task = db.get(Task, task_id)
        if not task:
            return {"error": "Task not found"}
        for key in ["content", "priority", "category", "completed", "date"]:
            if key in data:
                setattr(task, key, data[key])
        db.commit()
        db.refresh(task)
        return {
            "id": task.id, "date": task.date, "content": task.content,
            "completed": task.completed, "priority": task.priority,
            "category": task.category or "general",
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }
    finally:
        db.close()


@app.get("/api/tasks/week")
def get_week_tasks(start: str = ""):
    """获取一周的任务（用于日历悬停预览）"""
    db = get_session()
    try:
        if not start:
            today = date.today()
            start_date = today - timedelta(days=today.weekday())
        else:
            start_date = date.fromisoformat(start)
        dates = [(start_date + timedelta(days=i)).isoformat() for i in range(7)]
        result = {}
        for d in dates:
            tasks = task_service.get_all_todos_by_date(db, d)
            result[d] = [{
                "id": t.id, "content": t.content, "completed": t.completed,
                "priority": t.priority, "category": t.category,
            } for t in tasks]
        return result
    finally:
        db.close()


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

            # 记录搜索行为埋点
            from app.services import metrics_service
            metrics_service.record_search(db, body.query,
                                         source=",".join(body.sources) if body.sources else "all",
                                         result_count=len(papers))
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


@app.get("/api/experiments/{exp_id}/git/status")
def experiment_git_status(exp_id: str):
    """获取试验项目的 Git 状态"""
    import subprocess
    db = get_session()
    try:
        exp = db.get(Experiment, exp_id)
        if not exp:
            return {"error": "Experiment not found"}
        local_path = exp.local_path or ""
        if not local_path or not os.path.isdir(local_path):
            return {"has_git": False, "reason": "项目路径不存在"}

        try:
            # Check if it's a git repo
            subprocess.run(["git", "rev-parse", "--git-dir"],
                          cwd=local_path, capture_output=True, check=True, timeout=5)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return {"has_git": False, "reason": "不是Git仓库"}

        try:
            # Get branch
            branch_result = subprocess.run(["git", "branch", "--show-current"],
                                          cwd=local_path, capture_output=True, text=True, timeout=5)
            branch = branch_result.stdout.strip() or "detached"

            # Get last commit
            log_result = subprocess.run(["git", "log", "-1", "--format=%H%n%h%n%s%n%ai"],
                                       cwd=local_path, capture_output=True, text=True, timeout=5)
            commit_lines = log_result.stdout.strip().split("\n") if log_result.stdout.strip() else []
            commit_hash = commit_lines[0] if len(commit_lines) > 0 else ""
            commit_short = commit_lines[1] if len(commit_lines) > 1 else ""
            commit_msg = commit_lines[2] if len(commit_lines) > 2 else ""
            commit_date = commit_lines[3] if len(commit_lines) > 3 else ""

            # Get dirty status
            status_result = subprocess.run(["git", "status", "--porcelain"],
                                          cwd=local_path, capture_output=True, text=True, timeout=5)
            dirty_files = len(status_result.stdout.strip().split("\n")) if status_result.stdout.strip() else 0

            return {
                "has_git": True,
                "branch": branch,
                "commit_hash": commit_hash,
                "commit_short": commit_short,
                "commit_message": commit_msg,
                "commit_date": commit_date,
                "dirty_files": dirty_files,
            }
        except Exception as e:
            return {"has_git": False, "reason": str(e)}
    finally:
        db.close()


@app.post("/api/experiments/{exp_id}/results/{result_id}/snapshot")
def snapshot_result(exp_id: str, result_id: str):
    """为试验结果关联当前 Git commit"""
    import subprocess
    db = get_session()
    try:
        exp = db.get(Experiment, exp_id)
        if not exp:
            return {"error": "Experiment not found"}
        result = db.get(ExperimentResult, result_id)
        if not result:
            return {"error": "Result not found"}

        local_path = exp.local_path or ""
        if not local_path or not os.path.isdir(local_path):
            return {"error": "项目路径不存在"}

        try:
            log_result = subprocess.run(["git", "log", "-1", "--format=%H%n%h%n%s"],
                                       cwd=local_path, capture_output=True, text=True, timeout=5)
            lines = log_result.stdout.strip().split("\n")
            commit_hash = lines[0] if len(lines) > 0 else ""
            commit_short = lines[1] if len(lines) > 1 else ""
            commit_msg = lines[2] if len(lines) > 2 else ""

            # Store in code_snippets as a git_snapshot entry
            snippets = json.loads(result.code_snippets or "[]")
            snippets.append({
                "type": "git_snapshot",
                "commit_hash": commit_hash,
                "commit_short": commit_short,
                "commit_message": commit_msg,
            })
            result.code_snippets = json.dumps(snippets, ensure_ascii=False)
            db.commit()

            return {"commit_short": commit_short, "commit_message": commit_msg}
        except Exception as e:
            return {"error": str(e)}
    finally:
        db.close()


@app.post("/api/experiments/{exp_id}/generate-readme")
def generate_readme(exp_id: str):
    """根据试验参数和结果自动生成 README.md"""
    db = get_session()
    try:
        exp = db.get(Experiment, exp_id)
        if not exp:
            return {"error": "Experiment not found"}

        results = db.query(ExperimentResult).filter(
            ExperimentResult.experiment_id == exp_id
        ).order_by(ExperimentResult.version).all()

        # Build README
        lines = [
            f"# {exp.title}",
            "",
            "## 背景",
            exp.background or "待补充",
            "",
            "## 目标",
            exp.objective or "待补充",
            "",
            "## 实验设置",
            exp.setup or "待补充",
            "",
            "## 试验结果",
            "",
            "| 版本 | 描述 | 参数 | 结论 |",
            "|------|------|------|------|",
        ]

        for r in results:
            params = json.loads(r.parameters) if r.parameters else {}
            param_str = ", ".join(f"{k}={v}" for k, v in params.items()) if params else "-"
            conclusion = (r.conclusion or "-")[:100]
            lines.append(f"| v{r.version} | {r.description or '-'} | {param_str} | {conclusion} |")

        if exp.ai_analysis:
            lines.extend(["", "## AI 分析", exp.ai_analysis])

        readme = "\n".join(lines)

        # Save to experiment
        exp.readme_content = readme
        exp.updated_at = datetime.now()
        db.commit()

        return {"readme": readme}
    finally:
        db.close()


@app.post("/api/experiments/{exp_id}/archive")
def archive_experiment(exp_id: str):
    """打包试验配置、参数、结果为可下载的JSON"""
    db = get_session()
    try:
        exp = db.get(Experiment, exp_id)
        if not exp:
            return {"error": "Experiment not found"}

        results = db.query(ExperimentResult).filter(
            ExperimentResult.experiment_id == exp_id
        ).order_by(ExperimentResult.version).all()

        archive = {
            "experiment": {
                "title": exp.title,
                "background": exp.background,
                "objective": exp.objective,
                "setup": exp.setup,
                "status": exp.status,
                "local_path": exp.local_path,
                "repo_url": exp.repo_url,
                "created_at": exp.created_at.isoformat(),
            },
            "results": [{
                "version": r.version,
                "description": r.description,
                "parameters": json.loads(r.parameters) if r.parameters else {},
                "result_data": r.result_data,
                "conclusion": r.conclusion,
                "code_snippets": json.loads(r.code_snippets) if r.code_snippets else [],
                "created_at": r.created_at.isoformat(),
            } for r in results],
            "ai_analysis": exp.ai_analysis,
            "exported_at": datetime.now().isoformat(),
        }

        return {"archive": archive}
    finally:
        db.close()


@app.post("/api/chat/sessions/{session_id}/export")
def export_chat_session(session_id: str):
    """导出对话为研究笔记 Markdown"""
    db = get_session()
    try:
        session = db.get(ChatSession, session_id)
        if not session:
            return {"error": "Session not found"}

        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at).all()

        lines = [f"# {session.title}", f"\n> 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]

        for msg in messages:
            role = "**You**" if msg.role == "user" else "**AI**"
            lines.append(f"## {role}\n")
            if msg.thinking_content:
                lines.append(f"<details><summary>Thinking</summary>\n\n{msg.thinking_content}\n\n</details>\n")
            lines.append(f"{msg.content}\n")

        content = "\n".join(lines)
        return {"content": content, "title": session.title}
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
def list_cards(search: str = "", category: str = "", tag: str = "", source_type: str = "",
               sort_by: str = "updated_at", sort_order: str = "desc", star_min: int = 0):
    db = get_session()
    try:
        cards = knowledge_service.get_cards(db, search, category, tag, source_type)
        # Apply star rating filter
        if star_min > 0:
            cards = [c for c in cards if (c.star_rating or 0) >= star_min]
        # Apply sorting
        reverse = sort_order == "desc"
        if sort_by == "title":
            cards.sort(key=lambda c: c.title or "", reverse=reverse)
        elif sort_by == "star_rating":
            cards.sort(key=lambda c: c.star_rating or 0, reverse=reverse)
        else:  # updated_at or created_at
            cards.sort(key=lambda c: getattr(c, sort_by, c.updated_at) or c.updated_at, reverse=reverse)
        # Get tags for each card
        result = []
        for c in cards:
            card_tags = knowledge_service.get_card_tags(db, c.id)
            result.append({
                "id": c.id, "title": c.title, "summary": c.summary,
                "key_points": json.loads(c.key_points) if c.key_points else [],
                "source_type": c.source_type, "category_path": c.category_path,
                "star_rating": c.star_rating, "user_notes": c.user_notes,
                "tags": [t.tag_name for t in card_tags],
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat() if c.updated_at else c.created_at.isoformat(),
            })
        return result
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


@app.get("/api/papers/stats")
def get_paper_stats():
    db = get_session()
    try:
        return paper_service.get_paper_stats(db)
    finally:
        db.close()


@app.get("/api/papers/fts-search")
def fts_search_papers(q: str = "", limit: int = 50):
    """FTS5 全文搜索文献（比 LIKE 查询更快）"""
    if not q.strip():
        return {"papers": [], "count": 0}
    db = get_session()
    try:
        from app.search.fts import search_papers_fts
        results = search_papers_fts(db, q, limit)
        return {"papers": results, "count": len(results)}
    finally:
        db.close()


@app.get("/api/papers/hybrid-search")
def hybrid_search_papers(q: str = "", limit: int = 20):
    """混合搜索（FTS5 + 向量 RRF 融合）"""
    if not q.strip():
        return {"papers": [], "count": 0}
    db = get_session()
    try:
        from app.search.hybrid import search_with_fallback
        results = search_with_fallback(db, q, top_k=limit)
        return {"papers": results, "count": len(results)}
    finally:
        db.close()


@app.post("/api/papers/build-vectors")
def build_paper_vectors(model: str = "all-MiniLM-L6-v2", rebuild: bool = False):
    """构建论文向量索引"""
    db = get_session()
    try:
        from app.search.vectors import build_vectors
        from app.utils.paths import get_data_dir
        result = build_vectors(db, str(get_data_dir() / "pdfs"), model_name=model, rebuild=rebuild)
        return result
    finally:
        db.close()


@app.get("/api/papers/export")
def export_papers(fmt: str = "bibtex", ids: str = ""):
    """批量导出文献（BibTeX / RIS）"""
    db = get_session()
    try:
        from app.models.paper import Paper
        id_list = [i.strip() for i in ids.split(",") if i.strip()] if ids else []
        if id_list:
            papers = db.query(Paper).filter(Paper.id.in_(id_list)).all()
        else:
            papers = db.query(Paper).all()

        if not papers:
            return {"content": "", "count": 0, "format": fmt}

        if fmt == "bibtex":
            content = _export_bibtex(papers)
        elif fmt == "ris":
            content = _export_ris(papers)
        else:
            content = _export_bibtex(papers)

        return {"content": content, "count": len(papers), "format": fmt}
    finally:
        db.close()


@app.get("/api/papers/search")
def search_papers_for_mention(q: str = "", limit: int = 10):
    """供 @引用使用的文献搜索"""
    db = get_session()
    try:
        papers = paper_service.get_papers(db, search=q)
        def _safe_authors(s):
            if not s:
                return []
            try:
                return json.loads(s)
            except (json.JSONDecodeError, TypeError):
                return []
        return [{"id": p.id, "title": p.title,
                 "authors": _safe_authors(p.authors),
                 "year": p.year} for p in papers[:limit]]
    finally:
        db.close()


@app.get("/api/papers/{paper_id}")
def get_paper(paper_id: str):
    db = get_session()
    try:
        paper = paper_service.get_paper(db, paper_id)
        if not paper:
            raise HTTPException(404, "Paper not found")
        # 记录阅读行为埋点
        from app.services import metrics_service
        metrics_service.record_paper_view(db, paper_id, paper.title)
        return _paper_to_dict(paper)
    finally:
        db.close()


@app.get("/api/papers/{paper_id}/pdf")
def get_paper_pdf(paper_id: str):
    """提供 PDF 文件流（用于 iframe 预览）"""
    from fastapi.responses import FileResponse
    db = get_session()
    try:
        paper = paper_service.get_paper(db, paper_id)
        if not paper or not paper.local_path:
            raise HTTPException(404, "PDF 文件不存在")
        import os
        if not os.path.exists(paper.local_path):
            raise HTTPException(404, "PDF 文件未找到")
        return FileResponse(paper.local_path, media_type="application/pdf")
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
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(400, str(e))
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
    """导入 PDF 到文献库 — 三级元数据提取（PyMuPDF → 正则 → AI）"""
    import urllib.parse
    import tempfile

    # 检查 fitz 可用性
    try:
        import fitz
    except ImportError:
        raise HTTPException(500, "PyMuPDF 未安装，请运行: pip install pymupdf")

    filename_raw = request.headers.get("x-filename", "paper.pdf")
    filename = urllib.parse.unquote(filename_raw)
    file_bytes = await request.body()

    if not file_bytes or len(file_bytes) < 100:
        raise HTTPException(400, f"文件太小 ({len(file_bytes) if file_bytes else 0} bytes)")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        # 第一级：PyMuPDF 内置元数据 + 正则提取
        from app.services.pdf_service import extract_pdf_metadata
        meta = extract_pdf_metadata(tmp_path)

        # 提取全文文本用于 AI 兜底
        doc = fitz.open(tmp_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()

        if not text.strip():
            raise HTTPException(400, "PDF 无法提取文本（可能是扫描版或纯图片 PDF）")

        lines = [l.strip() for l in text.split("\n") if l.strip()]
        fallback_title = lines[0][:200] if lines else filename.replace(".pdf", "")

        # 第二级：AI 提取元数据（补充缺失字段）
        need_ai = not meta.get("title") or not meta.get("authors") or not meta.get("abstract")
        if need_ai:
            ai = get_ai()
            system_prompt = """你是学术文献分析助手。请从以下学术论文文本中提取元数据。

要求：
1. 仔细阅读文本，提取准确的标题、作者、年份、期刊/会议名、DOI、摘要
2. 生成一段200字以内的中文摘要，概括研究目的、方法和主要发现
3. authors 应该是字符串数组，每个元素是"名 姓"格式
4. year 必须是整数
5. 必须返回纯JSON，不要添加任何其他文本或代码块标记

返回格式：
{"title":"...","authors":["FirstName LastName", "..."],"year":2024,"journal":"...","doi":"...","abstract":"...","summary":"中文摘要..."}"""

            result = ai.chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text[:8000]}
            ])
            ai_meta = _parse_ai_json(result.get("content", ""))

            # JSON 解析失败时重试
            if not ai_meta or not ai_meta.get("title"):
                retry_prompt = f"""请从以下文本中提取文献元数据，只返回纯JSON，不要包含```json```标记：
{{"title":"...","authors":["..."],"year":2024,"journal":"...","doi":"...","abstract":"...","summary":"..."}}

文本内容：
{text[:6000]}"""
                result2 = ai.chat([{"role": "user", "content": retry_prompt}])
                ai_meta = _parse_ai_json(result2.get("content", ""))

            # 合并：AI 结果补充缺失字段（不覆盖已提取的）
            for key in ["title", "authors", "year", "doi", "abstract", "journal"]:
                if key not in meta or not meta[key]:
                    if ai_meta.get(key):
                        meta[key] = ai_meta[key]
            if ai_meta.get("summary"):
                meta["summary"] = ai_meta["summary"]

        # 兜底标题
        if not meta.get("title"):
            meta["title"] = fallback_title

        # 确保 authors 是列表
        if isinstance(meta.get("authors"), str):
            meta["authors"] = [a.strip() for a in meta["authors"].split(",") if a.strip()]
        elif not isinstance(meta.get("authors"), list):
            meta["authors"] = []

        # 确保 year 是整数
        try:
            meta["year"] = int(meta.get("year", 0))
        except (ValueError, TypeError):
            meta["year"] = 0

        # DOI 去重检查
        doi = str(meta.get("doi", "")).strip().lower()
        if doi:
            db = get_session()
            try:
                from sqlalchemy import func
                existing = db.query(Paper).filter(func.lower(Paper.doi) == doi).first()
                if existing:
                    return _paper_to_dict(existing)
            finally:
                db.close()

        # 保存 PDF 文件
        pdf_dir = data_dir / "pdfs"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        import uuid as _uuid
        pdf_filename = f"{_uuid.uuid4().hex[:8]}_{filename}"
        pdf_path = pdf_dir / pdf_filename
        with open(pdf_path, "wb") as f:
            f.write(file_bytes)

        # 生成引用（容错）
        citation = ""
        try:
            from app.search.citation import format_gb
            citation = format_gb(meta, 1)
        except Exception:
            pass

        db = get_session()
        try:
            paper = paper_service.create_paper(
                db,
                title=str(meta.get("title", fallback_title))[:200],
                authors=json.dumps(meta.get("authors", []), ensure_ascii=False),
                year=meta.get("year", 0),
                doi=str(meta.get("doi", ""))[:200],
                abstract=str(meta.get("abstract", text[:1000]))[:10000],
                journal=str(meta.get("journal", ""))[:500],
                source="pdf_import",
                paper_type="journal",
                citation=citation,
                ai_summary=str(meta.get("summary", ""))[:2000],
                local_path=str(pdf_path),
            )
            return _paper_to_dict(paper)
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, str(e))
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _parse_ai_json(content: str) -> dict:
    """从 AI 返回内容中解析 JSON，支持纯 JSON 和 markdown 代码块"""
    import re
    if not content:
        return {}

    # 尝试1: 直接解析整个内容
    try:
        return json.loads(content.strip())
    except (json.JSONDecodeError, TypeError):
        pass

    # 尝试2: 从 markdown 代码块中提取 ```json ... ```
    code_block = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?\s*```', content)
    if code_block:
        try:
            return json.loads(code_block.group(1).strip())
        except (json.JSONDecodeError, TypeError):
            pass

    # 尝试3: 提取最外层 { ... }
    json_match = re.search(r'\{[\s\S]*\}', content)
    if json_match:
        try:
            return json.loads(json_match.group())
        except (json.JSONDecodeError, TypeError):
            pass

    return {}


@app.post("/api/topics/build")
def build_topics(min_topic_size: int = 3):
    """构建主题模型"""
    db = get_session()
    try:
        from app.search.topics import build_topics
        result = build_topics(db, min_topic_size=min_topic_size)
        return result
    finally:
        db.close()


@app.get("/api/topics")
def get_topics():
    """获取主题概览"""
    db = get_session()
    try:
        from app.search.topics import get_topic_overview
        return get_topic_overview(db)
    finally:
        db.close()


@app.get("/api/topics/{topic_id}/papers")
def get_topic_papers(topic_id: int):
    """获取主题下的论文"""
    db = get_session()
    try:
        from app.search.topics import get_topic_papers
        return {"papers": get_topic_papers(db, topic_id)}
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════
#  引用图谱
# ══════════════════════════════════════════════════════════════

@app.post("/api/citations/build")
def build_citations():
    """构建引用关系"""
    db = get_session()
    try:
        from app.services.citation_service import build_citations
        return build_citations(db)
    finally:
        db.close()


@app.get("/api/citations/{paper_id}/references")
def get_paper_references(paper_id: str):
    """获取论文的参考文献（正向引用）"""
    db = get_session()
    try:
        from app.services.citation_service import get_references
        return {"references": get_references(db, paper_id)}
    finally:
        db.close()


@app.get("/api/citations/{paper_id}/citing")
def get_paper_citing(paper_id: str):
    """获取引用此论文的其他论文（反向引用）"""
    db = get_session()
    try:
        from app.services.citation_service import get_citing_papers
        return {"citing": get_citing_papers(db, paper_id)}
    finally:
        db.close()


@app.get("/api/citations/stats")
def get_citation_stats():
    """获取引用统计"""
    db = get_session()
    try:
        from app.services.citation_service import get_citation_stats
        return get_citation_stats(db)
    finally:
        db.close()


@app.post("/api/citations/check")
def check_citations(data: dict):
    """检查文内引用"""
    text = data.get("text", "")
    if not text:
        return {"citations": []}
    db = get_session()
    try:
        import re
        from app.models.paper import Paper
        from sqlalchemy import func

        # 提取文内引用
        # 模式1: Author (Year)
        narrative = re.findall(r'([A-Z][a-z]+(?:\s+(?:and|&|et al\.?)\s+[A-Z][a-z]+)*)\s*\((\d{4})\)', text)
        # 模式2: (Author, Year)
        parenthetical = re.findall(r'\(([A-Z][a-z]+(?:\s+(?:and|&|et al\.?)\s+[A-Z][a-z]+)*),?\s*(\d{4})\)', text)

        citations = []
        for author, year in narrative + parenthetical:
            # 在库中查找
            papers = db.query(Paper).filter(
                Paper.authors.ilike(f"%{author}%"),
                Paper.year == int(year)
            ).all()

            status = "NOT_IN_LIBRARY"
            paper_id = None
            if papers:
                status = "VERIFIED"
                paper_id = papers[0].id

            citations.append({
                "author": author,
                "year": int(year),
                "status": status,
                "paper_id": paper_id,
            })

        return {"citations": citations}
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════
#  高级导出
# ══════════════════════════════════════════════════════════════

@app.post("/api/export/docx")
def export_docx(data: dict):
    """导出为 DOCX"""
    content = data.get("content", "")
    title = data.get("title", "文档")
    if not content:
        raise HTTPException(400, "内容不能为空")

    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp_path = tmp.name

    from app.services.export_service import export_docx
    result = export_docx(content, tmp_path, title)

    if result["status"] == "ok":
        from fastapi.responses import FileResponse
        return FileResponse(tmp_path, filename=f"{title}.docx",
                           media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    else:
        raise HTTPException(500, result.get("message", "导出失败"))


@app.get("/api/export/refs")
def export_refs(fmt: str = "gb7714", ids: str = ""):
    """导出参考文献列表"""
    db = get_session()
    try:
        from app.services.export_service import export_markdown_refs
        id_list = [i.strip() for i in ids.split(",") if i.strip()] if ids else None
        content = export_markdown_refs(db, id_list, style=fmt)
        return {"content": content, "count": content.count("\n") + 1 if content else 0, "format": fmt}
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════
#  工作区
# ══════════════════════════════════════════════════════════════

@app.get("/api/workspaces")
def list_workspaces():
    """获取所有工作区"""
    from app.services import workspace_service
    db = get_session()
    try:
        return {"workspaces": workspace_service.get_workspaces(db)}
    finally:
        db.close()


@app.post("/api/workspaces")
def create_workspace(data: dict):
    """创建工作区"""
    from app.services import workspace_service
    db = get_session()
    try:
        ws = workspace_service.create_workspace(
            db,
            name=data.get("name", "未命名工作区"),
            description=data.get("description", ""),
            paper_ids=data.get("paper_ids", []),
        )
        return ws
    finally:
        db.close()


@app.get("/api/workspaces/{workspace_id}")
def get_workspace(workspace_id: str):
    """获取单个工作区"""
    from app.services import workspace_service
    db = get_session()
    try:
        ws = workspace_service.get_workspace(db, workspace_id)
        if not ws:
            raise HTTPException(404, "工作区不存在")
        return ws
    finally:
        db.close()


@app.put("/api/workspaces/{workspace_id}")
def update_workspace(workspace_id: str, data: dict):
    """更新工作区"""
    from app.services import workspace_service
    db = get_session()
    try:
        ws = workspace_service.update_workspace(db, workspace_id, **data)
        if not ws:
            raise HTTPException(404, "工作区不存在")
        return ws
    finally:
        db.close()


@app.delete("/api/workspaces/{workspace_id}")
def delete_workspace(workspace_id: str):
    """删除工作区"""
    from app.services import workspace_service
    db = get_session()
    try:
        ok = workspace_service.delete_workspace(db, workspace_id)
        if not ok:
            raise HTTPException(404, "工作区不存在")
        return {"status": "ok"}
    finally:
        db.close()


@app.post("/api/workspaces/{workspace_id}/papers")
def add_papers_to_workspace(workspace_id: str, data: dict):
    """向工作区添加论文"""
    from app.services import workspace_service
    db = get_session()
    try:
        ws = workspace_service.add_papers_to_workspace(db, workspace_id, data.get("paper_ids", []))
        if not ws:
            raise HTTPException(404, "工作区不存在")
        return ws
    finally:
        db.close()


@app.delete("/api/workspaces/{workspace_id}/papers")
def remove_papers_from_workspace(workspace_id: str, data: dict):
    """从工作区移除论文"""
    from app.services import workspace_service
    db = get_session()
    try:
        ws = workspace_service.remove_papers_from_workspace(db, workspace_id, data.get("paper_ids", []))
        if not ws:
            raise HTTPException(404, "工作区不存在")
        return ws
    finally:
        db.close()


@app.get("/api/workspaces/{workspace_id}/papers")
def get_workspace_papers(workspace_id: str):
    """获取工作区中的论文"""
    from app.services import workspace_service
    db = get_session()
    try:
        papers = workspace_service.get_workspace_papers(db, workspace_id)
        return {"papers": papers, "count": len(papers)}
    finally:
        db.close()


@app.post("/api/papers/fts-rebuild")
def fts_rebuild():
    """重建 FTS5 全文索引"""
    db = get_session()
    try:
        from app.search.fts import rebuild_fts
        rebuild_fts(db)
        return {"status": "ok", "message": "FTS5 索引已重建"}
    finally:
        db.close()


def _paper_to_dict(p: Paper) -> dict:
    def _safe_json(s, default):
        if not s:
            return default
        try:
            return json.loads(s)
        except (json.JSONDecodeError, TypeError):
            return default

    return {
        "id": p.id, "title": p.title,
        "authors": _safe_json(p.authors, []),
        "year": p.year, "doi": p.doi, "abstract": p.abstract,
        "journal": p.journal, "source": p.source, "url": p.url,
        "citation": p.citation, "paper_type": p.paper_type,
        "has_fulltext": p.has_fulltext, "star_rating": p.star_rating,
        "user_notes": p.user_notes, "ai_summary": p.ai_summary,
        "local_path": p.local_path,
        "tags": _safe_json(p.tags, []),
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


@app.post("/api/backups/import-db")
async def import_db_file(request: Request):
    """导入 .db 文件恢复数据

    支持两种格式：
    1. 单个 .db 文件（向后兼容）
    2. .zip 包含 nexus.db + nexus.db-wal + nexus.db-shm（推荐）
    """
    import tempfile
    import zipfile
    import io

    file_bytes = await request.body()
    if not file_bytes or len(file_bytes) < 100:
        raise HTTPException(400, "文件太小或为空")

    tmp_dir = tempfile.mkdtemp(prefix="nexus_restore_")

    try:
        # 判断是 zip 还是单个 db
        if zipfile.is_zipfile(io.BytesIO(file_bytes)):
            # ZIP 模式：解压 .db、.db-wal、.db-shm
            with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as zf:
                names = zf.namelist()
                # 找到 .db 文件
                db_name = None
                for n in names:
                    if n.endswith(".db") and not n.endswith(".db-wal") and not n.endswith(".db-shm"):
                        db_name = n
                        break
                if not db_name:
                    raise HTTPException(400, "ZIP 中未找到 .db 文件")

                # 解压所有 db 相关文件
                zf.extractall(tmp_dir)

            # 验证 .db 文件
            db_file = os.path.join(tmp_dir, db_name)
            with open(db_file, "rb") as f:
                header = f.read(16)
            if b"SQLite format" not in header:
                raise HTTPException(400, "不是有效的 SQLite 数据库文件")

            from app.services.backup_service import restore_backup as _restore
            result = _restore(db_file)
        else:
            # 单文件模式（向后兼容）
            header = file_bytes[:16]
            if b"SQLite format" not in header:
                raise HTTPException(400, "不是有效的 SQLite 数据库文件")

            db_file = os.path.join(tmp_dir, "nexus.db")
            with open(db_file, "wb") as f:
                f.write(file_bytes)

            from app.services.backup_service import restore_backup as _restore
            result = _restore(db_file)

        if result:
            get_ai().reload()
        return {"ok": bool(result)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.get("/api/backups/export-db")
def export_db_file():
    """导出数据库为 zip 文件（包含 .db + .db-wal + .db-shm）"""
    import zipfile
    import io
    from fastapi.responses import StreamingResponse

    from app.utils.paths import get_data_dir
    db_path = get_data_dir() / "nexus.db"
    if not db_path.exists():
        raise HTTPException(404, "数据库文件不存在")

    # 先 checkpoint，尽量减小 WAL
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path), timeout=5)
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()
    except Exception:
        pass

    # 创建 zip 包
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(db_path, "nexus.db")
        for suffix in ["-wal", "-shm"]:
            f = db_path.with_suffix(db_path.suffix + suffix)
            if f.exists() and f.stat().st_size > 0:
                zf.write(f, f.name)

    zip_buf.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"nexus_backup_{timestamp}.zip"

    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ══════════════════════════════════════════════════════════════
#  搜索服务控制
# ══════════════════════════════════════════════════════════════

@app.get("/api/search-service/status")
def search_service_status():
    """检查搜索服务状态"""
    from app.ai.search_service import is_search_service_running
    return {"running": is_search_service_running()}


@app.post("/api/search-service/start")
def search_service_start():
    """启动搜索服务"""
    from app.ai.search_service import start_search_service, _find_node, _find_open_websearch_dir
    node = _find_node()
    ows_dir = _find_open_websearch_dir()
    if not node:
        return {"ok": False, "running": False, "error": "未找到 Node.js，请安装后重启应用"}
    if not ows_dir:
        return {"ok": False, "running": False, "error": "未找到 open-webSearch 目录"}
    ok = start_search_service()
    return {"ok": ok, "running": ok}


@app.post("/api/search-service/stop")
def search_service_stop():
    """停止搜索服务"""
    from app.ai.search_service import stop_search_service, is_search_service_running
    stop_search_service()
    return {"ok": True, "running": is_search_service_running()}


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


# ── 写作工作台 API ──

@app.get("/api/writing/documents")
def list_writing_documents(document_type: str = None):
    """列出写作文档"""
    from app.services.writing_service import list_documents
    db = get_session()
    try:
        docs = list_documents(db, document_type)
        return {"documents": [{
            "id": d.id, "title": d.title, "document_type": d.document_type,
            "word_count": d.word_count, "created_at": d.created_at.isoformat(),
            "updated_at": d.updated_at.isoformat(),
        } for d in docs]}
    finally:
        db.close()


@app.post("/api/writing/documents")
def create_writing_document(data: dict):
    """创建写作文档"""
    from app.services.writing_service import create_document
    db = get_session()
    try:
        doc = create_document(
            db,
            title=data.get("title", "无标题文档"),
            content=data.get("content", ""),
            document_type=data.get("document_type", "paper"),
            linked_paper_ids=data.get("linked_paper_ids", []),
        )
        return {"id": doc.id, "title": doc.title}
    finally:
        db.close()


@app.get("/api/writing/documents/{doc_id}")
def get_writing_document(doc_id: str):
    """获取写作文档"""
    from app.services.writing_service import get_document
    db = get_session()
    try:
        doc = get_document(db, doc_id)
        if not doc:
            return {"error": "Document not found"}
        import json
        return {
            "id": doc.id, "title": doc.title, "content": doc.content,
            "outline": json.loads(doc.outline or "[]"),
            "linked_paper_ids": json.loads(doc.linked_paper_ids or "[]"),
            "document_type": doc.document_type, "word_count": doc.word_count,
            "created_at": doc.created_at.isoformat(),
            "updated_at": doc.updated_at.isoformat(),
        }
    finally:
        db.close()


@app.patch("/api/writing/documents/{doc_id}")
def update_writing_document(doc_id: str, data: dict):
    """更新写作文档"""
    from app.services.writing_service import update_document
    db = get_session()
    try:
        doc = update_document(db, doc_id, **data)
        if not doc:
            return {"error": "Document not found"}
        return {"id": doc.id, "title": doc.title, "word_count": doc.word_count}
    finally:
        db.close()


@app.delete("/api/writing/documents/{doc_id}")
def delete_writing_document(doc_id: str):
    """删除写作文档"""
    from app.services.writing_service import delete_document
    db = get_session()
    try:
        ok = delete_document(db, doc_id)
        return {"success": ok}
    finally:
        db.close()


@app.post("/api/writing/documents/{doc_id}/link-paper")
def link_paper_to_document(doc_id: str, data: dict):
    """关联文献到文档"""
    from app.services.writing_service import link_paper
    db = get_session()
    try:
        doc = link_paper(db, doc_id, data.get("paper_id", ""))
        if not doc:
            return {"error": "Document not found"}
        return {"id": doc.id, "linked_paper_ids": json.loads(doc.linked_paper_ids)}
    finally:
        db.close()


@app.post("/api/writing/documents/{doc_id}/ai")
def writing_ai_operation(doc_id: str, data: dict):
    """写作 AI 操作（润色/翻译/扩写/缩写）"""
    from app.services.writing_service import get_document, update_document
    db = get_session()
    try:
        doc = get_document(db, doc_id)
        if not doc:
            return {"error": "Document not found"}

        operation = data.get("operation", "polish")  # polish/translate/expand/condense/latex
        text = data.get("text", doc.content)
        if not text:
            return {"error": "No text to process"}

        prompts = {
            "polish": "请对以下学术文本进行润色，保持原意的同时提升语言表达的学术性和流畅度。使用准确的学术术语，保持逻辑连贯，避免口语化表达。只返回润色后的文本，不要解释。",
            "translate": "请将以下文本翻译为学术英语/中文（根据源语言自动判断方向）。使用准确的学术术语，保持句式地道。只返回翻译后的文本，不要解释。",
            "expand": "请将以下文本进行学术性扩写，补充必要的细节、论证和过渡，使论述更加完整和严谨。只返回扩写后的文本，不要解释。",
            "condense": "请将以下文本精简，保留核心观点和关键信息，去除冗余表述。只返回精简后的文本，不要解释。",
            "latex": "请将以下文本转换为 LaTeX 格式。数学公式转为 $...$ 或 \\[...\\]，结构转为 section/subsection，列表转为 enumerate/itemize。只返回 LaTeX 代码，不要解释。",
        }

        system_prompt = prompts.get(operation, prompts["polish"])
        ai = get_ai()
        result = ai.chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text[:8000]}
        ])

        return {"result": result.get("content", ""), "operation": operation}
    finally:
        db.close()


# ── 增强的文献检索 API ──

@app.post("/api/search/enhanced")
def enhanced_search(req: dict):
    """布尔逻辑搜索"""
    groups = req.get("groups", [])
    sources = req.get("sources", ["openalex", "arxiv", "semantic_scholar"])
    max_results = req.get("max_results", 50)

    if not groups:
        return {"papers": [], "count": 0}

    # Build boolean query string
    query_parts = []
    for g in groups:
        keywords = g.get("keywords", [])
        field = g.get("field", "all")
        op = g.get("operator", "AND")
        if not keywords:
            continue
        part = " ".join(keywords)
        if op == "NOT":
            query_parts.append(f"NOT ({part})")
        else:
            query_parts.append(f"({part})")

    # Join with AND between groups
    query = " AND ".join(query_parts)
    if not query:
        return {"papers": [], "count": 0}

    engine = get_search_engine()
    results = engine.search(query, sources=sources, max_results=max_results)
    return {"papers": results, "count": len(results), "query": query}


@app.post("/api/papers/batch-import")
def batch_import_papers(data: dict):
    """批量导入文献（从搜索结果）— DOI 优先去重"""
    papers_data = data.get("papers", [])
    db = get_session()
    try:
        imported = 0
        skipped = 0
        for p in papers_data:
            title = p.get("title", "")
            if not title:
                continue
            # DOI 去重（优先）
            doi = str(p.get("doi", "")).strip().lower()
            if doi:
                from sqlalchemy import func
                existing = db.query(Paper).filter(func.lower(Paper.doi) == doi).first()
                if existing:
                    skipped += 1
                    continue
            # 标题去重（降级）
            existing = db.query(Paper).filter(Paper.title == title).first()
            if existing:
                skipped += 1
                continue
            paper_service.save_from_search(db, p)
            imported += 1
        return {"imported": imported, "skipped": skipped}
    finally:
        db.close()


# ── 增强的综述生成 API ──

@app.post("/api/reviews/smart-generate")
def smart_review_generate(data: dict):
    """智能综述生成（支持自定义结构）"""
    paper_ids = data.get("paper_ids", [])
    title = data.get("title", "文献综述")
    sections = data.get("sections", ["研究背景", "研究现状", "方法对比", "研究趋势", "关键结论"])

    db = get_session()
    try:
        papers = db.query(Paper).filter(Paper.id.in_(paper_ids)).all()
        if not papers:
            return {"error": "No papers found"}

        # Build paper context
        paper_context = []
        for i, p in enumerate(papers, 1):
            summary = p.ai_summary or p.abstract[:200] if p.abstract else ""
            authors = json.loads(p.authors) if p.authors else []
            author_str = ", ".join(authors[:3]) + ("等" if len(authors) > 3 else "")
            paper_context.append(f"[{i}] {p.title}\n作者: {author_str}\n年份: {p.year}\n期刊: {p.journal or 'N/A'}\n摘要: {summary}")

        papers_text = "\n\n".join(paper_context)
        sections_text = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(sections))

        prompt = f"""请基于以下文献，撰写一篇结构化的综述文章。

文献列表：
{papers_text}

综述标题：{title}

请按照以下结构撰写（使用 Markdown 二级标题）：
{sections_text}

要求：
1. 每个部分都要引用具体文献，使用 [数字] 格式标注
2. 保持学术性语言，逻辑清晰
3. 在"研究趋势"部分要指出未来可能的研究方向
4. 总字数控制在 2000-4000 字"""

        ai = get_ai()
        full_content = ""
        for chunk in ai.stream_chat([
            {"role": "system", "content": "你是一个专业的学术综述撰写助手。"},
            {"role": "user", "content": prompt}
        ]):
            if chunk.get("type") == "content":
                full_content += chunk.get("data", "")

        # Save review
        from app.models.review import Review
        review = Review(title=title, content=full_content, paper_ids=json.dumps(paper_ids))
        db.add(review)
        db.commit()
        db.refresh(review)

        return {"id": review.id, "title": title, "content": full_content}
    finally:
        db.close()


# ── 知识库增强导入 API ──

@app.post("/api/knowledge/import/url")
def import_from_url(data: dict):
    """从网页 URL 导入知识卡片"""
    url = data.get("url", "")
    if not url:
        return {"error": "No URL provided"}

    try:
        import httpx
        resp = httpx.get(url, timeout=30, follow_redirects=True, proxy=None)
        resp.raise_for_status()
        html = resp.text

        # Simple content extraction
        import re
        # Remove script/style tags
        html = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', html, flags=re.IGNORECASE)
        html = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', html, flags=re.IGNORECASE)
        # Extract title
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else url
        # Extract text content
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()

        if len(text) < 50:
            return {"error": "Could not extract meaningful content"}

        # Use AI to generate card
        ai = get_ai()
        result = ai.chat([
            {"role": "system", "content": "你是一个知识管理助手。请从以下网页内容中提取：1) 标题 2) 简短摘要(200字以内) 3) 3-5个关键点 4) 5个标签。用JSON格式返回：{\"title\": \"...\", \"summary\": \"...\", \"key_points\": [...], \"tags\": [...]}"},
            {"role": "user", "content": text[:3000]}
        ])

        json_match = re.search(r'\{[\s\S]*\}', result.get("content", ""))
        ai_data = {}
        if json_match:
            try:
                ai_data = json.loads(json_match.group())
            except:
                pass

        if not ai_data:
            ai_data = {"title": title[:60], "summary": text[:300], "key_points": [], "tags": []}

        db = get_session()
        try:
            card = KnowledgeCard(
                title=ai_data.get("title", title[:60])[:200],
                summary=ai_data.get("summary", text[:300])[:1000],
                key_points=json.dumps(ai_data.get("key_points", []), ensure_ascii=False),
                source_type="web",
                user_notes=f"来源: {url}",
            )
            db.add(card)
            db.commit()
            db.refresh(card)
            return {"id": card.id, "title": card.title}
        finally:
            db.close()
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    # 检测端口是否已被占用（旧实例未退出）
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", args.port))
        sock.close()
    except OSError:
        print(f"[server] 端口 {args.port} 已被占用，可能有旧实例在运行", flush=True)
        print(f"[server] 请先关闭旧实例，或使用 taskkill /F /IM nexus-server.exe", flush=True)
        # 不退出 — 让搜索服务继续运行，Tauri 前端会连接到旧实例
        # 但需要清理搜索服务（因为 atexit 会在 sys.exit 时触发）
        sys.exit(0)

    print(f"NEXUS_SERVER_READY:{args.port}", flush=True)
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
