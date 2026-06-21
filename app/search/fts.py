"""FTS5 全文索引 — 替代 LIKE 查询提升搜索性能"""

from sqlalchemy import text
from sqlalchemy.orm import Session


def init_fts(db: Session):
    """初始化 FTS5 虚拟表和同步触发器"""
    # Papers FTS5 虚拟表
    db.execute(text("""
        CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(
            title, authors, journal, abstract,
            content='papers',
            content_rowid='rowid',
            tokenize='unicode61'
        )
    """))

    # Knowledge cards FTS5 虚拟表
    db.execute(text("""
        CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
            title, summary, key_points, user_notes,
            content='knowledge_cards',
            content_rowid='rowid',
            tokenize='unicode61'
        )
    """))

    # Papers 同步触发器
    db.execute(text("""
        CREATE TRIGGER IF NOT EXISTS papers_ai AFTER INSERT ON papers BEGIN
            INSERT INTO papers_fts(rowid, title, authors, journal, abstract)
            VALUES (new.rowid, new.title, new.authors, new.journal, new.abstract);
        END
    """))
    db.execute(text("""
        CREATE TRIGGER IF NOT EXISTS papers_ad AFTER DELETE ON papers BEGIN
            INSERT INTO papers_fts(papers_fts, rowid, title, authors, journal, abstract)
            VALUES ('delete', old.rowid, old.title, old.authors, old.journal, old.abstract);
        END
    """))
    db.execute(text("""
        CREATE TRIGGER IF NOT EXISTS papers_au AFTER UPDATE ON papers BEGIN
            INSERT INTO papers_fts(papers_fts, rowid, title, authors, journal, abstract)
            VALUES ('delete', old.rowid, old.title, old.authors, old.journal, old.abstract);
            INSERT INTO papers_fts(rowid, title, authors, journal, abstract)
            VALUES (new.rowid, new.title, new.authors, new.journal, new.abstract);
        END
    """))

    # Knowledge cards 同步触发器
    db.execute(text("""
        CREATE TRIGGER IF NOT EXISTS knowledge_ai AFTER INSERT ON knowledge_cards BEGIN
            INSERT INTO knowledge_fts(rowid, title, summary, key_points, user_notes)
            VALUES (new.rowid, new.title, new.summary, new.key_points, new.user_notes);
        END
    """))
    db.execute(text("""
        CREATE TRIGGER IF NOT EXISTS knowledge_ad AFTER DELETE ON knowledge_cards BEGIN
            INSERT INTO knowledge_fts(knowledge_fts, rowid, title, summary, key_points, user_notes)
            VALUES ('delete', old.rowid, old.title, old.summary, old.key_points, old.user_notes);
        END
    """))
    db.execute(text("""
        CREATE TRIGGER IF NOT EXISTS knowledge_au AFTER UPDATE ON knowledge_cards BEGIN
            INSERT INTO knowledge_fts(knowledge_fts, rowid, title, summary, key_points, user_notes)
            VALUES ('delete', old.rowid, old.title, old.summary, old.key_points, old.user_notes);
            INSERT INTO knowledge_fts(rowid, title, summary, key_points, user_notes)
            VALUES (new.rowid, new.title, new.summary, new.key_points, new.user_notes);
        END
    """))

    db.commit()


def rebuild_fts(db: Session):
    """重建 FTS5 索引（全量同步）"""
    # 清空 FTS 表
    db.execute(text("INSERT INTO papers_fts(papers_fts) VALUES('rebuild')"))
    db.execute(text("INSERT INTO knowledge_fts(knowledge_fts) VALUES('rebuild')"))
    db.commit()


def search_papers_fts(db: Session, query: str, limit: int = 50) -> list[dict]:
    """使用 FTS5 搜索文献"""
    if not query.strip():
        return []

    # 构建 FTS5 查询：支持中英文分词
    fts_query = _build_fts_query(query)

    try:
        result = db.execute(text("""
            SELECT p.id, p.title, p.authors, p.year, p.doi, p.abstract,
                   p.journal, p.source, p.url, p.citation, p.paper_type,
                   p.has_fulltext, p.star_rating, p.user_notes, p.ai_summary,
                   p.local_path, p.tags, p.created_at,
                   rank
            FROM papers_fts fts
            JOIN papers p ON p.rowid = fts.rowid
            WHERE papers_fts MATCH :query
            ORDER BY rank
            LIMIT :limit
        """), {"query": fts_query, "limit": limit})

        rows = result.fetchall()
        return [_row_to_dict(row) for row in rows]
    except Exception as e:
        # FTS 查询失败时降级到 LIKE
        print(f"[fts] FTS 查询失败，降级到 LIKE: {e}")
        return _fallback_like_search(db, query, limit)


