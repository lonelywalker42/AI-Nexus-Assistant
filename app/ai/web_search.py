"""Web 搜索工具 — 调用 open-webSearch 聚合搜索引擎

通过本地 open-webSearch 守护进程（端口 3210）搜索，聚合 DuckDuckGo + Bing + Brave + Wikipedia + Arxiv。
守护进程未运行时返回空结果。
"""

import json
import logging

logger = logging.getLogger(__name__)

# open-webSearch 守护进程地址
_OWS_URL = "http://127.0.0.1:3210/search"
_OWS_TIMEOUT = 15.0


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """执行 Web 搜索，返回结果列表。

    每条结果包含: {"title": str, "url": str, "snippet": str, "engine": str}
    """
    try:
        import httpx
    except ImportError:
        return [{"title": "错误", "url": "", "snippet": "未安装 httpx 库", "engine": "error"}]

    try:
        resp = httpx.post(
            _OWS_URL,
            json={
                "query": query,
                "limit": max_results,
                "engines": ["bing"],
            },
            timeout=_OWS_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "ok" or not data.get("data"):
            msg = data.get("error", {}).get("message", "unknown")
            logger.warning(f"open-webSearch 返回错误: {msg}")
            return [{"title": "搜索失败", "url": "", "snippet": msg, "engine": "error"}]

        results = []
        for item in data["data"].get("results", [])[:max_results]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("description", ""),
                "engine": item.get("engine", "open-websearch"),
            })
        return results

    except httpx.ConnectError:
        logger.warning("open-webSearch 守护进程未运行 (port 3210)")
        return [{"title": "搜索服务未启动", "url": "", "snippet": "请确保 open-webSearch 守护进程已启动", "engine": "error"}]
    except Exception as e:
        logger.warning(f"open-webSearch 调用失败: {e}")
        return [{"title": "搜索失败", "url": "", "snippet": str(e), "engine": "error"}]


# ── 工具定义（OpenAI / Anthropic 格式）────────────────────────

TOOL_DEFINITION_OPENAI = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "搜索互联网获取最新信息。当用户询问实时信息、最新新闻、当前事件或你不确定的事实时使用此工具。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词，应简洁明确"
                },
                "max_results": {
                    "type": "integer",
                    "description": "返回结果数量，默认5",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    }
}

TOOL_DEFINITION_ANTHROPIC = {
    "name": "web_search",
    "description": "搜索互联网获取最新信息。当用户询问实时信息、最新新闻、当前事件或你不确定的事实时使用此工具。",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词，应简洁明确"
            },
            "max_results": {
                "type": "integer",
                "description": "返回结果数量，默认5",
                "default": 5
            }
        },
        "required": ["query"]
    }
}


def execute_tool_call(arguments: str | dict) -> str:
    """执行工具调用，返回格式化的搜索结果文本"""
    if isinstance(arguments, str):
        try:
            args = json.loads(arguments)
        except json.JSONDecodeError:
            return "错误：无法解析搜索参数"
    else:
        args = arguments

    query = args.get("query", "")
    max_results = args.get("max_results", 5)

    if not query:
        return "错误：缺少搜索关键词"

    results = web_search(query, max_results)

    if not results:
        return f"未找到与 \"{query}\" 相关的搜索结果。"

    lines = [f"搜索 \"{query}\" 的结果：\n"]
    for i, r in enumerate(results, 1):
        engine_tag = f" [{r.get('engine', '')}]" if r.get('engine') else ""
        lines.append(f"{i}. **{r['title']}**{engine_tag}")
        lines.append(f"   链接: {r['url']}")
        if r.get('snippet'):
            lines.append(f"   摘要: {r['snippet']}")
        lines.append("")

    return "\n".join(lines)
