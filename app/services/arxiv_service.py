"""arXiv 搜索与导入服务 — Atom API 查询 + PDF 下载"""

import re
import os
import time
import logging
import xml.etree.ElementTree as ET
from typing import Optional
from pathlib import Path

_log = logging.getLogger("nexus.arxiv")

ARXIV_API = "http://export.arxiv.org/api/query"
ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom"}


def search_arxiv(query: str, max_results: int = 20) -> list[dict]:
    """查询 arXiv Atom API。

    支持字段限定: au:, ti:, abs:, cat:
    返回: [{title, authors, abstract, arxiv_id, pdf_url, published, categories, primary_category}]

    Args:
        query: 搜索查询
        max_results: 最大结果数

    Returns:
        list[dict]: 论文列表
    """
    import httpx

    params = {
        "search_query": query,
        "start": 0,
        "max_results": min(max_results, 100),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    try:
        with httpx.Client(proxy=None, timeout=30) as client:
            resp = client.get(ARXIV_API, params=params)
            resp.raise_for_status()
            return _parse_arxiv_xml(resp.text)
    except httpx.TimeoutException:
        _log.error("arXiv API 请求超时")
        return []
    except Exception as e:
        _log.error(f"arXiv 搜索失败: {e}")
        return []


def _parse_arxiv_xml(xml_text: str) -> list[dict]:
    """解析 arXiv Atom XML 响应"""
    papers = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        _log.error(f"arXiv XML 解析失败: {e}")
        return []

    for entry in root.findall("atom:entry", ARXIV_NS):
        try:
            paper = _parse_entry(entry)
            if paper:
                papers.append(paper)
        except Exception as e:
            _log.debug(f"解析条目失败: {e}")
            continue

    return papers


def _parse_entry(entry) -> Optional[dict]:
    """解析单个 arXiv 条目"""
    # 标题
    title_el = entry.find("atom:title", ARXIV_NS)
    title = title_el.text.strip().replace("\n", " ") if title_el is not None and title_el.text else ""
    if not title:
        return None

    # 摘要
    summary_el = entry.find("atom:summary", ARXIV_NS)
    abstract = summary_el.text.strip().replace("\n", " ") if summary_el is not None and summary_el.text else ""

    # arXiv ID
    id_el = entry.find("atom:id", ARXIV_NS)
    arxiv_url = id_el.text.strip() if id_el is not None and id_el.text else ""
    arxiv_id = arxiv_url.split("/abs/")[-1] if "/abs/" in arxiv_url else ""
    # 去掉版本号
    arxiv_id_clean = re.sub(r"v\d+$", "", arxiv_id)

    # 作者
    authors = []
    for author_el in entry.findall("atom:author", ARXIV_NS):
        name_el = author_el.find("atom:name", ARXIV_NS)
        if name_el is not None and name_el.text:
            authors.append(name_el.text.strip())

    # 发布日期
    published_el = entry.find("atom:published", ARXIV_NS)
    published = published_el.text.strip()[:10] if published_el is not None and published_el.text else ""
    year = int(published[:4]) if len(published) >= 4 and published[:4].isdigit() else 0

    # 分类
    categories = []
    for cat_el in entry.findall("atom:category", ARXIV_NS):
        term = cat_el.get("term", "")
        if term:
            categories.append(term)

    primary_category = ""
    primary_el = entry.find("arxiv:primary_category", {"arxiv": "http://arxiv.org/schemas/atom"})
    if primary_el is not None:
        primary_category = primary_el.get("term", "")

    # PDF 链接
    pdf_url = ""
    for link_el in entry.findall("atom:link", ARXIV_NS):
        if link_el.get("title") == "pdf" or link_el.get("type") == "application/pdf":
            pdf_url = link_el.get("href", "")
            break
    if not pdf_url and arxiv_id_clean:
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id_clean}.pdf"

    return {
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "arxiv_id": arxiv_id_clean,
        "pdf_url": pdf_url,
        "published": published,
        "year": year,
        "categories": categories,
        "primary_category": primary_category,
        "source": "arxiv",
    }


def download_arxiv_pdf(arxiv_id: str, output_dir: str, timeout: int = 60) -> dict:
    """下载 arXiv PDF。

    使用 3 秒礼貌间隔限速，原子写入（.part 临时文件 → rename）。

    Args:
        arxiv_id: arXiv ID（如 "2301.12345"）
        output_dir: 保存目录
        timeout: 超时秒数

    Returns:
        dict: {success, pdf_path, error}
    """
    import httpx

    # 清理 ID
    clean_id = re.sub(r"v\d+$", "", arxiv_id.strip())
    if not clean_id:
        return {"success": False, "error": "无效的 arXiv ID"}

    pdf_url = f"https://arxiv.org/pdf/{clean_id}.pdf"
    os.makedirs(output_dir, exist_ok=True)
    pdf_path = os.path.join(output_dir, f"arxiv_{clean_id.replace('/', '_')}.pdf")
    part_path = pdf_path + ".part"

    try:
        with httpx.Client(proxy=None, timeout=timeout, follow_redirects=True) as client:
            _log.info(f"下载 arXiv PDF: {pdf_url}")
            with client.stream("GET", pdf_url) as resp:
                resp.raise_for_status()
                with open(part_path, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=8192):
                        f.write(chunk)

        # 验证 PDF
        with open(part_path, "rb") as f:
            header = f.read(1024)
            if b"%PDF-" not in header:
                os.unlink(part_path)
                return {"success": False, "error": "下载内容不是有效 PDF"}

        # 原子重命名
        os.replace(part_path, pdf_path)
        size_mb = os.path.getsize(pdf_path) / 1024 / 1024
        _log.info(f"arXiv PDF 下载成功: {pdf_path} ({size_mb:.1f} MB)")

        return {"success": True, "pdf_path": pdf_path}

    except httpx.TimeoutException:
        _cleanup(part_path)
        return {"success": False, "error": f"下载超时 ({timeout}s)"}
    except httpx.HTTPStatusError as e:
        _cleanup(part_path)
        return {"success": False, "error": f"HTTP 错误: {e.response.status_code}"}
    except Exception as e:
        _cleanup(part_path)
        return {"success": False, "error": str(e)}


def _cleanup(path: str):
    """清理临时文件"""
    try:
        if os.path.exists(path):
            os.unlink(path)
    except OSError:
        pass
