"""Web 搜索工具 — 通过 DuckDuckGo 获取搜索结果，供 AI 工具调用使用"""

import re
import json
import html as html_mod
from typing import Optional


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """执行 Web 搜索，返回结果列表。

    每条结果包含: {"title": str, "url": str, "snippet": str}
    """
    try:
        import httpx
    except ImportError:
        return [{"title": "错误", "url": "", "snippet": "未安装 httpx 库，无法执行搜索。"}]

    try:
        return _search_duckduckgo(query, max_results, httpx)
    except Exception as e:
        return [{"title": "搜索失败", "url": "", "snippet": f"DuckDuckGo 搜索出错: {e}"}]


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

    # 匹配结果块: <a class="result__a" href="...">title</a> + <a class="result__snippet" ...>snippet</a>
    # DuckDuckGo HTML 版本使用相对简单的结构
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
            })

    # 如果上面的正则没匹配到，尝试备用模式
    if not results:
        results = _parse_ddg_fallback(html_text, max_results)

    return results


def _parse_ddg_fallback(html_text: str, max_results: int) -> list[dict]:
    """备用解析: 匹配 <a> 标签中的链接和标题"""
    results = []
    # 匹配所有看起来像搜索结果的链接
    links = re.findall(
        r'<a[^>]*rel="nofollow"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
        html_text, re.DOTALL
    )
    for href, text_html in links[:max_results]:
        title = _strip_html(text_html)
        url = _extract_ddg_url(href)
        if title and url and len(title) > 5:
            results.append({"title": title, "url": url, "snippet": ""})
    return results


def _strip_html(s: str) -> str:
    """移除 HTML 标签并解码实体"""
    s = re.sub(r'<[^>]+>', '', s)
    s = html_mod.unescape(s)
    return s.strip()


def _extract_ddg_url(href: str) -> str:
    """从 DuckDuckGo 重定向链接中提取真实 URL"""
    # DuckDuckGo 的链接格式: //duckduckgo.com/l/?uddg=<encoded_url>&...
    match = re.search(r'uddg=([^&]+)', href)
    if match:
        from urllib.parse import unquote
        return unquote(match.group(1))
    # 如果不是重定向格式，直接返回
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
        lines.append(f"{i}. **{r['title']}**")
        lines.append(f"   链接: {r['url']}")
        if r['snippet']:
            lines.append(f"   摘要: {r['snippet']}")
        lines.append("")

    return "\n".join(lines)
