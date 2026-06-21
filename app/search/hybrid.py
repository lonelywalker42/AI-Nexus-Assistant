"""混合搜索 — FTS5 关键词 + 向量语义 RRF 融合排序"""

from typing import Optional
from sqlalchemy.orm import Session


def hybrid_search(db: Session, query: str, top_k: int = 20,
                  fts_weight: float = 1.0, vec_weight: float = 1.0,
                  rrf_k: int = 60) -> list[dict]:
    """混合搜索：FTS5 + 向量 RRF 融合

    参考：Cormack et al., SIGIR 2009
    公式：score(d) = Σ weight_i / (k + rank_i(d))
    """
    from app.search.fts import search_papers_fts
    from app.search.vectors import vsearch

    # 并行获取两个搜索结果
    fts_results = search_papers_fts(db, query, limit=top_k * 2)
    vec_results = vsearch(db, query, top_k=top_k * 2)

    # RRF 融合
    scores: dict[str, float] = {}
    sources: dict[str, set] = {}
    paper_map: dict[str, dict] = {}

    # FTS 结果
    for rank, paper in enumerate(fts_results, 1):
        pid = paper.get("id", "")
        if not pid:
            continue
        scores[pid] = scores.get(pid, 0) + fts_weight / (rrf_k + rank)
        sources[pid] = sources.get(pid, set()) | {"fts"}
        paper_map[pid] = paper

    # 向量结果
    for rank, paper in enumerate(vec_results, 1):
        pid = paper.get("id", "")
        if not pid:
            continue
        scores[pid] = scores.get(pid, 0) + vec_weight / (rrf_k + rank)
        sources[pid] = sources.get(pid, set()) | {"vec"}
        if pid not in paper_map:
            paper_map[pid] = paper

    # 排序
    ranked = sorted(scores.items(), key=lambda x: -x[1])

    # 构建结果
    results = []
    for pid, score in ranked[:top_k]:
        paper = paper_map.get(pid, {})
        paper["rrf_score"] = score
        paper["search_source"] = "+".join(sorted(sources.get(pid, set())))
        results.append(paper)

    return results


def search_with_fallback(db: Session, query: str, top_k: int = 20) -> list[dict]:
    """搜索（自动降级：混合 → FTS5 → LIKE）"""
    # 尝试混合搜索
    try:
        results = hybrid_search(db, query, top_k=top_k)
        if results:
            return results
    except Exception as e:
        print(f"[hybrid] 混合搜索失败: {e}")

    # 降级到 FTS5
    try:
        from app.search.fts import search_papers_fts
        results = search_papers_fts(db, query, limit=top_k)
        if results:
            return results
    except Exception as e:
        print(f"[hybrid] FTS5 搜索失败: {e}")

    # 降级到 LIKE
    from app.search.fts import _fallback_like_search
    return _fallback_like_search(db, query, top_k)
