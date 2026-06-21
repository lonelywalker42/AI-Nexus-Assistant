"""引用图谱服务 — 正向/反向引用查询"""

import json
from typing import Optional
from sqlalchemy import text
from sqlalchemy.orm import Session


def init_citations_table(db: Session):
    """初始化引用关系表"""
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS citations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            target_doi TEXT,
            target_id TEXT,
            FOREIGN KEY (source_id) REFERENCES papers(id) ON DELETE CASCADE
        )
    """))
    db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_citations_source ON citations(source_id)
    """))
    db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_citations_target_doi ON citations(target_doi)
    """))
    db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_citations_target_id ON citations(target_id)
    """))
    db.commit()


def build_citations(db: Session) -> dict:
    """从论文摘要中提取引用关系"""
    from app.models.paper import Paper
    import re

    init_citations_table(db)

    # 清空旧数据
    db.execute(text("DELETE FROM citations"))

    papers = db.query(Paper).all()
    doi_map = {}
    for p in papers:
        if p.doi:
            doi_map[p.doi.lower()] = p.id

    # DOI 正则
    doi_pattern = re.compile(r'\b(10\.\d{4,}/[^\s,;]{5,})\b')

    total_refs = 0
    for p in papers:
        # 从摘要中提取 DOI
        text_content = p.abstract or ""
        dois = doi_pattern.findall(text_content)

        for doi in dois:
            doi = doi.rstrip('.').rstrip(')')
            target_id = doi_map.get(doi.lower())

            db.execute(text("""
                INSERT INTO citations (source_id, target_doi, target_id)
                VALUES (:sid, :tdoi, :tid)
            """), {
                "sid": p.id,
                "tdoi": doi,
                "tid": target_id,
            })
            total_refs += 1

    db.commit()

    return {
        "status": "ok",
        "total_papers": len(papers),
        "total_references": total_refs,
    }


def get_references(db: Session, paper_id: str) -> list[dict]:
    """获取论文的参考文献（正向引用）"""
    from app.models.paper import Paper

    result = db.execute(text("""
        SELECT target_doi, target_id FROM citations WHERE source_id = :sid
    """), {"sid": paper_id})

    refs = []
    for row in result.fetchall():
        doi = row[0]
        target_id = row[1]

        ref = {"doi": doi, "in_library": False}
        if target_id:
            paper = db.get(Paper, target_id)
            if paper:
                ref["in_library"] = True
                ref["id"] = paper.id
                ref["title"] = paper.title
                ref["authors"] = paper.authors
                ref["year"] = paper.year
                ref["journal"] = paper.journal

        refs.append(ref)

    return refs


def get_citing_papers(db: Session, paper_id: str) -> list[dict]:
    """获取引用此论文的其他论文（反向引用）"""
    from app.models.paper import Paper

    paper = db.get(Paper, paper_id)
    if not paper:
        return []

    # 查找引用此论文的记录
    result = db.execute(text("""
        SELECT DISTINCT source_id FROM citations
        WHERE target_id = :tid OR target_doi = :tdoi
    """), {"tid": paper_id, "tdoi": paper.doi or ""})

    citing = []
    for row in result.fetchall():
        source_id = row[0]
        if source_id == paper_id:
            continue
        source = db.get(Paper, source_id)
        if source:
            citing.append({
                "id": source.id,
                "title": source.title,
                "authors": source.authors,
                "year": source.year,
                "journal": source.journal,
            })

    return citing


def get_shared_references(db: Session, paper_ids: list[str]) -> list[dict]:
    """获取多篇论文的共同引用"""
    from app.models.paper import Paper

    if len(paper_ids) < 2:
        return []

    # 获取每篇论文的引用
    all_refs: dict[str, set] = {}
    for pid in paper_ids:
        result = db.execute(text("""
            SELECT target_doi, target_id FROM citations WHERE source_id = :sid
        """), {"sid": pid})
        for row in result.fetchall():
            doi = row[0]
            target_id = row[1] or doi
            if target_id:
                if target_id not in all_refs:
                    all_refs[target_id] = set()
                all_refs[target_id].add(pid)

    # 找出被多篇论文引用的文献
    shared = []
    for target, sources in all_refs.items():
        if len(sources) >= 2:
            ref = {"target": target, "cited_by_count": len(sources), "cited_by": list(sources)}

            # 尝试获取论文详情
            if target in [p.id for p in db.query(Paper).all()]:
                paper = db.get(Paper, target)
                if paper:
                    ref["title"] = paper.title
                    ref["authors"] = paper.authors
                    ref["year"] = paper.year

            shared.append(ref)

    shared.sort(key=lambda x: -x["cited_by_count"])
    return shared


def get_citation_stats(db: Session) -> dict:
    """获取引用统计"""
    try:
        total = db.execute(text("SELECT COUNT(*) FROM citations")).fetchone()[0]
        unique_targets = db.execute(text("SELECT COUNT(DISTINCT target_doi) FROM citations WHERE target_doi != ''")).fetchone()[0]
        resolved = db.execute(text("SELECT COUNT(*) FROM citations WHERE target_id IS NOT NULL")).fetchone()[0]

        return {
            "total_references": total,
            "unique_targets": unique_targets,
            "resolved_in_library": resolved,
        }
    except Exception:
        return {"total_references": 0, "unique_targets": 0, "resolved_in_library": 0}
