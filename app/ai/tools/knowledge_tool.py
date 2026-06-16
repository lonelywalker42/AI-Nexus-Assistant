"""query_knowledge 工具 — 按关键词/标签检索知识库"""

import json
from app.db import get_session
from app.services import knowledge_service
from app.ai.tools import register_tool


def handle_query_knowledge(args_json: str) -> str:
    """执行知识库查询"""
    try:
        args = json.loads(args_json)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"}, ensure_ascii=False)

    search = args.get("query", "")
    tag = args.get("tag", "")
    source_type = args.get("source_type", "")
    limit = args.get("limit", 10)

    db = get_session()
    try:
        cards = knowledge_service.get_cards(db, search=search, tag=tag, source_type=source_type)
        results = []
        for c in cards[:limit]:
            tags = knowledge_service.get_card_tags(db, c.id)
            results.append({
                "id": c.id,
                "title": c.title,
                "summary": (c.summary or "")[:300],
                "key_points": json.loads(c.key_points) if c.key_points else [],
                "source_type": c.source_type,
                "star_rating": c.star_rating,
                "tags": [t.name for t in tags],
            })
        return json.dumps({"count": len(results), "cards": results}, ensure_ascii=False)
    finally:
        db.close()


register_tool(
    name="query_knowledge",
    description="从本地知识库中搜索知识卡片。可按关键词、标签、来源类型筛选。返回匹配的卡片列表（含标题、摘要、要点、标签）。",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词（匹配标题、摘要、笔记）"
            },
            "tag": {
                "type": "string",
                "description": "按标签筛选（可选）"
            },
            "source_type": {
                "type": "string",
                "description": "来源类型：literature/deepseek/manual（可选）"
            },
            "limit": {
                "type": "integer",
                "description": "返回结果数量上限，默认 10"
            }
        },
        "required": ["query"]
    },
    handler=handle_query_knowledge,
)
