"""向量搜索服务 — 基于 sentence-transformers + FAISS"""

import json
import os
import hashlib
from typing import Optional
from sqlalchemy import text
from sqlalchemy.orm import Session


# 嵌入签名（用于检测模型变更）
_EMBED_SIGNATURE_KEY = "embed_signature"


def _get_embed_signature(model_name: str = "all-MiniLM-L6-v2") -> str:
    """生成嵌入配置签名"""
    return hashlib.md5(model_name.encode()).hexdigest()


def _check_embedder_available() -> bool:
    """检查 sentence-transformers 是否可用"""
    try:
        import sentence_transformers
        return True
    except ImportError:
        return False


def _check_faiss_available() -> bool:
    """检查 FAISS 是否可用"""
    try:
        import faiss
        return True
    except ImportError:
        return False


def build_vectors(db: Session, papers_dir: str, model_name: str = "all-MiniLM-L6-v2",
                  rebuild: bool = False) -> dict:
    """构建论文向量索引"""
    if not _check_embedder_available():
        return {"status": "skipped", "reason": "sentence-transformers 未安装"}
    if not _check_faiss_available():
        return {"status": "skipped", "reason": "faiss 未安装"}

    from sentence_transformers import SentenceTransformer
    import numpy as np
    import faiss

    # 检查签名是否变更
    sig = _get_embed_signature(model_name)
    if not rebuild:
        stored_sig = _get_stored_signature(db)
        if stored_sig == sig:
            return {"status": "ok", "reason": "签名未变，跳过重建"}

    # 加载模型
    model = SentenceTransformer(model_name)

    # 获取所有论文
    from app.models.paper import Paper
    papers = db.query(Paper).all()
    if not papers:
        return {"status": "ok", "count": 0}

    # 构建嵌入文本（标题 + 摘要）
    texts = []
    paper_ids = []
    for p in papers:
        embed_text = f"{p.title or ''} {p.abstract or ''}".strip()
        if embed_text:
            texts.append(embed_text)
            paper_ids.append(p.id)

    if not texts:
        return {"status": "ok", "count": 0}

    # 批量嵌入
    embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    embeddings = np.array(embeddings, dtype=np.float32)

    # 构建 FAISS 索引
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # 内积（归一化后等价于余弦相似度）
    index.add(embeddings)

    # 保存到数据库
    _save_vectors(db, paper_ids, embeddings, sig)

    # 保存 FAISS 索引到磁盘
    index_path = _get_index_path(db)
    faiss.write_index(index, index_path)

    return {"status": "ok", "count": len(papers), "dimension": dim}


def vsearch(db: Session, query: str, top_k: int = 10,
            model_name: str = "all-MiniLM-L6-v2") -> list[dict]:
    """向量语义搜索"""
    if not _check_embedder_available() or not _check_faiss_available():
        return []

    from sentence_transformers import SentenceTransformer
    import numpy as np
    import faiss

    # 加载 FAISS 索引
    index_path = _get_index_path(db)
    if not os.path.exists(index_path):
        return []

    index = faiss.read_index(index_path)
    if index.ntotal == 0:
        return []

    # 加载模型并编码查询
    model = SentenceTransformer(model_name)
    query_vec = model.encode([query], normalize_embeddings=True)
    query_vec = np.array(query_vec, dtype=np.float32)

    # 搜索
    scores, indices = index.search(query_vec, min(top_k, index.ntotal))

    # 获取论文 ID
    paper_ids = _get_paper_ids(db)
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or idx >= len(paper_ids):
            continue
        pid = paper_ids[idx]
        from app.models.paper import Paper
        paper = db.get(Paper, pid)
        if paper:
            results.append({
                "id": paper.id,
                "title": paper.title,
                "authors": paper.authors,
                "year": paper.year,
                "doi": paper.doi,
                "abstract": paper.abstract,
                "journal": paper.journal,
                "score": float(score),
                "source": "vector",
            })

    return results


