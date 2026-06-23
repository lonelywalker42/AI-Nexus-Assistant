"""出版社 PDF 拉取服务 — DOI → 出版商落地页 → PDF 下载

基于 ScholarAIO 的 pdf_fetch 设计，适配 AI Nexus Assistant 架构。
核心管线: DOI 规范化 → 落地页抓取 → PDF 链接提取 → 下载验证

增强特性:
  - Crossref API 标题→DOI 解析
  - 多模式 PDF 链接提取（meta标签/锚点/正则/JavaScript重定向）
  - Unpaywall / Semantic Scholar / Crossref Fulltext / Sci-Hub 多源兜底
  - 校园网直连模式支持
"""

import re
import os
import time
import logging
import urllib.parse
from pathlib import Path
from typing import Optional

_log = logging.getLogger("nexus.pdf_fetch")

# 阶段 1: DOI → URL 规范化


def normalize_doi(doi_or_url: str) -> str:
    """将 DOI 字符串规范化为 doi.org URL。

    支持输入格式:
      - "10.xxxx/yyy"         → "https://doi.org/10.xxxx/yyy"
      - "https://doi.org/..." → 直接返回
      - "doi:10.xxxx/yyy"    → "https://doi.org/10.xxxx/yyy"
      - "http://dx.doi.org/..." → "https://doi.org/..."
      - "DOI: 10.xxxx/yyy"  → "https://doi.org/10.xxxx/yyy"
      - 带空格/换行的 DOI    → 自动清理
    """
    s = doi_or_url.strip()
    if not s:
        return ""
    # 清理多余空白和换行
    s = re.sub(r'\s+', '', s)
    # 已经是 URL — 统一为 https://doi.org/
    if s.startswith("http://doi.org/") or s.startswith("https://doi.org/"):
        return s.replace("http://doi.org/", "https://doi.org/")
    if s.startswith("http://dx.doi.org/") or s.startswith("https://dx.doi.org/"):
        return s.replace("http://dx.doi.org/", "https://doi.org/").replace("https://dx.doi.org/", "https://doi.org/")
    if s.startswith("http://") or s.startswith("https://"):
        return s
    # 去掉 "doi:" 前缀
    s = re.sub(r"^doi:\s*", "", s, flags=re.IGNORECASE)
    # 纯 DOI
    if re.match(r"^10\.\d{4,}/", s):
        return f"https://doi.org/{s}"
    return s


# 阶段 2: 落地页抓取 → PDF 链接提取


