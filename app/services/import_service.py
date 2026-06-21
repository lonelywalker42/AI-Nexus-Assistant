"""多源文献导入服务 — BibTeX / RIS / 批量 PDF"""

import re
import json
import logging
from typing import Optional

_log = logging.getLogger("nexus.import_service")


# ══════════════════════════════════════════════════════════════
#  BibTeX 解析
# ══════════════════════════════════════════════════════════════


def parse_bibtex(content: str) -> list[dict]:
    """解析 BibTeX 文件内容。

    Returns:
        list[dict]: [{title, authors, year, doi, journal, abstract, paper_type, ...}]
    """
    entries = []
    # 匹配 @type{key, fields...} 块
    pattern = r'@(\w+)\s*\{([^,]+),\s*(.*?)\n\s*\}'
    for m in re.finditer(pattern, content, re.DOTALL | re.IGNORECASE):
        entry_type = m.group(1).lower()
        fields_str = m.group(3)
        fields = _parse_bibtex_fields(fields_str)

        if not fields.get("title") and not fields.get("author"):
            continue

        # 解析作者
        authors = []
        if fields.get("author"):
            for a in re.split(r'\s+and\s+', fields["author"]):
                a = a.strip()
                if a:
                    # "Last, First" → "First Last"
                    if "," in a:
                        parts = a.split(",", 1)
                        a = f"{parts[1].strip()} {parts[0].strip()}"
                    authors.append(a)

        # 解析年份
        year = 0
        for key in ["year", "date"]:
            if fields.get(key):
                match = re.search(r'(\d{4})', fields[key])
                if match:
                    year = int(match.group(1))
                    break

        entry = {
            "title": _clean_tex(fields.get("title", "")),
            "authors": authors,
            "year": year,
            "doi": _clean_tex(fields.get("doi", "")),
            "journal": _clean_tex(fields.get("journal", "") or fields.get("booktitle", "")),
            "abstract": _clean_tex(fields.get("abstract", "")),
            "url": fields.get("url", ""),
            "paper_type": _bibtex_type_to_paper_type(entry_type),
            "keywords": _clean_tex(fields.get("keywords", "")),
        }
        entries.append(entry)

    _log.info(f"BibTeX 解析完成: {len(entries)} 条记录")
    return entries


def _parse_bibtex_fields(fields_str: str) -> dict:
    """解析 BibTeX 字段"""
    fields = {}
    # 匹配 key = {value} 或 key = value
    pattern = r'(\w+)\s*=\s*(?:\{((?:[^{}]|\{[^{}]*\})*)\}|([^\n,}]+))'
    for m in re.finditer(pattern, fields_str, re.DOTALL):
        key = m.group(1).lower().strip()
        value = (m.group(2) or m.group(3) or "").strip()
        if key and value:
            fields[key] = value
    return fields


def _clean_tex(text: str) -> str:
    """清理 LaTeX 特殊字符"""
    if not text:
        return ""
    # 移除大括号
    text = re.sub(r'[{}]', '', text)
    # 常见 LaTeX 命令
    text = re.sub(r'\\[a-zA-Z]+\s*', '', text)
    # 多余空白
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _bibtex_type_to_paper_type(entry_type: str) -> str:
    """BibTeX 条目类型 → 论文类型"""
    mapping = {
        "article": "journal",
        "inproceedings": "conference",
        "conference": "conference",
        "book": "book",
        "incollection": "book_chapter",
        "phdthesis": "thesis",
        "mastersthesis": "thesis",
        "techreport": "report",
        "misc": "preprint",
        "unpublished": "preprint",
    }
    return mapping.get(entry_type.lower(), "未知")


# ══════════════════════════════════════════════════════════════
#  RIS 解析
# ══════════════════════════════════════════════════════════════


