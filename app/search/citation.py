"""GB/T 7714-2015 引用格式化 — 从 ai-literature (JS) 移植到 Python"""

import re


def detect_lang(text: str) -> str:
    """检测文本语言：'cn' 或 'en'"""
    cn_count = len(re.findall(r'[一-鿿]', text))
    return "cn" if cn_count > len(text) * 0.2 else "en"


def type_gb(paper_type: str) -> str:
    """文献类型 → GB/T 7714 类型标识"""
    s = (paper_type or "").lower()
    if "conference" in s or "proceeding" in s:
        return "C"
    if "thesis" in s or "dissertation" in s:
        return "D"
    if "book" in s and "chapter" not in s:
        return "M"
    return "J"


def format_gb(paper: dict, idx: int) -> str:
    """生成 GB/T 7714 格式引用

    Args:
        paper: 包含 title, authors, year, journal, doi, paper_type 等字段的字典
        idx: 引用序号
    """
    title = paper.get("title", "")
    authors = paper.get("authors", [])
    year = paper.get("year", "")
    journal = paper.get("journal", "")
    doi = paper.get("doi", "")
    ptype = paper.get("paper_type", "未知")
    volume = paper.get("volume", "")
    issue = paper.get("issue", "")
    first_page = paper.get("first_page", "")
    last_page = paper.get("last_page", "")

    lang = detect_lang(f"{title} {journal} {' '.join(authors)}")
    typ = type_gb(ptype)

    # 作者格式化
    if lang == "cn":
        if len(authors) > 3:
            authors_str = ", ".join(authors[:3]) + ", 等"
        else:
            authors_str = ", ".join(authors)
    else:
        fmt = []
        for a in authors:
            parts = re.split(r'[\s,]+', a)
            parts = [p for p in parts if p]
            if len(parts) >= 2:
                fmt.append(parts[0].upper() + " " + " ".join(p[0].upper() for p in parts[1:] if p))
            else:
                fmt.append(a.upper())
        if len(fmt) > 3:
            authors_str = ", ".join(fmt[:3]) + ", et al."
        else:
            authors_str = ", ".join(fmt)

    # 页码
    pages = ""
    if first_page:
        pages = f"{first_page}-{last_page}" if last_page else first_page

    # 组装
    s = f"[{idx}] {authors_str}. {title}"
    if typ == "C":
        s += "[C]//"
    else:
        s += f"[{typ}]. "

    if journal:
        s += journal
    if year:
        s += f", {year}"
    if volume:
        s += f", {volume}"
    if issue:
        s += f"({issue})"
    if pages:
        s += f": {pages}"
    s += "."

    # 清理
    s = s.replace("..", ".").replace(", ,", ",")
    return s
