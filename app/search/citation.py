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


# ── 引文验证 (4 层) ──────────────────────────────────────────

import re as _re
from urllib.parse import urlparse as _urlparse


def _is_valid_arxiv_id(arxiv_id: str) -> bool:
    """验证 arXiv ID 格式"""
    if not arxiv_id:
        return False
    # 新格式: 2301.12345, 2301.12345v1
    # 旧格式: hep-th/9901001
    patterns = [
        r'^\d{4}\.\d{4,5}(v\d+)?$',
        r'^[a-z\-]+/\d{7}$',
    ]
    return any(_re.match(p, arxiv_id.strip()) for p in patterns)


def _is_valid_doi(doi: str) -> bool:
    """验证 DOI 格式"""
    if not doi:
        return False
    doi = doi.strip()
    # DOI 格式: 10.xxxx/yyyy
    return bool(_re.match(r'^10\.\d{4,}/.+$', doi))


def _has_url(text: str) -> bool:
    """检查文本是否包含有效 URL"""
    if not text:
        return False
    return bool(_re.search(r'https?://\S+', text))


def verify_citation(paper: dict) -> dict:
    """4 层引文验证 (参考 AutoResearchClaw)

    返回:
        {
            "valid": bool,
            "confidence": float (0-1),
            "checks": {
                "arxiv_id": bool,
                "doi": bool,
                "has_url": bool,
                "title_not_empty": bool,
            },
            "issues": list[str]
        }
    """
    checks = {
        "arxiv_id": False,
        "doi": False,
        "has_url": False,
        "title_not_empty": False,
    }
    issues = []

    # 层 1: arXiv ID 验证
    arxiv_id = paper.get("arxiv_id") or paper.get("arxivId") or ""
    if arxiv_id:
        checks["arxiv_id"] = _is_valid_arxiv_id(arxiv_id)
        if not checks["arxiv_id"]:
            issues.append(f"arXiv ID 格式无效: {arxiv_id}")

    # 层 2: DOI 验证
    doi = paper.get("doi") or ""
    if doi:
        checks["doi"] = _is_valid_doi(doi)
        if not checks["doi"]:
            issues.append(f"DOI 格式无效: {doi}")

    # 层 3: URL 验证
    url = paper.get("url") or ""
    checks["has_url"] = _has_url(url)

    # 层 4: 标题非空验证
    title = paper.get("title") or ""
    checks["title_not_empty"] = bool(title.strip())
    if not checks["title_not_empty"]:
        issues.append("标题为空")

    # 计算置信度
    passed = sum(checks.values())
    total = len(checks)
    confidence = passed / total

    # 至少需要标题非空
    valid = checks["title_not_empty"]

    return {
        "valid": valid,
        "confidence": confidence,
        "checks": checks,
        "issues": issues,
    }


def batch_verify_citations(papers: list[dict]) -> list[dict]:
    """批量引文验证，返回验证结果列表"""
    return [verify_citation(p) for p in papers]