def parse_ris(content: str) -> list[dict]:
    """解析 RIS 文件内容。

    Returns:
        list[dict]: [{title, authors, year, doi, journal, abstract, paper_type, ...}]
    """
    entries = []
    current = {}
    authors = []

    for line in content.split("\n"):
        line = line.rstrip()
        if not line:
            continue

        # RIS 格式: "TAG  - value"
        match = re.match(r'^([A-Z][A-Z0-9])\s{2}-\s*(.*)', line)
        if not match:
            continue

        tag = match.group(1)
        value = match.group(2).strip()

        if tag == "ER":
            # 记录结束
            if current:
                current["authors"] = authors
                if not current.get("paper_type"):
                    current["paper_type"] = "journal"
                entries.append(current)
            current = {}
            authors = []

        elif tag == "TY":
            current["paper_type"] = _ris_type_to_paper_type(value)

        elif tag == "TI" or tag == "T1":
            current["title"] = value

        elif tag == "AU":
            # "Last, First" → "First Last"
            if "," in value:
                parts = value.split(",", 1)
                authors.append(f"{parts[1].strip()} {parts[0].strip()}")
            else:
                authors.append(value)

        elif tag == "PY" or tag == "Y1":
            match_y = re.search(r'(\d{4})', value)
            if match_y:
                current["year"] = int(match_y.group(1))

        elif tag == "DO":
            current["doi"] = value

        elif tag == "JO" or tag == "JA" or tag == "JF" or tag == "T2":
            if not current.get("journal"):
                current["journal"] = value

        elif tag == "AB":
            current["abstract"] = value

        elif tag == "UR":
            current["url"] = value

        elif tag == "KW":
            kw = current.get("keywords", "")
            current["keywords"] = f"{kw}; {value}" if kw else value

        elif tag == "SP":
            current["page_start"] = value
        elif tag == "EP":
            current["page_end"] = value

    # 最后一条记录（如果没有 ER 标记）
    if current:
        current["authors"] = authors
        entries.append(current)

    # 标准化
    for entry in entries:
        entry.setdefault("title", "")
        entry.setdefault("authors", [])
        entry.setdefault("year", 0)
        entry.setdefault("doi", "")
        entry.setdefault("journal", "")
        entry.setdefault("abstract", "")
        entry.setdefault("source", "ris_import")

    _log.info(f"RIS 解析完成: {len(entries)} 条记录")
    return entries


def _ris_type_to_paper_type(ris_type: str) -> str:
    """RIS 类型 → 论文类型"""
    mapping = {
        "JOUR": "journal",
        "CONF": "conference",
        "CHAP": "book_chapter",
        "BOOK": "book",
        "THES": "thesis",
        "RPRT": "report",
        "UNPB": "preprint",
        "GEN": "未知",
    }
    return mapping.get(ris_type.upper(), "未知")


# ══════════════════════════════════════════════════════════════
#  自动检测格式
# ══════════════════════════════════════════════════════════════


def detect_and_parse(content: str, filename: str = "") -> list[dict]:
    """自动检测文件格式并解析。

    Args:
        content: 文件内容
        filename: 文件名（用于扩展名检测）

    Returns:
        list[dict]: 解析后的记录
    """
    # 扩展名优先
    lower_name = filename.lower()
    if lower_name.endswith(".bib"):
        return parse_bibtex(content)
    elif lower_name.endswith(".ris"):
        return parse_ris(content)

    # 内容检测
    stripped = content.strip()
    if stripped.startswith("@") or "@" in stripped[:100]:
        return parse_bibtex(content)
    elif re.match(r'^TY\s+-\s+', stripped, re.MULTILINE):
        return parse_ris(content)

    # 默认尝试 BibTeX
    result = parse_bibtex(content)
    if result:
        return result
    return parse_ris(content)


def import_entries_to_db(entries: list[dict], session) -> list[dict]:
    """将解析后的记录导入数据库（DOI 优先去重）。

    Args:
        entries: 解析后的记录列表
        session: SQLAlchemy 会话

    Returns:
        list[dict]: [{title, paper_id, status}]
    """
    from app.services.paper_service import save_from_search

    results = []
    for entry in entries:
        title = entry.get("title", "")
        if not title:
            results.append({"title": "(无标题)", "status": "skipped"})
            continue

        try:
            paper = save_from_search(session, entry)
            # 检查是否是已存在的记录
            if paper:
                results.append({
                    "title": title,
                    "paper_id": paper.id,
                    "status": "imported",
                })
        except Exception as e:
            _log.warning(f"导入失败 [{title[:50]}]: {e}")
            results.append({
                "title": title,
                "status": "failed",
                "error": str(e),
            })

    imported = sum(1 for r in results if r.get("status") == "imported")
    _log.info(f"导入完成: {imported}/{len(results)} 成功")
    return results
