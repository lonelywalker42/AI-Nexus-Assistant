"""任务服务层 — 整合 ai-todo + ai-research-manager 的任务管理逻辑"""

import json
from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.task import Task, WeeklyPlan


USER_ID = "default"


def get_todos_by_date(db: Session, date_str: str) -> list[Task]:
    """按日期获取待办列表"""
    return (
        db.query(Task)
        .filter(Task.date == date_str, Task.plan_id.is_(None))
        .order_by(Task.completed.asc(), Task.sort_order.asc(), Task.created_at.desc())
        .all()
    )


def get_all_todos_by_date(db: Session, date_str: str) -> list[Task]:
    """按日期获取所有任务（包括周计划中的）"""
    return (
        db.query(Task)
        .filter(Task.date == date_str)
        .order_by(Task.completed.asc(), Task.sort_order.asc(), Task.created_at.desc())
        .all()
    )


def add_standalone_task(db: Session, date_str: str, content: str,
                        priority: str = "normal", category: str = "general") -> Task:
    """添加独立待办（不关联周计划）"""
    task = Task(
        date=date_str,
        content=content,
        priority=priority,
        category=category,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def toggle_complete(db: Session, task_id: str) -> Optional[Task]:
    """切换完成状态"""
    task = db.get(Task, task_id)
    if not task:
        return None
    task.completed = not task.completed
    task.completed_at = datetime.now() if task.completed else None
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task_id: str) -> bool:
    """删除任务"""
    task = db.get(Task, task_id)
    if not task:
        return False
    db.delete(task)
    db.commit()
    return True


def update_task(db: Session, task_id: str, **kwargs) -> Optional[Task]:
    """更新任务字段"""
    task = db.get(Task, task_id)
    if not task:
        return None
    for key, value in kwargs.items():
        if hasattr(task, key):
            setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return task


def get_dates_with_todos(db: Session, start: str, end: str) -> dict[str, str]:
    """获取日期范围内有待办的日期，返回 {date_str: "pending"|"completed"}"""
    pending_dates = (
        db.query(Task.date)
        .filter(Task.date.between(start, end), Task.completed == False)
        .distinct()
        .all()
    )
    completed_dates = (
        db.query(Task.date)
        .filter(Task.date.between(start, end), Task.completed == True)
        .distinct()
        .all()
    )

    pending_set = {r[0] for r in pending_dates}
    completed_set = {r[0] for r in completed_dates}

    result = {}
    for d in pending_set | completed_set:
        result[d] = "pending" if d in pending_set else "completed"

    return result


def get_month_stats(db: Session, year: int, month: int) -> tuple[int, int]:
    """获取月度统计：(总任务数, 已完成数)"""
    start = f"{year:04d}-{month:02d}-01"
    if month == 12:
        end = f"{year + 1:04d}-01-01"
    else:
        end = f"{year:04d}-{month + 1:02d}-01"

    total = db.query(func.count(Task.id)).filter(
        Task.date >= start, Task.date < end
    ).scalar() or 0

    done = db.query(func.count(Task.id)).filter(
        Task.date >= start, Task.date < end, Task.completed == True
    ).scalar() or 0

    return total, done


# ── 周计划相关 ────────────────────────────────────────────────

def get_current_plan(db: Session) -> Optional[WeeklyPlan]:
    """获取当前周的周计划"""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    return (
        db.query(WeeklyPlan)
        .filter(WeeklyPlan.user_id == USER_ID, WeeklyPlan.week_start == monday)
        .first()
    )


def get_all_plans(db: Session) -> list[WeeklyPlan]:
    """获取所有周计划"""
    return (
        db.query(WeeklyPlan)
        .filter(WeeklyPlan.user_id == USER_ID)
        .order_by(WeeklyPlan.week_start.desc())
        .all()
    )


def create_plan(db: Session, week_start: date, tasks_data: list[dict] | None = None) -> WeeklyPlan:
    """创建周计划"""
    plan = WeeklyPlan(
        user_id=USER_ID,
        week_start=week_start,
        week_end=week_start + timedelta(days=6),
    )
    db.add(plan)
    db.flush()

    if tasks_data:
        for i, td in enumerate(tasks_data):
            task = Task(
                plan_id=plan.id,
                date=td.get("date", week_start.isoformat()),
                content=td.get("content", ""),
                priority=td.get("priority", "normal"),
                category=td.get("category", "general"),
                sort_order=i,
            )
            db.add(task)

    db.commit()
    db.refresh(plan)
    return plan


def copy_plan_to_next_week(db: Session, plan_id: str) -> Optional[WeeklyPlan]:
    """复制周计划到下一周"""
    plan = db.get(WeeklyPlan, plan_id)
    if not plan:
        return None

    new_start = plan.week_start + timedelta(days=7)
    new_plan = WeeklyPlan(
        user_id=USER_ID,
        week_start=new_start,
        week_end=new_start + timedelta(days=6),
    )
    db.add(new_plan)
    db.flush()

    # 复制任务
    for task in plan.tasks:
        new_task = Task(
            plan_id=new_plan.id,
            date=(date.fromisoformat(task.date) + timedelta(days=7)).isoformat() if task.date else new_start.isoformat(),
            content=task.content,
            priority=task.priority,
            category=task.category,
            sort_order=task.sort_order,
        )
        db.add(new_task)

    db.commit()
    db.refresh(new_plan)
    return new_plan


def get_task_stats(db: Session, date_str: str) -> dict:
    """获取指定日期的任务统计"""
    tasks = get_all_todos_by_date(db, date_str)
    total = len(tasks)
    done = sum(1 for t in tasks if t.completed)
    return {"total": total, "done": done, "pending": total - done}