def extract_pdf_urls_from_html(html: str) -> list[str]:
    """从 HTML 中提取 PDF 候选 URL。

    七种模式并行扫描（按优先级排序）:
      1. <meta name="citation_pdf_url" content="...">  ← 最高优先级（学术出版标准）
      2. <link rel="alternate" type="application/pdf">  ← 次优先
      3. <a href="...pdf"> / <a href=".../pdf/">        ← 中等优先
      4. JavaScript 重定向 / data 属性中的 PDF URL       ← 次低
      5. <iframe>/<embed> 中的 PDF URL                   ← 新增
      6. 常见出版社专用 URL 模式（ScienceDirect/Springer/Wiley/IEEE/ACM/Nature 等）← 新增
      7. 正则匹配 body 中的 https://...pdf URL           ← 兜底
    """
    candidates = []
    seen = set()

    # 模式 1: citation_pdf_url meta 标签（学术出版标准）
    for m in re.finditer(
        r'<meta\s+name=["\']citation_pdf_url["\']\s+content=["\']([^"\']+)["\']',
        html, re.IGNORECASE
    ):
        url = m.group(1).strip()
        if url and url not in seen:
            candidates.append(url)
            seen.add(url)

    # 模式 1b: citation_pdf_url 顺序颠倒（content 在 name 之前）
    for m in re.finditer(
        r'<meta\s+content=["\']([^"\']+)["\']\s+name=["\']citation_pdf_url["\']',
        html, re.IGNORECASE
    ):
        url = m.group(1).strip()
        if url and url not in seen:
            candidates.append(url)
            seen.add(url)

    # 模式 2: <link rel="alternate" type="application/pdf">
    for m in re.finditer(
        r'<link\s+[^>]*rel=["\']alternate["\'][^>]*type=["\']application/pdf["\'][^>]*href=["\']([^"\']+)["\']',
        html, re.IGNORECASE
    ):
        url = m.group(1).strip()
        if url and url not in seen:
            candidates.append(url)
            seen.add(url)

    # 模式 2b: href 在 type 之前
    for m in re.finditer(
        r'<link\s+[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\']alternate["\'][^>]*type=["\']application/pdf["\']',
        html, re.IGNORECASE
    ):
        url = m.group(1).strip()
        if url and url not in seen:
            candidates.append(url)
            seen.add(url)

    # 模式 3: <a> 标签中的 PDF 链接
    for m in re.finditer(
        r'<a\s+[^>]*href=["\']([^"\']*\.pdf[^"\']*)["\']',
        html, re.IGNORECASE
    ):
        url = m.group(1).strip()
        if url and url not in seen and _is_valid_pdf_url(url):
            candidates.append(url)
            seen.add(url)

    # 模式 3b: <a> 标签 href 包含 /pdf/
    for m in re.finditer(
        r'<a\s+[^>]*href=["\']([^"\']*(?:/pdf/|/pdf\b)[^"\']*)["\']',
        html, re.IGNORECASE
    ):
        url = m.group(1).strip()
        if url and url not in seen and _is_valid_pdf_url(url):
            candidates.append(url)
            seen.add(url)

    # 模式 3c: <a> 标签包含 "Download PDF" 或 "PDF" 文本
    for m in re.finditer(
        r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(?:[^<]*(?:download|full\s*text|pdf)[^<]*)</a>',
        html, re.IGNORECASE
    ):
        url = m.group(1).strip()
        if url and url not in seen and _is_valid_pdf_url(url):
            candidates.append(url)
            seen.add(url)

    # 模式 4: JavaScript 重定向中的 PDF URL
    for m in re.finditer(
        r'(?:window\.location|location\.href|window\.open)\s*=\s*["\']([^"\']*\.pdf[^"\']*)["\']',
        html, re.IGNORECASE
    ):
        url = m.group(1).strip()
        if url and url not in seen and _is_valid_pdf_url(url):
            candidates.append(url)
            seen.add(url)

    # 模式 4b: data 属性中的 PDF URL
    for m in re.finditer(
        r'data-(?:pdf-url|download-url|file-url|article-url)=["\']([^"\']*\.pdf[^"\']*)["\']',
        html, re.IGNORECASE
    ):
        url = m.group(1).strip()
        if url and url not in seen and _is_valid_pdf_url(url):
            candidates.append(url)
            seen.add(url)

    # 模式 4c: <iframe> 和 <embed> 中的 PDF URL
    for m in re.finditer(
        r'<(?:iframe|embed)\s+[^>]*src=["\']([^"\']*\.pdf[^"\']*)["\']',
        html, re.IGNORECASE
    ):
        url = m.group(1).strip()
        if url and url not in seen and _is_valid_pdf_url(url):
            candidates.append(url)
            seen.add(url)

    # 模式 4d: 常见出版社专用 URL 模式
    publisher_patterns = [
        # ScienceDirect / Elsevier
        r'(https?://[^"\']*sciencedirect\.com[^"\']*/pdf[^"\']*)',
        r'(https?://[^"\']*sciencedirect\.com[^"\']*\.pdf[^"\']*)',
        # Springer
        r'(https?://[^"\']*springer\.com[^"\']*/content/pdf[^"\']*)',
        r'(https?://[^"\']*springer\.com[^"\']*\.pdf[^"\']*)',
        # Wiley
        r'(https?://[^"\']*wiley\.com[^"\']*/pdf[^"\']*)',
        r'(https?://[^"\']*onlinelibrary\.wiley\.com[^"\']*/pdf[^"\']*)',
        # IEEE
        r'(https?://[^"\']*ieee\.org[^"\']*/stamp\.jsp[^"\']*)',
        r'(https?://[^"\']*ieeexplore\.ieee\.org[^"\']*/pdf[^"\']*)',
        # ACM
        r'(https?://[^"\']*acm\.org[^"\']*/doi/pdf[^"\']*)',
        r'(https?://[^"\']*dl\.acm\.org[^"\']*/pdf[^"\']*)',
        # Nature
        r'(https?://[^"\']*nature\.com[^"\']*/\.pdf[^"\']*)',
        r'(https?://[^"\']*nature\.com[^"\']*\.pdf[^"\']*)',
        # Oxford Academic
        r'(https?://[^"\']*academic\.oup\.com[^"\']*/pdf[^"\']*)',
        # Cambridge
        r'(https?://[^"\']*cambridge\.org[^"\']*/pdf[^"\']*)',
        # SAGE
        r'(https?://[^"\']*sagepub\.com[^"\']*/pdf[^"\']*)',
        # Taylor & Francis
        r'(https?://[^"\']*tandfonline\.com[^"\']*/pdf[^"\']*)',
    ]
    for pattern in publisher_patterns:
        for m in re.finditer(pattern, html, re.IGNORECASE):
            url = m.group(1).strip()
            if url and url not in seen and _is_valid_pdf_url(url):
                candidates.append(url)
                seen.add(url)

    # 模式 5: 正则匹配 body 中的 PDF URL（通用兜底）
    for m in re.finditer(
        r'(https?://[^\s"\'<>]+\.pdf(?:\?[^\s"\'<>]*)?)',
        html, re.IGNORECASE
    ):
        url = m.group(1).strip()
        if url not in seen and _is_valid_pdf_url(url):
            candidates.append(url)
            seen.add(url)

    return candidates


