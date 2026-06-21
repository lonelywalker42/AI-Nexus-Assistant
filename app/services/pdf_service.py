"""PDF 元数据提取服务 — 基于 PyMuPDF + 正则 + AI 三级提取"""

import re
import json
from typing import Optional


def extract_pdf_metadata(pdf_path: str) -> dict:
    """从 PDF 文件提取元数据（PyMuPDF 内置元数据 + 正则提取）

    Returns:
        dict: {title, authors, year, doi, abstract, journal, keywords, ...}
    """
    try:
        import fitz
    except ImportError:
        return {}

    meta = {}
    text = ""

    try:
        doc = fitz.open(pdf_path)

        # 1. 从 PDF 内置元数据提取
        pdf_info = doc.metadata or {}
        if pdf_info.get("title"):
            meta["title"] = pdf_info["title"].strip()
        if pdf_info.get("author"):
            # PDF 作者字段可能是逗号分隔或分号分隔
            raw_authors = pdf_info["author"]
            authors = _parse_author_string(raw_authors)
            if authors:
                meta["authors"] = authors
        if pdf_info.get("subject"):
            meta["abstract"] = pdf_info["subject"].strip()
        if pdf_info.get("keywords"):
            meta["keywords"] = pdf_info["keywords"].strip()

        # 2. 提取全文文本用于正则提取
        for page in doc:
            text += page.get_text()
        doc.close()

        if not text.strip():
            return meta

        # 3. 正则提取 DOI
        doi = _extract_doi(text)
        if doi:
            meta["doi"] = doi

        # 4. 正则提取年份
        year = _extract_year(text, pdf_info)
        if year:
            meta["year"] = year

        # 5. 正则提取摘要
        if "abstract" not in meta:
            abstract = _extract_abstract(text)
            if abstract:
                meta["abstract"] = abstract

        # 6. 正则提取期刊名
        journal = _extract_journal(text)
        if journal:
            meta["journal"] = journal

        # 7. 如果标题仍未提取，从文本首行推断
        if "title" not in meta:
            title = _extract_title_from_text(text)
            if title:
                meta["title"] = title

        # 8. 从 DOI 查询 OpenAlex 补充元数据
        if meta.get("doi") and not meta.get("authors"):
            oa_meta = _fetch_from_openalex(meta["doi"])
            if oa_meta:
                meta.update({k: v for k, v in oa_meta.items() if v and k not in meta})

    except Exception as e:
        print(f"[pdf_service] 提取元数据出错: {e}")

    return meta


def _parse_author_string(raw: str) -> list[str]:
    """解析作者字符串为列表"""
    if not raw:
        return []

    # 尝试不同分隔符
    for sep in [";", ",", " and ", " & "]:
        if sep in raw:
            authors = [a.strip() for a in raw.split(sep) if a.strip()]
            if len(authors) > 1:
                return authors

    # 单个作者
    return [raw.strip()] if raw.strip() else []


