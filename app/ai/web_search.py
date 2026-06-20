"""Web 搜索工具 — 调用 open-webSearch 聚合搜索引擎

通过本地 open-webSearch 守护进程（端口 3210）搜索，聚合 DuckDuckGo + Bing + Brave + Wikipedia + Arxiv。
守护进程未运行时返回空结果。

注意：系统可能配置了 HTTP 代理（如 Clash），localhost 请求必须绕过代理。
"""

import json
import logging

logger = logging.getLogger(__name__)

# open-webSearch 守护进程地址
_OWS_URL = "http://127.0.0.1:3210/search"
_OWS_TIMEOUT = 60.0


def _create_client():
    """创建 httpx 客户端，绕过代理访问 localhost"""
    import httpx
    try:
        return httpx.Client(proxy=None)
    except Exception:
        return httpx.Client()


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """执行 Web 搜索，返回结果列表。

    每条结果包含: {"title": str, "url": str, "snippet": str, "engine": str}
    """
    try:
        import httpx
    except ImportError:
        return [{"title": "错误", "url": "", "snippet": "未安装 httpx 库", "engine": "error"}]

    search_limit = max(max_results * 2, 10)
    client = _create_client()

    try:
        resp = client.post(
            _OWS_URL,
            json={"query": query, "limit": search_limit, "engines": ["bing", "duckduckgo"]},
            timeout=_OWS_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "ok" or not data.get("data"):
            msg = data.get("error", {}).get("message", "unknown")
            logger.warning(f"open-webSearch 返回错误: {msg}")
            return [{"title": "搜索失败", "url": "", "snippet": msg, "engine": "error"}]

        return _parse_results(data, max_results)

    except (httpx.ConnectError, httpx.ConnectTimeout):
        logger.warning("open-webSearch 守护进程未运行 (port 3210)，尝试重启...")
        return _retry_search(client, httpx, query, max_results, search_limit)
    except httpx.HTTPStatusError as e:
        logger.warning(f"open-webSearch HTTP 错误: {e.response.status_code}")
        return [{"title": "搜索服务暂时不可用", "url": "",
                 "snippet": f"HTTP {e.response.status_code}，请基于已有知识回答，不要再搜索。", "engine": "error"}]
    except Exception as e:
        logger.warning(f"open-webSearch 调用失败: {e}")
        return [{"title": "搜索失败", "url": "",
                 "snippet": f"搜索出错，请基于已有知识回答。错误: {str(e)[:100]}", "engine": "error"}]
    finally:
        client.close()


def _parse_results(data: dict, max_results: int) -> list[dict]:
    """解析搜索结果，去重"""
    results = []
    seen_urls = set()
    for item in data["data"].get("results", []):
        url = item.get("url", "")
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        results.append({
            "title": item.get("title", ""),
            "url": url,
            "snippet": item.get("description", ""),
            "engine": item.get("engine", "open-websearch"),
        })
        if len(results) >= max_results:
            break
    return results


def _retry_search(client, httpx_module, query: str, max_results: int, search_limit: int) -> list[dict]:
    """搜索服务不可用时，尝试重启并重试"""
    try:
        from app.ai.search_service import start_search_service
        if start_search_service():
            resp = client.post(
                _OWS_URL,
                json={"query": query, "limit": search_limit, "engines": ["bing", "duckduckgo"]},
                timeout=_OWS_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "ok" and data.get("data"):
                return _parse_results(data, max_results)
    except Exception as e:
        logger.warning(f"重启后重试搜索失败: {e}")

    return [{"title": "搜索服务未启动", "url": "",
             "snippet": "搜索服务不可用，请基于已有知识回答。", "engine": "error"}]


# ── 工具定义（OpenAI / Anthropic 格式）────────────────────────

TOOL_DEFINITION_OPENAI = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "搜索互联网获取最新信息。当用户询问实时信息、最新新闻或你不确定的事实时使用。收到结果后，必须阅读并基于结果回答用户问题。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
                "max_results": {"type": "integer", "description": "返回结果数，默认5", "default": 5}
            },
            "required": ["query"]
        }
    }
}

TOOL_DEFINITION_ANTHROPIC = {
    "name": "web_search",
    "description": "搜索互联网获取最新信息。当用户询问实时信息、最新新闻或你不确定的事实时使用。收到结果后，必须阅读并基于结果回答用户问题。",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
            "max_results": {"type": "integer", "description": "返回结果数，默认5", "default": 5}
        },
        "required": ["query"]
    }
}


def is_search_error(result: str) -> bool:
    """检查搜索结果是否为错误（未获得有效数据）"""
    return any(kw in result for kw in [
        "未获得有效结果", "未启动", "不可用", "搜索失败", "未找到",
        "错误：", "搜索服务",
    ])


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
        return f"未找到与 \"{query}\" 相关的搜索结果。请基于已有知识回答用户问题。"

    valid_results = [r for r in results if r.get("engine") != "error"]
    if not valid_results:
        return f"搜索 \"{query}\" 未获得有效结果。请基于已有知识直接回答，不要再尝试搜索。"

    lines = [f"搜索 \"{query}\" 获得 {len(valid_results)} 条结果：\n"]
    for i, r in enumerate(valid_results, 1):
        lines.append(f"[{i}] {r['title']}")
        if r.get('url'):
            lines.append(f"    来源: {r['url']}")
        if r.get('snippet'):
            lines.append(f"    内容: {r['snippet']}")
        lines.append("")

    lines.append("请基于以上搜索结果，为用户提供详细、准确的回答。")
    return "\n".join(lines)
