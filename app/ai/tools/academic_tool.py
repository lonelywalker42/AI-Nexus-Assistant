"""search_academic 工具 — 在线学术搜索（调用 UnifiedSearchEngine）"""

import json
from app.ai.tools import register_tool

# 延迟导入搜索引擎（避免启动时加载）
_search_engine = None


def _get_engine():
    global _search_engine
    if _search_engine is None:
        from app.search.engine import UnifiedSearchEngine
        _search_engine = UnifiedSearchEngine()
    return _search_engine


def handle_search_academic(args_json: str) -> str:
    """执行在线学术搜索"""
    try:
        args = json.loads(args_json)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"}, ensure_ascii=False)

    query = args.get("query", "")
    max_results = args.get("max_results", 10)

    if not query:
        return json.dumps({"error": "query is required"}, ensure_ascii=False)

    try:
        engine = _get_engine()
        results = engine.search(query, max_results=max_results)
        papers = []
        for p in results:
            papers.append({
                "title": p.title,
                "authors": p.authors[:5],
                "year": p.year,
                "journal": p.journal,
                "abstract": (p.abstract or "")[:300],
                "doi": p.doi,
                "source": p.source,
                "url": p.url,
            })
        return json.dumps({"count": len(papers), "papers": papers}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


register_tool(
    name="search_academic",
    description="在线搜索学术论文。使用多个学术数据源（OpenAlex、arXiv、Semantic Scholar、CrossRef、PubMed 等）并行搜索。返回论文列表（含标题、作者、年份、期刊、摘要、DOI）。",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词或查询字符串"
            },
            "max_results": {
                "type": "integer",
                "description": "最大返回结果数，默认 10"
            }
        },
        "required": ["query"]
    },
    handler=handle_search_academic,
)
