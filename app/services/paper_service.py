"""文献库服务层 — Paper CRUD + 入库 + 引用 + AI 总结"""

import json
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session, defer
from sqlalchemy import func, or_
from app.models.paper import Paper


def get_papers(db: Session, search: str = "", sort_by: str = "created_at",
               sort_order: str = "desc", year_from: int = 0, year_to: int = 0,
               star_min: int = 0, limit: int | None = None,
               offset: int = 0) -> list[Paper]:
    """获取文献列表（筛选/排序）"""
    # Full text can be several megabytes and is not part of list responses.
    q = db.query(Paper).options(defer(Paper.fulltext))
    if search:
        q = q.filter(or_(
            Paper.title.ilike(f"%{search}%"),
            Paper.authors.ilike(f"%{search}%"),
            Paper.journal.ilike(f"%{search}%"),
            Paper.abstract.ilike(f"%{search}%"),
        ))
    if year_from > 0:
        q = q.filter(Paper.year >= year_from)
    if year_to > 0:
        q = q.filter(Paper.year <= year_to)
    if star_min > 0:
        q = q.filter(Paper.star_rating >= star_min)

    # 排序
    sort_col = getattr(Paper, sort_by, Paper.created_at)
    if sort_order == "asc":
        q = q.order_by(sort_col.asc())
    else:
        q = q.order_by(sort_col.desc())

    if offset > 0:
        q = q.offset(offset)
    if limit is not None:
        q = q.limit(limit)
    return q.all()


def get_paper(db: Session, paper_id: str) -> Optional[Paper]:
    """获取单篇文献"""
    return db.get(Paper, paper_id)


def create_paper(db: Session, **kwargs) -> Paper:
    """创建文献记录"""
    paper = Paper(**kwargs)
    db.add(paper)
    db.commit()
    db.refresh(paper)
    return paper


def update_paper(db: Session, paper_id: str, **kwargs) -> Optional[Paper]:
    """更新文献"""
    paper = db.get(Paper, paper_id)
    if not paper:
        return None
    for key, value in kwargs.items():
        if key == "tags" and isinstance(value, list):
            value = json.dumps(value, ensure_ascii=False)
        if hasattr(paper, key):
            setattr(paper, key, value)
    db.commit()
    db.refresh(paper)
    return paper


def delete_paper(db: Session, paper_id: str) -> bool:
    """删除文献"""
    paper = db.get(Paper, paper_id)
    if not paper:
        return False
    db.delete(paper)
    db.commit()
    return True


def delete_papers_batch(db: Session, paper_ids: list[str]) -> int:
    """批量删除文献"""
    count = db.query(Paper).filter(Paper.id.in_(paper_ids)).delete()
    db.commit()
    return count


def save_from_search(db: Session, paper_data: dict) -> Paper:
    """从搜索结果入库（DOI 优先去重 → 标题降级去重）"""
    title = paper_data.get("title", "")
    if not title:
        raise ValueError("文献标题不能为空")

    # 1. DOI 去重（优先级最高）
    doi = str(paper_data.get("doi", "")).strip().lower()
    if doi:
        existing = db.query(Paper).filter(func.lower(Paper.doi) == doi).first()
        if existing:
            return existing

    # 2. 标题精确匹配去重（降级方案）
    existing = db.query(Paper).filter(Paper.title == title).first()
    if existing:
        return existing

    # 清洗 authors 数据
    authors = paper_data.get("authors", [])
    if isinstance(authors, str):
        try:
            authors = json.loads(authors)
        except (json.JSONDecodeError, TypeError):
            authors = [authors] if authors else []
    if not isinstance(authors, list):
        authors = []
    authors = [a for a in authors if a]  # 过滤空字符串
    authors_json = json.dumps(authors, ensure_ascii=False)

    # 清洗 year
    year = paper_data.get("year", 0)
    if isinstance(year, str):
        try:
            year = int(year)
        except (ValueError, TypeError):
            year = 0
    elif not isinstance(year, int):
        year = 0

    # 生成 GB/T 7714 引用（容错处理）
    citation = ""
    try:
        from app.search.citation import format_gb
        citation = format_gb(paper_data, 1)
    except Exception:
        pass  # 引用生成失败不影响入库

    paper = Paper(
        title=title[:500],
        authors=authors_json,
        year=year,
        doi=str(paper_data.get("doi", ""))[:200],
        abstract=str(paper_data.get("abstract", ""))[:10000],
        journal=str(paper_data.get("journal", ""))[:500],
        source=str(paper_data.get("source", ""))[:50],
        url=str(paper_data.get("url", ""))[:1000],
        citation=citation,
        paper_type=str(paper_data.get("paper_type", "未知"))[:50],
        has_fulltext=bool(paper_data.get("has_fulltext", False)),
        star_rating=int(paper_data.get("star_rating", 0)) if paper_data.get("star_rating") else 0,
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)
    return paper


def get_citation(db: Session, paper_id: str, fmt: str = "gb7714", idx: int = 1) -> str:
    """获取指定格式的引用"""
    paper = db.get(Paper, paper_id)
    if not paper:
        return ""

    paper_dict = {
        "title": paper.title,
        "authors": json.loads(paper.authors) if paper.authors else [],
        "year": paper.year,
        "doi": paper.doi,
        "journal": paper.journal,
        "paper_type": paper.paper_type,
    }

    if fmt == "gb7714":
        from app.search.citation import format_gb
        return format_gb(paper_dict, idx)
    elif fmt == "apa":
        return _format_apa(paper_dict)
    elif fmt == "ieee":
        return _format_ieee(paper_dict, idx)
    elif fmt == "mla":
        return _format_mla(paper_dict)
    elif fmt == "bibtex":
        return _format_bibtex(paper_dict, paper)
    else:
        from app.search.citation import format_gb
        return format_gb(paper_dict, idx)


