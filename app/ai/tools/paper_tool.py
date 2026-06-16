"""query_papers 工具 — 按关键词/作者/年份检索文献库"""

import json
from app.db import get_session
from app.services import paper_service
from app.ai.tools import register_tool


def handle_query_papers(args_json: str) -> str:
    """执行文献库查询"""
    try:
        args = json.loads(args_json)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"}, ensure_ascii=False)

    search = args.get("query", "")
    year_from = args.get("year_from", 0)
    year_to = args.get("year_to", 0)
    star_min = args.get("star_min", 0)
    limit = args.get("limit", 10)

    db = get_session()
    try:
        papers = paper_service.get_papers(db, search=search, year_from=year_from, year_to=year_to, star_min=star_min)
        results = []
        for p in papers[:limit]:
            results.append({
                "id": p.id,
                "title": p.title,
                "authors": json.loads(p.authors) if p.authors else [],
                "year": p.year,
                "journal": p.journal,
                "abstract": (p.abstract or "")[:300],
                "ai_summary": (p.ai_summary or "")[:200],
                "star_rating": p.star_rating,
            })
        return json.dumps({"count": len(results), "papers": results}, ensure_ascii=False)
    finally:
        db.close()


register_tool(
    name="query_papers",
    description="从本地文献库中搜索学术论文。可按关键词、年份范围、评分筛选。返回匹配的论文列表（含标题、作者、年份、期刊、摘要）。",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词（匹配标题、作者、期刊、摘要）"
            },
            "year_from": {
                "type": "integer",
                "description": "起始年份（可选）"
            },
            "year_to": {
                "type": "integer",
                "description": "截止年份（可选）"
            },
            "star_min": {
                "type": "integer",
                "description": "最低评分 1-5（可选）"
            },
            "limit": {
                "type": "integer",
                "description": "返回结果数量上限，默认 10"
            }
        },
        "required": ["query"]
    },
    handler=handle_query_papers,
)
