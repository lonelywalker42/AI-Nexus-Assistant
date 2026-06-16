"""query_experiments 工具 — 按状态/关键词检索试验"""

import json
from app.db import get_session
from app.services import experiment_service
from app.ai.tools import register_tool


def handle_query_experiments(args_json: str) -> str:
    """执行试验查询"""
    try:
        args = json.loads(args_json)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"}, ensure_ascii=False)

    search = args.get("query", "")
    status = args.get("status", "")
    limit = args.get("limit", 10)

    db = get_session()
    try:
        exps = experiment_service.get_experiments(db, search, status)
        results = []
        for e in exps[:limit]:
            results.append({
                "id": e.id,
                "title": e.title,
                "status": e.status,
                "background": (e.background or "")[:200],
                "objective": (e.objective or "")[:200],
                "result_count": len(e.results),
                "local_path": e.local_path,
                "repo_url": e.repo_url,
            })
        return json.dumps({"count": len(results), "experiments": results}, ensure_ascii=False)
    finally:
        db.close()


register_tool(
    name="query_experiments",
    description="从本地试验管理系统中搜索试验记录。可按关键词和状态筛选。返回匹配的试验列表（含标题、状态、背景、目标、结果数量）。",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词（匹配标题、背景、目标）"
            },
            "status": {
                "type": "string",
                "description": "试验状态筛选：planning/running/completed/suspended（可选）"
            },
            "limit": {
                "type": "integer",
                "description": "返回结果数量上限，默认 10"
            }
        },
        "required": ["query"]
    },
    handler=handle_query_experiments,
)
