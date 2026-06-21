"""主题发现服务 — 基于 BERTopic 的自动主题聚类"""

import json
from typing import Optional
from sqlalchemy.orm import Session


def _check_bertopic_available() -> bool:
    """检查 BERTopic 是否可用"""
    try:
        import bertopic
        return True
    except ImportError:
        return False


def build_topics(db: Session, min_topic_size: int = 3) -> dict:
    """构建主题模型"""
    if not _check_bertopic_available():
        return {"status": "skipped", "reason": "BERTopic 未安装，请运行: pip install bertopic"}

    from bertopic import BERTopic
    from app.models.paper import Paper
    import numpy as np

    # 获取所有论文
    papers = db.query(Paper).all()
    if len(papers) < 5:
        return {"status": "skipped", "reason": f"论文数量不足（{len(papers)}篇，至少需要5篇）"}

    # 构建文档列表
    docs = []
    paper_ids = []
    for p in papers:
        text = f"{p.title or ''} {p.abstract or ''}".strip()
        if text and len(text) > 20:
            docs.append(text)
            paper_ids.append(p.id)

    if len(docs) < 5:
        return {"status": "skipped", "reason": "有效文档数量不足"}

    # 加载嵌入（如果已有）
    embeddings = _load_embeddings(db, paper_ids)

    # 构建主题模型
    topic_model = BERTopic(
        min_topic_size=min_topic_size,
        verbose=False,
        calculate_probabilities=False,
    )

    if embeddings is not None:
        topics, probs = topic_model.fit_transform(docs, embeddings=embeddings)
    else:
        topics, probs = topic_model.fit_transform(docs)

    # 保存结果
    _save_topics(db, topic_model, paper_ids, topics)

    # 获取主题概览
    overview = get_topic_overview(db)

    return {
        "status": "ok",
        "total_papers": len(docs),
        "num_topics": len(overview.get("topics", [])),
        "topics": overview.get("topics", []),
    }


def get_topic_overview(db: Session) -> dict:
    """获取主题概览"""
    try:
        from app.models.paper import Paper
        from sqlalchemy import text, inspect

        # 检查表是否存在
        inspector = inspect(db.get_bind())
        if "paper_topics" not in inspector.get_table_names():
            return {"topics": [], "count": 0}

        # 从数据库加载主题数据
        result = db.execute(text("""
            SELECT topic_id, paper_ids, keywords, label
            FROM paper_topics
            ORDER BY topic_id
        """))

        topics = []
        for row in result.fetchall():
            topic_id = row[0]
            paper_ids = json.loads(row[1]) if row[1] else []
            keywords = json.loads(row[2]) if row[2] else []
            label = row[3] or f"Topic {topic_id}"

            # 获取论文标题
            paper_titles = []
            for pid in paper_ids[:5]:  # 只取前5篇
                paper = db.get(Paper, pid)
                if paper:
                    paper_titles.append(paper.title)

            topics.append({
                "id": topic_id,
                "label": label,
                "keywords": keywords[:10],
                "paper_count": len(paper_ids),
                "sample_papers": paper_titles,
            })

        return {"topics": topics, "count": len(topics)}
    except Exception as e:
        return {"topics": [], "count": 0, "error": str(e)}


def get_topic_papers(db: Session, topic_id: int) -> list[dict]:
    """获取主题下的论文"""
    try:
        from app.models.paper import Paper
        from sqlalchemy import text

        result = db.execute(text("""
            SELECT paper_ids FROM paper_topics WHERE topic_id = :tid
        """), {"tid": topic_id})
        row = result.fetchone()
        if not row:
            return []

        paper_ids = json.loads(row[0]) if row[0] else []
        papers = []
        for pid in paper_ids:
            paper = db.get(Paper, pid)
            if paper:
                papers.append({
                    "id": paper.id,
                    "title": paper.title,
                    "authors": paper.authors,
                    "year": paper.year,
                    "journal": paper.journal,
                    "abstract": (paper.abstract or "")[:200],
                })
        return papers
    except Exception:
        return []


def _load_embeddings(db: Session, paper_ids: list[str]):
    """加载预计算的嵌入"""
    try:
        from sqlalchemy import text
        import numpy as np

        result = db.execute(text("SELECT paper_id, embedding FROM paper_vectors"))
        emb_map = {}
        for row in result.fetchall():
            emb_map[row[0]] = np.frombuffer(row[1], dtype=np.float32)

        embeddings = []
        for pid in paper_ids:
            if pid in emb_map:
                embeddings.append(emb_map[pid])
            else:
                return None  # 缺失嵌入，返回 None

        return np.array(embeddings, dtype=np.float32)
    except Exception:
        return None


def _save_topics(db: Session, topic_model, paper_ids: list[str], topics: list[int]):
    """保存主题结果到数据库"""
    from sqlalchemy import text

    # 创建表
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS paper_topics (
            topic_id INTEGER PRIMARY KEY,
            paper_ids TEXT,
            keywords TEXT,
            label TEXT
        )
    """))

    # 清空旧数据
    db.execute(text("DELETE FROM paper_topics"))

    # 按主题分组
    topic_groups: dict[int, list[str]] = {}
    for pid, tid in zip(paper_ids, topics):
        if tid == -1:  # 跳过离群点
            continue
        if tid not in topic_groups:
            topic_groups[tid] = []
        topic_groups[tid].append(pid)

    # 获取主题信息
    topic_info = topic_model.get_topic_info()

    # 保存每个主题
    for _, row in topic_info.iterrows():
        tid = row["Topic"]
        if tid == -1:
            continue

        # 获取主题关键词
        topic_words = topic_model.get_topic(tid)
        keywords = [w for w, _ in topic_words[:10]] if topic_words else []

        # 获取主题标签
        label = row.get("Name", f"Topic {tid}")

        # 保存
        db.execute(text("""
            INSERT INTO paper_topics (topic_id, paper_ids, keywords, label)
            VALUES (:tid, :pids, :kw, :label)
        """), {
            "tid": tid,
            "pids": json.dumps(topic_groups.get(tid, [])),
            "kw": json.dumps(keywords),
            "label": str(label)[:200],
        })

    db.commit()
