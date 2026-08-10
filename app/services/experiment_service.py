"""试验管理服务层 — 来自 ai-research-manager，扩展版本化结果 + 代码片段"""

import json
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func
from app.models.experiment import Experiment, ExperimentResult


USER_ID = "default"


def get_experiments(db: Session, search: str = "", status: str = "") -> list[Experiment]:
    """获取试验列表"""
    q = db.query(Experiment).options(selectinload(Experiment.results)).filter(
        Experiment.user_id == USER_ID
    )
    if search:
        q = q.filter(Experiment.title.ilike(f"%{search}%"))
    if status:
        q = q.filter(Experiment.status == status)
    return q.order_by(Experiment.updated_at.desc()).all()


def get_experiment(db: Session, exp_id: str) -> Optional[Experiment]:
    """获取单个试验（含结果）"""
    return db.query(Experiment).filter(
        Experiment.id == exp_id, Experiment.user_id == USER_ID
    ).first()


def create_experiment(db: Session, title: str, background: str = "",
                      objective: str = "", setup: str = "") -> Experiment:
    """创建试验"""
    exp = Experiment(
        user_id=USER_ID,
        title=title,
        background=background,
        objective=objective,
        setup=setup,
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return exp


def update_experiment(db: Session, exp_id: str, **kwargs) -> Optional[Experiment]:
    """更新试验"""
    exp = get_experiment(db, exp_id)
    if not exp:
        return None
    for key, value in kwargs.items():
        if hasattr(exp, key):
            setattr(exp, key, value)
    exp.updated_at = datetime.now()
    db.commit()
    db.refresh(exp)
    return exp


def delete_experiment(db: Session, exp_id: str) -> bool:
    """删除试验"""
    exp = get_experiment(db, exp_id)
    if not exp:
        return False
    db.delete(exp)
    db.commit()
    return True


def add_result(db: Session, exp_id: str, description: str = "",
               parameters: dict | None = None, code_snippets: list | None = None,
               result_data: str = "", conclusion: str = "") -> Optional[ExperimentResult]:
    """添加试验结果（自动递增版本号）"""
    exp = get_experiment(db, exp_id)
    if not exp:
        return None

    # 计算下一个版本号
    max_version = db.query(func.max(ExperimentResult.version)).filter(
        ExperimentResult.experiment_id == exp_id
    ).scalar() or 0

    result = ExperimentResult(
        experiment_id=exp_id,
        version=max_version + 1,
        description=description,
        parameters=json.dumps(parameters or {}, ensure_ascii=False),
        code_snippets=json.dumps(code_snippets or [], ensure_ascii=False),
        result_data=result_data,
        conclusion=conclusion,
    )
    db.add(result)
    exp.updated_at = datetime.now()
    db.commit()
    db.refresh(result)
    return result


def update_result(db: Session, result_id: str, **kwargs) -> Optional[ExperimentResult]:
    """更新试验结果"""
    result = db.query(ExperimentResult).filter(ExperimentResult.id == result_id).first()
    if not result:
        return None
    for key, value in kwargs.items():
        if key == "parameters" and isinstance(value, dict):
            value = json.dumps(value, ensure_ascii=False)
        elif key == "code_snippets" and isinstance(value, list):
            value = json.dumps(value, ensure_ascii=False)
        if hasattr(result, key):
            setattr(result, key, value)
    db.commit()
    db.refresh(result)
    return result


def delete_result(db: Session, result_id: str) -> bool:
    """删除试验结果"""
    result = db.query(ExperimentResult).filter(ExperimentResult.id == result_id).first()
    if not result:
        return False
    db.delete(result)
    db.commit()
    return True


def get_results(db: Session, exp_id: str) -> list[ExperimentResult]:
    """获取试验的所有结果版本"""
    return (
        db.query(ExperimentResult)
        .filter(ExperimentResult.experiment_id == exp_id)
        .order_by(ExperimentResult.version.desc())
        .all()
    )


def get_experiment_stats(db: Session) -> dict:
    """获取试验统计"""
    stats = {}
    for status in ["planning", "running", "completed", "suspended"]:
        count = db.query(func.count(Experiment.id)).filter(
            Experiment.user_id == USER_ID, Experiment.status == status
        ).scalar() or 0
        stats[status] = count
    stats["total"] = sum(stats.values())
    return stats


def export_experiment_markdown(db: Session, exp_id: str) -> str:
    """导出试验报告为 Markdown"""
    exp = get_experiment(db, exp_id)
    if not exp:
        return ""

    lines = [f"# {exp.title}\n"]
    lines.append(f"**状态**: {exp.status}\n")
    lines.append(f"**创建时间**: {exp.created_at.strftime('%Y-%m-%d %H:%M')}\n")

    if exp.background:
        lines.append(f"\n## 背景\n\n{exp.background}\n")
    if exp.objective:
        lines.append(f"\n## 目标\n\n{exp.objective}\n")
    if exp.setup:
        lines.append(f"\n## 实验设置\n\n{exp.setup}\n")

    results = get_results(db, exp_id)
    if results:
        lines.append("\n## 试验结果\n")
        for r in results:
            lines.append(f"\n### 版本 {r.version}\n")
            lines.append(f"**描述**: {r.description}\n")

            params = json.loads(r.parameters) if r.parameters else {}
            if params:
                lines.append("\n**参数配置**:\n")
                for k, v in params.items():
                    lines.append(f"- `{k}`: {v}")

            snippets = json.loads(r.code_snippets) if r.code_snippets else []
            if snippets:
                for s in snippets:
                    fname = s.get("file", "code")
                    lines.append(f"\n**代码片段** (`{fname}`):\n")
                    lines.append(f"```\n{s.get('code', '')}\n```\n")
                    if s.get("diff"):
                        lines.append(f"**修改**:\n```\n{s['diff']}\n```\n")

            if r.result_data:
                lines.append(f"\n**结果数据**:\n\n{r.result_data}\n")
            if r.conclusion:
                lines.append(f"\n**结论**: {r.conclusion}\n")

    return "\n".join(lines)