def _try_crossref_title_to_doi(title: str) -> Optional[str]:
    """通过 Crossref API 将论文标题解析为 DOI。

    用于用户输入纯标题（无 DOI）时的降级查询。
    """
    import urllib.request
    import json as _json

    if not title or len(title) < 10:
        return None

    try:
        # Crossref API 查询
        encoded_title = urllib.parse.quote(title)
        url = f"https://api.crossref.org/works?query.title={encoded_title}&rows=1"
        req = urllib.request.Request(url, headers={
            "User-Agent": "AI-Nexus-Assistant/1.0 (mailto:support@example.com)",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = _json.loads(resp.read())

        items = data.get("message", {}).get("items", [])
        if items:
            doi = items[0].get("DOI", "")
            if doi and doi.startswith("10."):
                return doi
    except Exception as e:
        _log.debug(f"Crossref 标题查询失败 ({title[:50]}): {e}")

    return None


def _is_valid_pdf_url(url: str) -> bool:
    """检查 URL 是否看起来像有效的 PDF 链接。

    过滤掉导航 URL、图片 URL、CSS/JS 资源等误报。
    """
    if not url or len(url) > 2000:
        return False
    lower = url.lower()
    # 排除明显的非 PDF 链接
    skip_extensions = [
        ".css", ".js", ".jsx", ".ts", ".tsx",
        ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
        ".mp3", ".mp4", ".wav", ".avi", ".mov",
        ".zip", ".tar", ".gz", ".rar",
        ".xml", ".json", ".woff", ".woff2", ".ttf", ".eot",
    ]
    for ext in skip_extensions:
        if lower.endswith(ext):
            return False
    skip_patterns = [
        "javascript:", "mailto:", "tel:", "#",
        "/login", "/signup", "/register", "/cart", "/checkout",
        "/cookie", "/privacy", "/terms", "/contact",
    ]
    for pat in skip_patterns:
        if pat in lower:
            return False
    # 排除明显的图片/资源路径
    if re.search(r'/images?/', lower) or re.search(r'/icons?/', lower) or re.search(r'/assets?/', lower):
        return False
    return True


# 阶段 3: PDF 验证与规范化


def validate_pdf(content: bytes) -> bool:
    """检查内容是否为有效 PDF（魔数检查 %PDF-）"""
    if not content or len(content) < 100:
        return False
    # 检查前 1024 字节中的 %PDF- 标记
    header = content[:1024]
    return b"%PDF-" in header


def normalize_pdf_header(content: bytes) -> bytes:
    """剥离 PDF 流前面的非 PDF 前缀字节。

    某些出版商在 PDF 流前面插入跟踪像素或广告横幅。
    此函数定位 %PDF- 标记并剥离前面的所有内容。
    """
    if not content:
        return content
    idx = content.find(b"%PDF-")
    if idx <= 0:
        return content
    return content[idx:]


# 阶段 4: 下载管线


def _try_unpaywall(doi: str) -> Optional[str]:
    """尝试从 Unpaywall API 获取开放获取 PDF 链接。

    Args:
        doi: 纯 DOI（不含 URL 前缀）

    Returns:
        PDF URL 或 None
    """
    import urllib.request
    import json as _json

    clean_doi = doi.strip()
    # 去掉可能的 URL 前缀
    if clean_doi.startswith("https://doi.org/"):
        clean_doi = clean_doi[len("https://doi.org/"):]
    elif clean_doi.startswith("http://doi.org/"):
        clean_doi = clean_doi[len("http://doi.org/"):]

    try:
        url = f"https://api.unpaywall.org/v2/{clean_doi}?email=test@example.com"
        req = urllib.request.Request(url, headers={"User-Agent": "AI-Nexus-Assistant/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = _json.loads(resp.read())

        # 优先取 best_oa_location
        best = data.get("best_oa_location")
        if best and best.get("url_for_pdf"):
            return best["url_for_pdf"]

        # 遍历所有 oa_locations
        for loc in data.get("oa_locations", []):
            if loc.get("url_for_pdf"):
                return loc["url_for_pdf"]

    except Exception as e:
        _log.debug(f"Unpaywall 查询失败 ({clean_doi}): {e}")

    return None


def _try_semantic_scholar(doi: str) -> Optional[str]:
    """尝试从 Semantic Scholar API 获取开放获取 PDF 链接。

    Args:
        doi: 纯 DOI（不含 URL 前缀）

    Returns:
        PDF URL 或 None
    """
    import urllib.request
    import json as _json

    clean_doi = doi.strip()
    if clean_doi.startswith("https://doi.org/"):
        clean_doi = clean_doi[len("https://doi.org/"):]
    elif clean_doi.startswith("http://doi.org/"):
        clean_doi = clean_doi[len("http://doi.org/"):]

    try:
        url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{clean_doi}?fields=openAccessPdf,externalIds"
        req = urllib.request.Request(url, headers={
            "User-Agent": "AI-Nexus-Assistant/1.0",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = _json.loads(resp.read())

        # 直接从 openAccessPdf 字段获取
        oapdf = data.get("openAccessPdf")
        if oapdf and oapdf.get("url"):
            return oapdf["url"]

    except Exception as e:
        _log.debug(f"Semantic Scholar 查询失败 ({clean_doi}): {e}")

    return None


def _try_crossref_fulltext(doi: str) -> Optional[str]:
    """尝试从 Crossref API 的 link 字段获取全文 PDF 链接。

    查询 Crossref works 端点，检查 link 数组中是否有
    content-type 为 application/pdf 或 text/xml 的全文链接。

    Args:
        doi: 纯 DOI（不含 URL 前缀）

    Returns:
        PDF URL 或 None
    """
    import urllib.request
    import json as _json

    clean_doi = doi.strip()
    if clean_doi.startswith("https://doi.org/"):
        clean_doi = clean_doi[len("https://doi.org/"):]
    elif clean_doi.startswith("http://doi.org/"):
        clean_doi = clean_doi[len("http://doi.org/"):]

    try:
        url = f"https://api.crossref.org/works/{clean_doi}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "AI-Nexus-Assistant/1.0 (mailto:support@example.com)",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = _json.loads(resp.read())

        message = data.get("message", {})
        links = message.get("link", [])

        # 优先取 application/pdf 类型的链接
        for link in links:
            ct = link.get("content-type", "").lower()
            if "application/pdf" in ct and link.get("URL"):
                return link["URL"]

        # 次选 text/xml 或其他全文类型
        for link in links:
            ct = link.get("content-type", "").lower()
            if ("text/xml" in ct or "application/xml" in ct) and link.get("URL"):
                return link["URL"]

        # 检查 resource.primary 是否有 PDF 链接
        resource = message.get("resource", {})
        primary = resource.get("primary", {})
        if primary.get("URL"):
            purl = primary["URL"]
            if ".pdf" in purl.lower():
                return purl

    except Exception as e:
        _log.debug(f"Crossref fulltext 查询失败 ({clean_doi}): {e}")

    return None


_SCIHUB_MIRRORS = [
    "https://sci-hub.se",
    "https://sci-hub.st",
    "https://sci-hub.ru",
]


def _try_scihub(doi: str, timeout: int = 30) -> Optional[str]:
    """尝试从 Sci-Hub 镜像获取 PDF 下载链接。

    依次尝试多个 Sci-Hub 镜像站点，从返回的 HTML 中提取
    iframe 或 embed 标签中的 PDF 下载链接。

    Args:
        doi: 纯 DOI（不含 URL 前缀）
        timeout: 超时秒数

    Returns:
        PDF URL 或 None
    """
    import httpx

    clean_doi = doi.strip()
    if clean_doi.startswith("https://doi.org/"):
        clean_doi = clean_doi[len("https://doi.org/"):]
    elif clean_doi.startswith("http://doi.org/"):
        clean_doi = clean_doi[len("http://doi.org/"):]

    for mirror in _SCIHUB_MIRRORS:
        try:
            scihub_url = f"{mirror}/{clean_doi}"
            _log.info(f"尝试 Sci-Hub 镜像: {scihub_url[:80]}")
            with httpx.Client(
                proxy=None,
                follow_redirects=True,
                timeout=timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                                  "Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,*/*",
                },
            ) as client:
                resp = client.get(scihub_url)
                if resp.status_code != 200:
                    _log.debug(f"Sci-Hub 镜像 {mirror} 返回 {resp.status_code}")
                    continue

                html = resp.text

                # 提取 iframe src（最常见的 Sci-Hub PDF 嵌入方式）
                iframe_match = re.search(
                    r'<iframe\s+[^>]*src=["\']([^"\']+)["\']',
                    html, re.IGNORECASE,
                )
                if iframe_match:
                    pdf_url = iframe_match.group(1).strip()
                    # 处理协议相对 URL
                    if pdf_url.startswith("//"):
                        pdf_url = "https:" + pdf_url
                    # 确保是有效的 PDF URL
                    if pdf_url.startswith("http") and (
                        ".pdf" in pdf_url.lower()
                        or "pdf" in pdf_url.lower()
                    ):
                        _log.info(f"Sci-Hub iframe 找到 PDF: {pdf_url[:100]}")
                        return pdf_url

                # 提取 embed src
                embed_match = re.search(
                    r'<embed\s+[^>]*src=["\']([^"\']+)["\']',
                    html, re.IGNORECASE,
                )
                if embed_match:
                    pdf_url = embed_match.group(1).strip()
                    if pdf_url.startswith("//"):
                        pdf_url = "https:" + pdf_url
                    if pdf_url.startswith("http") and (
                        ".pdf" in pdf_url.lower()
                        or "pdf" in pdf_url.lower()
                    ):
                        _log.info(f"Sci-Hub embed 找到 PDF: {pdf_url[:100]}")
                        return pdf_url

                # 提取 <a> 标签中的 .pdf 链接
                a_match = re.search(
                    r'<a\s+[^>]*href=["\']([^"\']*\.pdf[^"\']*)["\']',
                    html, re.IGNORECASE,
                )
                if a_match:
                    pdf_url = a_match.group(1).strip()
                    if pdf_url.startswith("//"):
                        pdf_url = "https:" + pdf_url
                    if pdf_url.startswith("http"):
                        _log.info(f"Sci-Hub anchor 找到 PDF: {pdf_url[:100]}")
                        return pdf_url

                # 提取 location.href 或 window.location 重定向
                loc_match = re.search(
                    r'(?:location\.href|window\.location)\s*=\s*["\']([^"\']*\.pdf[^"\']*)["\']',
                    html, re.IGNORECASE,
                )
                if loc_match:
                    pdf_url = loc_match.group(1).strip()
                    if pdf_url.startswith("//"):
                        pdf_url = "https:" + pdf_url
                    if pdf_url.startswith("http"):
                        _log.info(f"Sci-Hub redirect 找到 PDF: {pdf_url[:100]}")
                        return pdf_url

                _log.debug(f"Sci-Hub 镜像 {mirror} 未找到 PDF 链接")

        except Exception as e:
            _log.debug(f"Sci-Hub 镜像 {mirror} 失败: {e}")
            continue

    return None


def _extract_doi_from_url(url_or_doi: str) -> str:
    """从 URL 或 DOI 字符串中提取纯 DOI"""
    s = url_or_doi.strip()
    if s.startswith("https://doi.org/"):
        return s[len("https://doi.org/"):]
    if s.startswith("http://doi.org/"):
        return s[len("http://doi.org/"):]
    if s.startswith("https://dx.doi.org/"):
        return s[len("https://dx.doi.org/"):]
    if re.match(r"^10\.\d{4,}/", s):
        return s
    return ""


def fetch_pdf(
    doi_or_url: str,
    output_dir: str,
    timeout: int = 60,
    filename: str = "",
) -> dict:
    """从出版社网站拉取 PDF。

    管线:
      1. DOI → doi.org URL 规范化（纯标题先通过 Crossref 查询 DOI）
      2. GET doi.org（跟随重定向）→ 落地页
         - Content-Type 是 PDF？→ 直接保存
         - 是 HTML？→ 进入步骤 3
      3. HTML 解析 PDF 链接（七种模式，含出版社专用 URL 模式）
      4. 逐候选 URL 下载 + 验证
      5. 兜底: Unpaywall API 获取开放获取链接
      6. 兜底: Semantic Scholar API 开放获取 PDF
      7. 兜底: Crossref API 全文链接
      8. 兜底: Sci-Hub 镜像站点

    增强特性:
      - 多 User-Agent 重试（某些出版商会阻断非浏览器 UA）
      - 常见出版社 URL 模式匹配（ScienceDirect/Springer/Wiley/IEEE/ACM/Nature 等）
      - 更完善的 URL 验证（过滤导航/图片/资源等误报）
      - 多源兜底: Unpaywall / Semantic Scholar / Crossref / Sci-Hub

    Args:
        doi_or_url: DOI 字符串、完整 URL 或纯论文标题
        output_dir: PDF 保存目录
        timeout: 超时秒数
        filename: 可选文件名（不含 .pdf 后缀）

    Returns:
        dict: {success, pdf_path, source_url, method, error}
    """
    import httpx

    # 如果输入看起来像纯标题（不是 DOI 也不是 URL），尝试 Crossref 查询
    if not doi_or_url.startswith("http") and not re.match(r"^10\.\d{4,}/", doi_or_url):
        _log.info("输入可能是论文标题，尝试 Crossref 查询 DOI...")
        crossref_doi = _try_crossref_title_to_doi(doi_or_url)
        if crossref_doi:
            _log.info("Crossref 找到 DOI: %s", crossref_doi)
            doi_or_url = crossref_doi

    url = normalize_doi(doi_or_url)
    if not url:
        return {"success": False, "error": "无效的 DOI 或 URL，请检查输入格式（如 10.1234/abcd）"}

    os.makedirs(output_dir, exist_ok=True)

    # 构建输出文件名
    if not filename:
        # 从 DOI 生成文件名
        clean_doi = re.sub(r"[^\w\-.]", "_", doi_or_url.strip().split("/")[-1])[:60]
        filename = clean_doi or "paper"
    pdf_path = os.path.join(output_dir, f"{filename}.pdf")

    # 多种 User-Agent，某些出版商会阻断非浏览器 UA
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]

    max_retries = 3  # 总共尝试 3 次（含不同 UA 重试）
    last_error = ""

    for attempt in range(max_retries):
        # 每次重试使用不同的 User-Agent
        ua = user_agents[attempt % len(user_agents)]
        headers = {
            "User-Agent": ua,
            "Accept": "application/pdf,text/html,*/*",
        }

        try:
            with httpx.Client(
                proxy=None,  # 绕过本地代理（Clash 等）
                follow_redirects=True,
                timeout=timeout,
                headers=headers,
            ) as client:
                # 阶段 2: 抓取落地页
                _log.info(f"正在获取: {url} (尝试 {attempt+1}/{max_retries})")
                resp = client.get(url)

                # 区分不同 HTTP 错误
                if resp.status_code == 403:
                    last_error = "访问被拒绝 (403)，该文献可能需要机构网络访问或付费订阅"
                    continue
                if resp.status_code == 404:
                    last_error = "DOI 对应的页面不存在 (404)，请检查 DOI 是否正确"
                    break  # 404 不重试
                if resp.status_code == 429:
                    last_error = "请求过于频繁 (429)，请稍后重试"
                    continue
                if resp.status_code >= 500:
                    last_error = f"服务器错误 ({resp.status_code})，出版社服务可能暂时不可用"
                    continue  # 5xx 重试

                resp.raise_for_status()

                content_type = resp.headers.get("content-type", "").lower()

                # 如果直接返回 PDF
                if "application/pdf" in content_type:
                    raw = resp.content
                    if validate_pdf(raw):
                        raw = normalize_pdf_header(raw)
                        with open(pdf_path, "wb") as f:
                            f.write(raw)
                        _log.info(f"直接下载 PDF: {pdf_path}")
                        return {
                            "success": True,
                            "pdf_path": pdf_path,
                            "source_url": str(resp.url),
                            "method": "direct",
                        }

                # 阶段 3: 从 HTML 提取 PDF 链接
                html = resp.text
                pdf_urls = extract_pdf_urls_from_html(html)

                if not pdf_urls:
                    # 尝试从 HTML 中提取重定向的 PDF URL
                    redirect_match = re.search(
                        r'(?:window\.location|location\.href)\s*=\s*["\']([^"\']*\.pdf[^"\']*)["\']',
                        html, re.IGNORECASE
                    )
                    if redirect_match:
                        pdf_urls = [redirect_match.group(1)]

                if pdf_urls:
                    _log.info(f"找到 {len(pdf_urls)} 个候选 PDF URL")

                    # 阶段 4: 逐候选 URL 尝试下载
                    for i, pdf_url in enumerate(pdf_urls):
                        # 相对 URL 补全
                        if pdf_url.startswith("/"):
                            from urllib.parse import urljoin
                            pdf_url = urljoin(str(resp.url), pdf_url)
                        elif not pdf_url.startswith("http"):
                            from urllib.parse import urljoin
                            pdf_url = urljoin(str(resp.url) + "/", pdf_url)

                        try:
                            _log.info(f"尝试候选 {i+1}/{len(pdf_urls)}: {pdf_url[:100]}")
                            pdf_resp = client.get(pdf_url)
                            pdf_resp.raise_for_status()

                            raw = pdf_resp.content
                            if validate_pdf(raw):
                                raw = normalize_pdf_header(raw)
                                with open(pdf_path, "wb") as f:
                                    f.write(raw)
                                _log.info(f"PDF 下载成功: {pdf_path}")
                                return {
                                    "success": True,
                                    "pdf_path": pdf_path,
                                    "source_url": pdf_url,
                                    "method": f"candidate_{i+1}",
                                }
                            else:
                                _log.debug(f"候选 {i+1}: 非有效 PDF")
                        except Exception as e:
                            _log.debug(f"候选 {i+1} 下载失败: {e}")
                            continue

                    last_error = (
                        f"从出版社页面找到 {len(pdf_urls)} 个候选链接，但均下载失败。\n"
                        "建议：\n"
                        "1. 确保在校园网或已配置机构 VPN 的环境下使用\n"
                        "2. 尝试在浏览器中手动访问该 DOI 链接并下载 PDF\n"
                        "3. 部分出版社（如 Elsevier、Springer）需要机构账号登录"
                    )
                else:
                    last_error = (
                        "出版社页面未包含 PDF 链接。可能原因：\n"
                        "1. 该文献需要付费订阅或机构网络访问\n"
                        "2. 请确保在校园网环境下使用，或配置正确的代理\n"
                        "3. 部分出版社需要手动登录后才能下载\n"
                        "4. 可尝试在浏览器中打开 DOI 链接手动下载 PDF"
                    )

                # 如果从 doi.org 落地页没找到，跳出重试循环，进入 Unpaywall 兜底
                break

        except httpx.TimeoutException:
            last_error = f"请求超时 ({timeout}s)，网络连接可能较慢"
            if attempt < max_retries - 1:
                _log.info(f"超时，正在重试...")
                continue
        except httpx.ConnectError:
            last_error = "网络连接失败，请检查网络连接"
            break  # 连接错误不重试
        except httpx.HTTPStatusError as e:
            last_error = f"HTTP 错误 {e.response.status_code}"
            if e.response.status_code >= 500 and attempt < max_retries - 1:
                continue
            break
        except Exception as e:
            last_error = f"拉取异常: {str(e)}"
            _log.error(f"PDF 拉取异常: {e}")
            break

    # 阶段 5: Unpaywall API 兜底
    _log.info(f"出版社直接拉取失败，尝试 Unpaywall API 兜底...")
    doi = _extract_doi_from_url(doi_or_url)
    if doi:
        unpaywall_url = _try_unpaywall(doi)
        if unpaywall_url:
            _log.info(f"Unpaywall 找到 OA 链接: {unpaywall_url[:100]}")
            try:
                with httpx.Client(
                    proxy=None,
                    follow_redirects=True,
                    timeout=timeout,
                    headers=headers,
                ) as client:
                    pdf_resp = client.get(unpaywall_url)
                    pdf_resp.raise_for_status()
                    raw = pdf_resp.content
                    if validate_pdf(raw):
                        raw = normalize_pdf_header(raw)
                        with open(pdf_path, "wb") as f:
                            f.write(raw)
                        _log.info(f"Unpaywall PDF 下载成功: {pdf_path}")
                        return {
                            "success": True,
                            "pdf_path": pdf_path,
                            "source_url": unpaywall_url,
                            "method": "unpaywall",
                        }
            except Exception as e:
                _log.debug(f"Unpaywall 下载失败: {e}")
                last_error += f"；Unpaywall OA 链接也下载失败"

    # 阶段 6: Semantic Scholar API 兜底
    if doi:
        _log.info("尝试 Semantic Scholar API 兜底...")
        try:
            ss_url = _try_semantic_scholar(doi)
            if ss_url:
                _log.info(f"Semantic Scholar 找到 OA 链接: {ss_url[:100]}")
                try:
                    with httpx.Client(
                        proxy=None,
                        follow_redirects=True,
                        timeout=timeout,
                        headers=headers,
                    ) as client:
                        pdf_resp = client.get(ss_url)
                        pdf_resp.raise_for_status()
                        raw = pdf_resp.content
                        if validate_pdf(raw):
                            raw = normalize_pdf_header(raw)
                            with open(pdf_path, "wb") as f:
                                f.write(raw)
                            _log.info(f"Semantic Scholar PDF 下载成功: {pdf_path}")
                            return {
                                "success": True,
                                "pdf_path": pdf_path,
                                "source_url": ss_url,
                                "method": "semantic_scholar",
                            }
                except Exception as e:
                    _log.debug(f"Semantic Scholar 下载失败: {e}")
                    last_error += "；Semantic Scholar OA 链接也下载失败"
        except Exception as e:
            _log.debug(f"Semantic Scholar 查询异常: {e}")

    # 阶段 7: Crossref API 全文链接兜底
    if doi:
        _log.info("尝试 Crossref API 全文链接兜底...")
        try:
            crossref_url = _try_crossref_fulltext(doi)
            if crossref_url:
                _log.info(f"Crossref 找到全文链接: {crossref_url[:100]}")
                try:
                    with httpx.Client(
                        proxy=None,
                        follow_redirects=True,
                        timeout=timeout,
                        headers=headers,
                    ) as client:
                        pdf_resp = client.get(crossref_url)
                        pdf_resp.raise_for_status()
                        raw = pdf_resp.content
                        if validate_pdf(raw):
                            raw = normalize_pdf_header(raw)
                            with open(pdf_path, "wb") as f:
                                f.write(raw)
                            _log.info(f"Crossref fulltext PDF 下载成功: {pdf_path}")
                            return {
                                "success": True,
                                "pdf_path": pdf_path,
                                "source_url": crossref_url,
                                "method": "crossref_fulltext",
                            }
                except Exception as e:
                    _log.debug(f"Crossref fulltext 下载失败: {e}")
                    last_error += "；Crossref 全文链接也下载失败"
        except Exception as e:
            _log.debug(f"Crossref fulltext 查询异常: {e}")

    # 阶段 8: Sci-Hub 镜像兜底
    if doi:
        _log.info("尝试 Sci-Hub 镜像兜底...")
        try:
            scihub_url = _try_scihub(doi, timeout=timeout)
            if scihub_url:
                _log.info(f"Sci-Hub 找到 PDF 链接: {scihub_url[:100]}")
                try:
                    with httpx.Client(
                        proxy=None,
                        follow_redirects=True,
                        timeout=timeout,
                        headers=headers,
                    ) as client:
                        pdf_resp = client.get(scihub_url)
                        pdf_resp.raise_for_status()
                        raw = pdf_resp.content
                        if validate_pdf(raw):
                            raw = normalize_pdf_header(raw)
                            with open(pdf_path, "wb") as f:
                                f.write(raw)
                            _log.info(f"Sci-Hub PDF 下载成功: {pdf_path}")
                            return {
                                "success": True,
                                "pdf_path": pdf_path,
                                "source_url": scihub_url,
                                "method": "scihub",
                            }
                except Exception as e:
                    _log.debug(f"Sci-Hub 下载失败: {e}")
                    last_error += "；Sci-Hub PDF 链接也下载失败"
        except Exception as e:
            _log.debug(f"Sci-Hub 查询异常: {e}")

    # 更新最终错误消息，提示已尝试所有来源
    sources_tried = "出版社页面、Unpaywall、Semantic Scholar、Crossref、Sci-Hub"
    if not last_error:
        last_error = f"所有 PDF 来源均未成功。已尝试: {sources_tried}"
    elif "已尝试" not in last_error:
        last_error += f"\n已尝试的来源: {sources_tried}"

    return {
        "success": False,
        "error": last_error or "PDF 拉取失败",
    }


def batch_fetch_pdf(
    dois: list[str],
    output_dir: str,
    timeout: int = 60,
) -> list[dict]:
    """批量拉取 PDF，单篇失败不中断。

    Args:
        dois: DOI 列表
        output_dir: PDF 保存目录
        timeout: 每篇超时秒数

    Returns:
        list[dict]: 每篇的结果 {doi, success, pdf_path, error}
    """
    import httpx

    os.makedirs(output_dir, exist_ok=True)
    results = []

    with httpx.Client(
        proxy=None,
        follow_redirects=True,
        timeout=timeout,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/pdf,text/html,*/*",
        },
    ) as client:
        for i, doi in enumerate(dois):
            doi = doi.strip()
            if not doi:
                continue
            _log.info(f"批量拉取 [{i+1}/{len(dois)}]: {doi}")
            try:
                result = fetch_pdf(doi, output_dir, timeout)
                result["doi"] = doi
                results.append(result)
            except Exception as e:
                results.append({
                    "doi": doi,
                    "success": False,
                    "error": str(e),
                })
            # 礼貌间隔
            if i < len(dois) - 1:
                time.sleep(1)

    return results