def _format_apa(paper: dict) -> str:
    """APA 7th edition 格式"""
    authors = paper.get("authors", [])
    year = paper.get("year", "n.d.")
    title = paper.get("title", "")
    journal = paper.get("journal", "")
    doi = paper.get("doi", "")

    if not authors:
        author_str = "Unknown Author"
    elif len(authors) == 1:
        parts = authors[0].split()
        author_str = f"{parts[-1]}, {' '.join(p[0] + '.' for p in parts[:-1])}" if len(parts) > 1 else authors[0]
    elif len(authors) <= 20:
        formatted = []
        for a in authors:
            parts = a.split()
            if len(parts) > 1:
                formatted.append(f"{parts[-1]}, {' '.join(p[0] + '.' for p in parts[:-1])}")
            else:
                formatted.append(a)
        author_str = ", ".join(formatted[:-1]) + ", & " + formatted[-1]
    else:
        parts = authors[0].split()
        first = f"{parts[-1]}, {' '.join(p[0] + '.' for p in parts[:-1])}" if len(parts) > 1 else authors[0]
        author_str = f"{first}, ... {authors[-1].split()[-1]}"

    s = f"{author_str} ({year}). {title}."
    if journal:
        s += f" *{journal}*."
    if doi:
        s += f" https://doi.org/{doi}"
    return s


def _format_ieee(paper: dict, idx: int = 1) -> str:
    """IEEE 格式"""
    authors = paper.get("authors", [])
    year = paper.get("year", "")
    title = paper.get("title", "")
    journal = paper.get("journal", "")

    formatted = []
    for a in authors:
        parts = a.split()
        if len(parts) > 1:
            formatted.append(f"{' '.join(p[0] + '.' for p in parts[:-1])} {parts[-1]}")
        else:
            formatted.append(a)
    author_str = ", ".join(formatted) if formatted else "Unknown"

    s = f"[{idx}] {author_str}, \"{title}\""
    if journal:
        s += f", *{journal}*"
    if year:
        s += f", {year}"
    s += "."
    return s


def _format_mla(paper: dict) -> str:
    """MLA 9th edition 格式"""
    authors = paper.get("authors", [])
    year = paper.get("year", "")
    title = paper.get("title", "")
    journal = paper.get("journal", "")

    if not authors:
        author_str = "Unknown Author"
    elif len(authors) == 1:
        parts = authors[0].split()
        author_str = f"{parts[-1]}, {' '.join(parts[:-1])}" if len(parts) > 1 else authors[0]
    elif len(authors) == 2:
        parts = authors[0].split()
        first = f"{parts[-1]}, {' '.join(parts[:-1])}" if len(parts) > 1 else authors[0]
        author_str = f"{first}, and {authors[1]}"
    else:
        parts = authors[0].split()
        author_str = f"{parts[-1]}, {' '.join(parts[:-1])}, et al." if len(parts) > 1 else f"{authors[0]}, et al."

    s = f'{author_str}. "{title}."'
    if journal:
        s += f" *{journal}*"
    if year:
        s += f", {year}"
    s += "."
    return s


def _format_bibtex(paper: dict, paper_obj: Paper) -> str:
    """BibTeX 格式"""
    authors = paper.get("authors", [])
    year = paper.get("year", "")
    title = paper.get("title", "")
    journal = paper.get("journal", "")
    doi = paper.get("doi", "")

    # 生成 cite key: 第一作者姓 + 年份
    if authors:
        first_author = authors[0].split()[-1].lower() if authors[0] else "unknown"
    else:
        first_author = "unknown"
    cite_key = f"{first_author}{year}"

    author_str = " and ".join(authors) if authors else "Unknown"

    s = f"@article{{{cite_key},\n"
    s += f"  author = {{{author_str}}},\n"
    s += f"  title = {{{title}}},\n"
    if journal:
        s += f"  journal = {{{journal}}},\n"
    if year:
        s += f"  year = {{{year}}},\n"
    if doi:
        s += f"  doi = {{{doi}}},\n"
    s += "}"
    return s


def generate_ai_summary(db: Session, paper_id: str, ai_router) -> Optional[Paper]:
    """生成 AI 摘要"""
    paper = db.get(Paper, paper_id)
    if not paper:
        return None

    text = f"标题: {paper.title}\n"
    if paper.abstract:
        text += f"摘要: {paper.abstract}\n"
    authors = json.loads(paper.authors) if paper.authors else []
    if authors:
        text += f"作者: {', '.join(authors[:5])}\n"
    if paper.journal:
        text += f"期刊: {paper.journal}\n"

    result = ai_router.chat([
        {"role": "system", "content": "你是学术文献分析助手。请用中文为以下论文生成简短总结(200字以内)，包含：研究目的、方法、主要发现。"},
        {"role": "user", "content": text}
    ])

    paper.ai_summary = result.get("content", "")
    db.commit()
    db.refresh(paper)
    return paper


def get_paper_stats(db: Session) -> dict:
    """获取文献库统计"""
    total = db.query(func.count(Paper.id)).scalar() or 0
    by_source = {}
    for src in ["openalex", "arxiv", "crossref", "semantic_scholar", "pubmed", "manual"]:
        count = db.query(func.count(Paper.id)).filter(Paper.source == src).scalar() or 0
        if count > 0:
            by_source[src] = count
    rated = db.query(func.count(Paper.id)).filter(Paper.star_rating > 0).scalar() or 0
    return {"total": total, "by_source": by_source, "rated": rated}