def _save_vectors(db: Session, paper_ids: list[str], embeddings, sig: str):
    """保存向量到数据库"""
    # 创建表（如果不存在）
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS paper_vectors (
            paper_id TEXT PRIMARY KEY,
            embedding BLOB,
            signature TEXT
        )
    """))
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS vector_metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """))

    # 清空旧数据
    db.execute(text("DELETE FROM paper_vectors"))
    db.execute(text("DELETE FROM vector_metadata WHERE key = :key"),
               {"key": _EMBED_SIGNATURE_KEY})

    # 插入新数据
    import numpy as np
    for pid, emb in zip(paper_ids, embeddings):
        blob = emb.tobytes()
        db.execute(text("INSERT INTO paper_vectors (paper_id, embedding, signature) VALUES (:pid, :emb, :sig)"),
                   {"pid": pid, "emb": blob, "sig": sig})

    # 保存签名
    db.execute(text("INSERT INTO vector_metadata (key, value) VALUES (:key, :value)"),
               {"key": _EMBED_SIGNATURE_KEY, "value": sig})

    db.commit()


def _get_stored_signature(db: Session) -> str:
    """获取存储的嵌入签名"""
    try:
        result = db.execute(text("SELECT value FROM vector_metadata WHERE key = :key"),
                            {"key": _EMBED_SIGNATURE_KEY})
        row = result.fetchone()
        return row[0] if row else ""
    except Exception:
        return ""


def _get_paper_ids(db: Session) -> list[str]:
    """获取向量索引中的论文 ID 列表"""
    try:
        result = db.execute(text("SELECT paper_id FROM paper_vectors ORDER BY rowid"))
        return [row[0] for row in result.fetchall()]
    except Exception:
        return []


def search_neighbors(db: Session, paper_id: str, top_k: int = 10,
                     model_name: str = "all-MiniLM-L6-v2") -> list[dict]:
    """找到与指定论文语义最相似的论文（基于 FAISS 向量索引）。

    用于论文详情页的"相关论文"推荐。

    Args:
        db: 数据库会话
        paper_id: 目标论文 ID
        top_k: 返回数量
        model_name: 嵌入模型名

    Returns:
        list[dict]: 相似论文列表，含 score 字段
    """
    if not _check_faiss_available():
        raise ImportError("faiss 未安装")

    import numpy as np
    import faiss

    # 加载 FAISS 索引
    index_path = _get_index_path(db)
    if not os.path.exists(index_path):
        raise FileNotFoundError("向量索引未构建")

    index = faiss.read_index(index_path)
    if index.ntotal == 0:
        return []

    # 获取论文 ID 列表
    paper_ids = _get_paper_ids(db)
    if paper_id not in paper_ids:
        return []

    # 获取目标论文的向量
    target_idx = paper_ids.index(paper_id)
    try:
        result = db.execute(
            text("SELECT embedding FROM paper_vectors WHERE paper_id = :pid"),
            {"pid": paper_id}
        )
        row = result.fetchone()
        if not row:
            return []
        target_vec = np.frombuffer(row[0], dtype=np.float32).reshape(1, -1)
    except Exception:
        return []

    # 搜索（+1 是因为第一个结果是自身）
    scores, indices = index.search(target_vec, min(top_k + 1, index.ntotal))

    from app.models.paper import Paper
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or idx >= len(paper_ids):
            continue
        pid = paper_ids[idx]
        if pid == paper_id:
            continue  # 跳过自身
        paper = db.get(Paper, pid)
        if paper:
            authors = []
            try:
                authors = json.loads(paper.authors) if paper.authors else []
            except (json.JSONDecodeError, TypeError):
                pass
            results.append({
                "id": paper.id,
                "title": paper.title,
                "authors": authors,
                "year": paper.year,
                "doi": paper.doi,
                "journal": paper.journal,
                "score": float(score),
            })
        if len(results) >= top_k:
            break

    return results


def _get_index_path(db: Session) -> str:
    """获取 FAISS 索引文件路径"""
    from app.utils.paths import get_data_dir
    return str(get_data_dir() / "faiss.index")
