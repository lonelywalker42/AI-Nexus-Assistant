"""备份服务 — 自动备份策略：1 月备份 + 1 周备份 + 6 日备份"""

import shutil
import os
from datetime import datetime, date
from pathlib import Path
from app.utils.paths import get_data_dir, get_backup_dir


def get_db_path() -> Path:
    """获取数据库文件路径"""
    return get_data_dir() / "nexus.db"


def create_backup(label: str = "") -> Path | None:
    """创建备份"""
    db_path = get_db_path()
    if not db_path.exists():
        return None

    backup_dir = get_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"nexus_{label}_{timestamp}.db" if label else f"nexus_{timestamp}.db"
    backup_path = backup_dir / name

    try:
        shutil.copy2(db_path, backup_path)
        return backup_path
    except Exception as e:
        print(f"Backup failed: {e}")
        return None


def auto_backup() -> dict:
    """自动备份 — 保留 1 月 + 1 周 + 6 日"""
    backup_dir = get_backup_dir()
    today = date.today()

    # 列出现有备份
    backups = sorted(backup_dir.glob("nexus_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)

    result = {"created": None, "cleaned": 0}

    # 创建今日备份
    backup_path = create_backup("daily")
    if backup_path:
        result["created"] = str(backup_path)

    # 清理策略
    daily_backups = []
    weekly_backups = []
    monthly_backups = []

    for bp in backups:
        name = bp.name
        if "daily" in name:
            daily_backups.append(bp)
        elif "weekly" in name:
            weekly_backups.append(bp)
        elif "monthly" in name:
            monthly_backups.append(bp)

    # 保留最近 6 个日备份
    for old in daily_backups[6:]:
        old.unlink(missing_ok=True)
        result["cleaned"] += 1

    # 保留最近 1 个周备份
    for old in weekly_backups[1:]:
        old.unlink(missing_ok=True)
        result["cleaned"] += 1

    # 保留最近 1 个月备份
    for old in monthly_backups[1:]:
        old.unlink(missing_ok=True)
        result["cleaned"] += 1

    # 每周创建周备份（周一）
    if today.weekday() == 0:
        create_backup("weekly")

    # 每月创建月备份（1号）
    if today.day == 1:
        create_backup("monthly")

    return result


def restore_backup(backup_path: str) -> bool:
    """从备份恢复"""
    src = Path(backup_path)
    if not src.exists():
        return False

    dst = get_db_path()
    try:
        # 先备份当前数据库
        create_backup("before_restore")
        shutil.copy2(src, dst)
        return True
    except Exception as e:
        print(f"Restore failed: {e}")
        return False


def list_backups() -> list[dict]:
    """列出所有备份"""
    backup_dir = get_backup_dir()
    backups = []
    for bp in sorted(backup_dir.glob("nexus_*.db"), key=lambda p: p.stat().st_mtime, reverse=True):
        stat = bp.stat()
        backups.append({
            "name": bp.name,
            "path": str(bp),
            "size": stat.st_size,
            "time": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })
    return backups
