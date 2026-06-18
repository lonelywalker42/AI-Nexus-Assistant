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
        logger.warning("open-webSearch 守护进程未运行 (port 3210)，尝试重启...")
        # 尝试自动重启搜索服务
        try:
            from app.ai.search_service import start_search_service
            if start_search_service():
                # 重启成功，重试搜索
                try:
                    resp = httpx.post(
                        _OWS_URL,
                        json={"query": query, "limit": max_results, "engines": ["bing"]},
                        timeout=_OWS_TIMEOUT,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    if data.get("status") == "ok" and data.get("data"):
                        results = []
                        for item in data["data"].get("results", [])[:max_results]:
                            results.append({
                                "title": item.get("title", ""),
                                "url": item.get("url", ""),
                                "snippet": item.get("description", ""),
                                "engine": item.get("engine", "open-websearch"),
                            })
                        return results
                except Exception as retry_err:
                    logger.warning(f"重启后重试搜索失败: {retry_err}")
        except Exception as restart_err:
            logger.warning(f"重启搜索服务失败: {restart_err}")
        return [{"title": "搜索服务未启动", "url": "", "snippet": "open-webSearch 守护进程不可用，请检查 Node.js 是否安装", "engine": "error"}]
    except Exception as e:
        logger.warning(f"open-webSearch 调用失败: {e}")
        return [{"title": "搜索失败", "url": "", "snippet": str(e), "engine": "error"}]


# ── 工具定义（OpenAI / Anthropic 格式）────────────────────────

TOOL_DEFINITION_OPENAI = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "搜索互联网获取最新信息。当用户询问实时信息、最新新闻、当前事件或你不确定的事实时使用此工具。收到搜索结果后，你必须仔细阅读每条结果的标题、链接和摘要内容，然后基于这些信息为用户提供全面、准确的回答。不要只告诉用户你搜索了什么，而要基于搜索结果回答用户的问题。",
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
    "description": "搜索互联网获取最新信息。当用户询问实时信息、最新新闻、当前事件或你不确定的事实时使用此工具。收到搜索结果后，你必须仔细阅读每条结果的标题、链接和摘要内容，然后基于这些信息为用户提供全面、准确的回答。不要只告诉用户你搜索了什么，而要基于搜索结果回答用户的问题。",
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
        return f"未找到与 \"{query}\" 相关的搜索结果。请尝试更换关键词重新搜索。"

    # 过滤掉错误结果
    valid_results = [r for r in results if r.get("engine") != "error"]
    if not valid_results:
        return f"搜索 \"{query}\" 未获得有效结果。请尝试更换关键词。"

    lines = [f"以下是搜索 \"{query}\" 获得的 {len(valid_results)} 条结果，请仔细阅读并基于这些内容回答用户问题：\n"]
    for i, r in enumerate(valid_results, 1):
        lines.append(f"[{i}] {r['title']}")
        if r.get('url'):
            lines.append(f"    来源: {r['url']}")
        if r.get('snippet'):
            lines.append(f"    内容: {r['snippet']}")
        lines.append("")

    lines.append("请基于以上搜索结果，为用户提供详细、准确的回答。引用具体来源。")
    return "\n".join(lines)