def _extract_doi(text: str) -> str:
    """从文本中提取 DOI"""
    # 常见 DOI 模式
    patterns = [
        r'(?:doi|DOI)\s*[:\s]*\s*(10\.\d{4,}/[^\s,;]+)',
        r'(?:https?://)?(?:dx\.)?doi\.org/(10\.\d{4,}/[^\s,;]+)',
        r'\b(10\.\d{4,}/[^\s,;]{5,})\b',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            doi = match.group(1).rstrip('.').rstrip(')')
            return doi
    return ""


def _extract_year(text: str, pdf_info: dict = None) -> int:
    """从文本中提取出版年份"""
    # 先从 PDF 元数据提取
    if pdf_info:
        creation_date = pdf_info.get("creationDate", "")
        if creation_date and len(creation_date) >= 4:
            try:
                year = int(creation_date[:4])
                if 1900 <= year <= 2030:
                    return year
            except ValueError:
                pass

    # 正则提取：常见年份模式
    # 模式1: "Published in 2024" / "© 2024"
    match = re.search(r'(?:Published|©|Copyright)\s*(?:in\s+)?(\d{4})', text[:2000])
    if match:
        year = int(match.group(1))
        if 1900 <= year <= 2030:
            return year

    # 模式2: "Received: ... Accepted: ..." 行中的年份
    match = re.search(r'(?:Received|Accepted|Published)\s*[:\s]+\d{1,2}\s+\w+\s+(\d{4})', text[:3000])
    if match:
        year = int(match.group(1))
        if 1900 <= year <= 2030:
            return year

    # 模式3: 首页独立的四位数年份（1990-2030）
    for line in text[:1000].split("\n"):
        match = re.search(r'\b((?:19|20)\d{2})\b', line.strip())
        if match:
            return int(match.group(1))

    return 0


def _extract_abstract(text: str) -> str:
    """从文本中提取摘要"""
    # 模式1: "Abstract" 标题后的内容
    patterns = [
        r'(?:Abstract|ABSTRACT|摘要)\s*[:\-\s]*\n?([\s\S]{50,1500}?)(?:\n\s*(?:Keywords|KEYWORDS|关键词|Introduction|INTRODUCTION|1\.|I\.))',
        r'(?:Abstract|ABSTRACT|摘要)\s*[:\-\s]*\n?([\s\S]{50,1500}?)(?:\n\s*\n)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text[:5000], re.IGNORECASE)
        if match:
            abstract = match.group(1).strip()
            # 清理多余空白
            abstract = re.sub(r'\s+', ' ', abstract)
            if len(abstract) > 50:
                return abstract[:2000]
    return ""


def _extract_journal(text: str) -> str:
    """从文本中提取期刊名"""
    # 模式1: "Published in Journal Name"
    match = re.search(r'Published\s+in\s*[:\s]*([A-Z][^\n]{5,100}?)(?:\n|,|\()', text[:2000])
    if match:
        return match.group(1).strip()

    # 模式2: "Journal of XXX" / "XXX Journal"
    match = re.search(r'\b(Journal\s+of\s+[A-Z][A-Za-z\s&]{5,80}|[A-Z][A-Za-z\s&]{3,50}\s+Journal)\b', text[:2000])
    if match:
        return match.group(1).strip()

    return ""


def _extract_title_from_text(text: str) -> str:
    """从文本首行推断标题"""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return ""

    # 第一行通常是标题（排除过短或全大写的行）
    for line in lines[:5]:
        # 跳过过短的行
        if len(line) < 10:
            continue
        # 跳过看起来像页眉的行
        if re.match(r'^(Page|Vol|Issue|DOI|http)', line, re.IGNORECASE):
            continue
        # 跳过全数字行
        if line.isdigit():
            continue
        return line[:200]
    return ""


def _fetch_from_openalex(doi: str) -> dict:
    """从 OpenAlex API 获取补充元数据"""
    import urllib.request
    import urllib.error

    try:
        url = f"https://api.openalex.org/works/doi:{doi}"
        req = urllib.request.Request(url, headers={"User-Agent": "AI-Nexus-Assistant/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        result = {}
        if data.get("title"):
            result["title"] = data["title"]
        if data.get("authorships"):
            authors = []
            for a in data["authorships"]:
                name = a.get("author", {}).get("display_name", "")
                if name:
                    authors.append(name)
            if authors:
                result["authors"] = authors
        if data.get("publication_year"):
            result["year"] = data["publication_year"]
        if data.get("primary_location", {}).get("source", {}).get("display_name"):
            result["journal"] = data["primary_location"]["source"]["display_name"]
        if data.get("abstract_inverted_index"):
            result["abstract"] = _reconstruct_abstract(data["abstract_inverted_index"])

        return result
    except Exception:
        return {}


def _reconstruct_abstract(inverted_index: dict) -> str:
    """从 OpenAlex 倒排索引重建摘要文本"""
    if not inverted_index:
        return ""
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort()
    return " ".join(w for _, w in word_positions)