def search_knowledge_fts(db: Session, query: str, limit: int = 50) -> list[dict]:
    """使用 FTS5 搜索知识卡片"""
    if not query.strip():
        return []

    fts_query = _build_fts_query(query)

    try:
        result = db.execute(text("""
            SELECT k.id, k.title, k.summary, k.key_points, k.source_type,
                   k.paper_id, k.category_path, k.star_rating, k.user_notes,
                   k.created_at, k.updated_at,
                   rank
            FROM knowledge_fts fts
            JOIN knowledge_cards k ON k.rowid = fts.rowid
            WHERE knowledge_fts MATCH :query
            ORDER BY rank
            LIMIT :limit
        """), {"query": fts_query, "limit": limit})

        rows = result.fetchall()
        return [_row_to_dict_knowledge(row) for row in rows]
    except Exception as e:
        print(f"[fts] FTS 查询失败，降级到 LIKE: {e}")
        return _fallback_like_search_knowledge(db, query, limit)


def _build_fts_query(query: str) -> str:
    """构建 FTS5 查询表达式"""
    # 清理特殊字符
    import re
    cleaned = re.sub(r'[^\w\s一-鿿]', ' ', query)
    tokens = cleaned.split()

    if not tokens:
        return '""'

    # 对于中文，使用前缀匹配
    # 对于英文，使用词匹配
    fts_tokens = []
    for token in tokens:
        if any('一' <= c <= '鿿' for c in token):
            # 中文 token：前缀匹配
            fts_tokens.append(f'"{token}"')
        else:
            # 英文 token：前缀匹配
            fts_tokens.append(f'{token}*')

    return ' OR '.join(fts_tokens)


def _row_to_dict(row) -> dict:
    """将数据库行转换为字典"""
    return {
        "id": row[0],
        "title": row[1],
        "authors": row[2],
        "year": row[3],
        "doi": row[4],
        "abstract": row[5],
        "journal": row[6],
        "source": row[7],
        "url": row[8],
        "citation": row[9],
        "paper_type": row[10],
        "has_fulltext": row[11],
        "star_rating": row[12],
        "user_notes": row[13],
        "ai_summary": row[14],
        "local_path": row[15],
        "tags": row[16],
        "created_at": row[17],
    }


def _row_to_dict_knowledge(row) -> dict:
    """将知识卡片数据库行转换为字典"""
    return {
        "id": row[0],
        "title": row[1],
        "summary": row[2],
        "key_points": row[3],
        "source_type": row[4],
        "paper_id": row[5],
        "category_path": row[6],
        "star_rating": row[7],
        "user_notes": row[8],
        "created_at": row[9],
        "updated_at": row[10],
    }


def _fallback_like_search(db: Session, query: str, limit: int) -> list[dict]:
    """LIKE 查询降级方案"""
    from app.models.paper import Paper
    from sqlalchemy import or_

    papers = db.query(Paper).filter(or_(
        Paper.title.ilike(f"%{query}%"),
        Paper.authors.ilike(f"%{query}%"),
        Paper.journal.ilike(f"%{query}%"),
        Paper.abstract.ilike(f"%{query}%"),
    )).limit(limit).all()

    return [
        {
            "id": p.id, "title": p.title, "authors": p.authors,
            "year": p.year, "doi": p.doi, "abstract": p.abstract,
            "journal": p.journal, "source": p.source, "url": p.url,
            "citation": p.citation, "paper_type": p.paper_type,
            "has_fulltext": p.has_fulltext, "star_rating": p.star_rating,
            "user_notes": p.user_notes, "ai_summary": p.ai_summary,
            "local_path": p.local_path, "tags": p.tags,
            "created_at": str(p.created_at),
        }
        for p in papers
    ]


def _fallback_like_search_knowledge(db: Session, query: str, limit: int) -> list[dict]:
    """知识卡片 LIKE 查询降级方案"""
    from app.models.knowledge import KnowledgeCard
    from sqlalchemy import or_

    cards = db.query(KnowledgeCard).filter(or_(
        KnowledgeCard.title.ilike(f"%{query}%"),
        KnowledgeCard.summary.ilike(f"%{query}%"),
        KnowledgeCard.user_notes.ilike(f"%{query}%"),
    )).limit(limit).all()

    return [
        {
            "id": c.id, "title": c.title, "summary": c.summary,
            "key_points": c.key_points, "source_type": c.source_type,
            "paper_id": c.paper_id, "category_path": c.category_path,
            "star_rating": c.star_rating, "user_notes": c.user_notes,
            "created_at": str(c.created_at), "updated_at": str(c.updated_at),
        }
        for c in cards
    ]
