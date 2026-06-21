"""出版社 PDF 拉取服务 — DOI → 出版商落地页 → PDF 下载

基于 ScholarAIO 的 pdf_fetch 设计，适配 AI Nexus Assistant 架构。
核心管线: DOI 规范化 → 落地页抓取 → PDF 链接提取 → 下载验证
"""

import re
import os
import time
import logging
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
    """
    s = doi_or_url.strip()
    if not s:
        return ""
    # 已经是 URL
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

    三种模式并行扫描（按优先级排序）:
      1. <meta name="citation_pdf_url" content="...">  ← 最高优先级
      2. <a href="...pdf"> / <a href=".../pdf/">       ← 次优先
      3. 正则匹配 body 中的 https://...pdf URL          ← 兜底
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

    # 模式 2: <a> 标签中的 PDF 链接
    for m in re.finditer(
        r'<a\s+[^>]*href=["\']([^"\']*\.pdf[^"\']*)["\']',
        html, re.IGNORECASE
    ):
        url = m.group(1).strip()
        if url and url not in seen and _is_valid_pdf_url(url):
            candidates.append(url)
            seen.add(url)

    # 模式 2b: <a> 标签 href 包含 /pdf/
    for m in re.finditer(
        r'<a\s+[^>]*href=["\']([^"\']*(?:/pdf/|/pdf\b)[^"\']*)["\']',
        html, re.IGNORECASE
    ):
        url = m.group(1).strip()
        if url and url not in seen and _is_valid_pdf_url(url):
            candidates.append(url)
            seen.add(url)

    # 模式 3: 正则匹配 body 中的 PDF URL
    for m in re.finditer(
        r'(https?://[^\s"\'<>]+\.pdf(?:\?[^\s"\'<>]*)?)',
        html, re.IGNORECASE
    ):
        url = m.group(1).strip()
        if url not in seen and _is_valid_pdf_url(url):
            candidates.append(url)
            seen.add(url)

    return candidates


def _is_valid_pdf_url(url: str) -> bool:
    """检查 URL 是否看起来像有效的 PDF 链接"""
    if not url or len(url) > 2000:
        return False
    # 排除明显的非 PDF 链接
    lower = url.lower()
    skip_patterns = [".css", ".js", ".png", ".jpg", ".gif", ".svg", "#", "javascript:"]
    for pat in skip_patterns:
        if pat in lower:
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


def fetch_pdf(
    doi_or_url: str,
    output_dir: str,
    timeout: int = 60,
    filename: str = "",
) -> dict:
    """从出版社网站拉取 PDF。

    管线:
      1. DOI → doi.org URL 规范化
      2. GET doi.org（跟随重定向）→ 落地页
         - Content-Type 是 PDF？→ 直接保存
         - 是 HTML？→ 进入步骤 3
      3. HTML 解析 PDF 链接（三种模式）
      4. 逐候选 URL 下载 + 验证

    Args:
        doi_or_url: DOI 字符串或完整 URL
        output_dir: PDF 保存目录
        timeout: 超时秒数
        filename: 可选文件名（不含 .pdf 后缀）

    Returns:
        dict: {success, pdf_path, source_url, method, error}
    """
    import httpx

    url = normalize_doi(doi_or_url)
    if not url:
        return {"success": False, "error": "无效的 DOI 或 URL"}

    os.makedirs(output_dir, exist_ok=True)

    # 构建输出文件名
    if not filename:
        # 从 DOI 生成文件名
        clean_doi = re.sub(r"[^\w\-.]", "_", doi_or_url.strip().split("/")[-1])[:60]
        filename = clean_doi or "paper"
    pdf_path = os.path.join(output_dir, f"{filename}.pdf")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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
            _log.info(f"正在获取: {url}")
            resp = client.get(url)
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

            if not pdf_urls:
                return {
                    "success": False,
                    "error": "未找到 PDF 链接",
                    "source_url": str(resp.url),
                    "html_snippet": html[:500],
                }

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

            return {
                "success": False,
                "error": f"所有 {len(pdf_urls)} 个候选 URL 均下载失败",
                "candidates": pdf_urls[:5],
            }

    except httpx.TimeoutException:
        return {"success": False, "error": f"请求超时 ({timeout}s)"}
    except httpx.HTTPStatusError as e:
        return {"success": False, "error": f"HTTP 错误: {e.response.status_code}"}
    except Exception as e:
        _log.error(f"PDF 拉取异常: {e}")
        return {"success": False, "error": str(e)}


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
