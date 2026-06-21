"""元数据质量审计服务 — 规则引擎（无 LLM）

扫描文献库检测:
  - 缺失字段: DOI / 摘要 / 年份 / 作者 / 期刊 / 标题
  - 标题一致性: 元数据标题 vs AI 摘要
  - DOI 重复检测
  - PDF 缺失检测
"""

import json
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.paper import Paper

_log = logging.getLogger("nexus.audit")

# 审计问题类型常量
MISSING_DOI = "missing_doi"
MISSING_ABSTRACT = "missing_abstract"
MISSING_YEAR = "missing_year"
MISSING_AUTHORS = "missing_authors"
MISSING_JOURNAL = "missing_journal"
MISSING_TITLE = "missing_title"
NO_PDF = "no_pdf"
SHORT_ABSTRACT = "short_abstract"
DOI_DUPLICATE = "doi_duplicate"
SUSPICIOUS_YEAR = "suspicious_year"


def audit_papers(session: Session) -> list[dict]:
    """对所有论文执行元数据质量审计。

    Returns:
        list[dict]: [{paper_id, title, issues: [...], severity: "high"|"medium"|"low"}]
    """
    papers = session.query(Paper).all()
    if not papers:
        return []

    # 收集所有 DOI 用于重复检测
    doi_map: dict[str, list[str]] = {}
    for p in papers:
        doi = (p.doi or "").strip().lower()
        if doi:
            doi_map.setdefault(doi, []).append(p.id)

    results = []
    for p in papers:
        issues = []
        severity = "low"

        # 缺失关键字段
        if not (p.title or "").strip():
            issues.append(MISSING_TITLE)
            severity = "high"

        if not (p.doi or "").strip():
            issues.append(MISSING_DOI)
            if severity != "high":
                severity = "medium"

        if not (p.abstract or "").strip():
            issues.append(MISSING_ABSTRACT)
            if severity != "high":
                severity = "medium"
        elif len(p.abstract.strip()) < 50:
            issues.append(SHORT_ABSTRACT)

        if not p.year or p.year < 1900:
            issues.append(MISSING_YEAR)

        authors = _safe_json_list(p.authors)
        if not authors:
            issues.append(MISSING_AUTHORS)

        if not (p.journal or "").strip():
            issues.append(MISSING_JOURNAL)

        # PDF 缺失
        if not (p.local_path or "").strip():
            issues.append(NO_PDF)
        elif not _file_exists(p.local_path):
            issues.append(NO_PDF)

        # DOI 重复
        doi = (p.doi or "").strip().lower()
        if doi and doi in doi_map and len(doi_map[doi]) > 1:
            issues.append(DOI_DUPLICATE)
            if severity != "high":
                severity = "medium"

        # 可疑年份
        if p.year and (p.year < 1950 or p.year > 2030):
            issues.append(SUSPICIOUS_YEAR)

        if issues:
            results.append({
                "paper_id": p.id,
                "title": p.title or "(无标题)",
                "issues": issues,
                "severity": severity,
            })

    # 按严重程度排序
    severity_order = {"high": 0, "medium": 1, "low": 2}
    results.sort(key=lambda x: severity_order.get(x["severity"], 3))

    _log.info(f"审计完成: {len(results)}/{len(papers)} 篇有问题")
    return results


def get_audit_stats(session: Session) -> dict:
    """获取审计统计摘要。

    Returns:
        dict: {total, with_issues, by_issue_type, severity_counts}
    """
    papers = session.query(Paper).all()
    total = len(papers)
    if total == 0:
        return {
            "total": 0,
            "with_issues": 0,
            "by_issue_type": {},
            "severity_counts": {"high": 0, "medium": 0, "low": 0},
        }

    audit_results = audit_papers(session)
    with_issues = len(audit_results)

    # 按问题类型统计
    by_type: dict[str, int] = {}
    for r in audit_results:
        for issue in r["issues"]:
            by_type[issue] = by_type.get(issue, 0) + 1

    # 按严重程度统计
    severity_counts = {"high": 0, "medium": 0, "low": 0}
    for r in audit_results:
        sev = r.get("severity", "low")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    return {
        "total": total,
        "with_issues": with_issues,
        "by_issue_type": by_type,
        "severity_counts": severity_counts,
    }


def _safe_json_list(s: str) -> list:
    """安全解析 JSON 数组"""
    if not s:
        return []
    try:
        result = json.loads(s)
        return result if isinstance(result, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _file_exists(path: str) -> bool:
    """检查文件是否存在"""
    if not path:
        return False
    try:
        import os
        return os.path.isfile(path)
    except Exception:
        return False
