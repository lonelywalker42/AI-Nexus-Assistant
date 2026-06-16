"""Web 搜索工具 — 调用 open-webSearch 聚合搜索引擎

优先通过 open-webSearch 守护进程（端口 3210）搜索，聚合 DuckDuckGo + Bing + Brave + Wikipedia + Arxiv。
守护进程不可用时回退到 DuckDuckGo HTML 直接爬取。
"""

import json
import re
import html as html_mod
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# open-webSearch 守护进程地址
_OWS_URL = "http://127.0.0.1:3210/search"
_OWS_TIMEOUT = 15.0  # 聚合搜索可能较慢


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """执行 Web 搜索，返回结果列表。

    每条结果包含: {"title": str, "url": str, "snippet": str, "engine": str}
    """
    # 1. 优先尝试 open-webSearch 守护进程
    results = _search_via_open_websearch(query, max_results)
    if results:
        return results

    # 2. 回退到 DuckDuckGo HTML 直接爬取
    logger.info("open-webSearch 不可用，回退到 DuckDuckGo HTML")
    try:
        import httpx
        return _search_duckduckgo(query, max_results, httpx)
    except ImportError:
        return [{"title": "错误", "url": "", "snippet": "未安装 httpx 库，无法执行搜索。", "engine": "error"}]
    except Exception as e:
        return [{"title": "搜索失败", "url": "", "snippet": f"DuckDuckGo 搜索出错: {e}", "engine": "error"}]


def _search_via_open_websearch(query: str, max_results: int) -> list[dict]:
    """通过 open-webSearch 守护进程搜索"""
    try:
        import httpx
    except ImportError:
        return []

    try:
        resp = httpx.post(
            _OWS_URL,
            json={
                "query": query,
                "limit": max_results,
                "engines": ["duckduckgo", "bing", "brave"],
            },
            timeout=_OWS_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "ok" or not data.get("data"):
            logger.warning(f"open-webSearch 返回错误: {data.get('error', {}).get('message', 'unknown')}")
            return []

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
        return []
    except Exception as e:
        logger.warning(f"open-webSearch 调用失败: {e}")
        return []


def _search_duckduckgo(query: str, max_results: int, httpx) -> list[dict]:
    """通过 DuckDuckGo HTML 版本搜索"""
    url = "https://html.duckduckgo.com/html/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    with httpx.Client(timeout=10, follow_redirects=True) as client:
        resp = client.post(url, data={"q": query}, headers=headers)
        resp.raise_for_status()

    return _parse_ddg_html(resp.text, max_results)


def _parse_ddg_html(html_text: str, max_results: int) -> list[dict]:
    """解析 DuckDuckGo HTML 搜索结果"""
    results = []

    blocks = re.findall(
        r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>'
        r'.*?'
        r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
        html_text, re.DOTALL
    )

    for href, title_html, snippet_html in blocks[:max_results]:
        title = _strip_html(title_html)
        snippet = _strip_html(snippet_html)
        url = _extract_ddg_url(href)

        if title and url:
            results.append({
                "title": title,
                "url": url,
                "snippet": snippet,
                "engine": "duckduckgo",
            })

    if not results:
        results = _parse_ddg_fallback(html_text, max_results)

    return results


def _parse_ddg_fallback(html_text: str, max_results: int) -> list[dict]:
    """备用解析: 匹配 <a> 标签中的链接和标题"""
    results = []
    links = re.findall(
        r'<a[^>]*rel="nofollow"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
        html_text, re.DOTALL
    )
    for href, text_html in links[:max_results]:
        title = _strip_html(text_html)
        url = _extract_ddg_url(href)
        if title and url and len(title) > 5:
            results.append({"title": title, "url": url, "snippet": "", "engine": "duckduckgo"})
    return results


def _strip_html(s: str) -> str:
    """移除 HTML 标签并解码实体"""
    s = re.sub(r'<[^>]+>', '', s)
    s = html_mod.unescape(s)
    return s.strip()


def _extract_ddg_url(href: str) -> str:
    """从 DuckDuckGo 重定向链接中提取真实 URL"""
    match = re.search(r'uddg=([^&]+)', href)
    if match:
        from urllib.parse import unquote
        return unquote(match.group(1))
    if href.startswith("http"):
        return href
    return ""


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

    # 格式化为可读文本
    lines = [f"搜索 \"{query}\" 的结果：\n"]
    for i, r in enumerate(results, 1):
        engine_tag = f" [{r.get('engine', '')}]" if r.get('engine') else ""
        lines.append(f"{i}. **{r['title']}**{engine_tag}")
        lines.append(f"   链接: {r['url']}")
        if r.get('snippet'):
            lines.append(f"   摘要: {r['snippet']}")
        lines.append("")

    return "\n".join(lines)
