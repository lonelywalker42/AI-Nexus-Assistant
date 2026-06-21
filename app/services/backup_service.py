"""备份服务 — 自动备份策略：1 月备份 + 1 周备份 + 6 日备份

SQLite WAL 模式下，完整备份需要三个文件：
  nexus.db      — 主数据库
  nexus.db-wal  — Write-Ahead Log
  nexus.db-shm  — 共享内存索引

仅复制 .db 文件可能丢失 WAL 中未 checkpoint 的数据。
备份策略：先尝试 checkpoint，再复制三个文件（确保原子性）。
"""

import shutil
import os
import sqlite3
from datetime import datetime, date
from pathlib import Path
from app.utils.paths import get_data_dir, get_backup_dir


def get_db_path() -> Path:
    """获取数据库文件路径"""
    return get_data_dir() / "nexus.db"


def _get_wal_files(db_path: Path) -> list[Path]:
    """获取 .db-wal 和 .db-shm 文件路径"""
    return [
        db_path.with_suffix(db_path.suffix + "-wal"),
        db_path.with_suffix(db_path.suffix + "-shm"),
    ]


def _checkpoint_wal(db_path: Path):
    """执行 WAL checkpoint，尽量将 WAL 数据合并到主库

    使用独立连接执行 checkpoint，不影响 SQLAlchemy 连接池。
    checkpoint 可能因活跃读者而部分完成，所以仍需复制 WAL 文件。
    """
    try:
        conn = sqlite3.connect(str(db_path), timeout=5)
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()
    except Exception as e:
        print(f"WAL checkpoint warning: {e}")


def _copy_db_files(src_db: Path, dst_db: Path):
    """使用 sqlite3.backup() API 复制数据库

    透明处理 WAL 模式，比手动复制三个文件更安全。
    Python 3.7+ 内置支持。
    """
    # 删除目标文件（backup API 要求目标不存在或为空）
    for suffix in ["", "-wal", "-shm"]:
        f = dst_db.with_suffix(dst_db.suffix + suffix) if suffix else dst_db
        f.unlink(missing_ok=True)

    try:
        src = sqlite3.connect(str(src_db), timeout=10)
        dst = sqlite3.connect(str(dst_db), timeout=10)
        src.backup(dst)
        dst.close()
        src.close()
    except Exception:
        # 回退到传统方式
        _checkpoint_wal(src_db)
        shutil.copy2(src_db, dst_db)
        for suffix in ["-wal", "-shm"]:
            src_file = src_db.with_suffix(src_db.suffix + suffix)
            dst_file = dst_db.with_suffix(dst_db.suffix + suffix)
            if src_file.exists() and src_file.stat().st_size > 0:
                shutil.copy2(src_file, dst_file)


def _remove_db_files(db_path: Path):
    """删除 .db 及 .db-wal、.db-shm"""
    for suffix in ["", "-wal", "-shm"]:
        f = db_path.with_suffix(db_path.suffix + suffix) if suffix else db_path
        f.unlink(missing_ok=True)


def create_backup(label: str = "") -> Path | None:
    """创建备份 — 复制 .db + .db-wal + .db-shm 三个文件

    备份目录结构：
      data/backups/nexus_daily_20260618_120000.db
      data/backups/nexus_daily_20260618_120000.db-wal  (可能不存在)
      data/backups/nexus_daily_20260618_120000.db-shm  (可能不存在)
    """
    db_path = get_db_path()
    if not db_path.exists():
        return None

    backup_dir = get_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"nexus_{label}_{timestamp}.db" if label else f"nexus_{timestamp}.db"
    backup_path = backup_dir / name

    try:
        _copy_db_files(db_path, backup_path)
        return backup_path
    except Exception as e:
        print(f"Backup failed: {e}")
        return None


def auto_backup() -> dict:
    """自动备份 — 保留 1 月 + 1 周 + 6 日"""
    backup_dir = get_backup_dir()
    today = date.today()

    backups = sorted(backup_dir.glob("nexus_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)

    result = {"created": None, "cleaned": 0}

    backup_path = create_backup("daily")
    if backup_path:
        result["created"] = str(backup_path)

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

    for old in daily_backups[6:]:
        _remove_backup(old)
        result["cleaned"] += 1

    for old in weekly_backups[1:]:
        _remove_backup(old)
        result["cleaned"] += 1

    for old in monthly_backups[1:]:
        _remove_backup(old)
        result["cleaned"] += 1

    if today.weekday() == 0:
        create_backup("weekly")

    if today.day == 1:
        create_backup("monthly")

    return result


def _remove_backup(db_path: Path):
    """删除备份文件及其 WAL/SHM"""
    for suffix in ["", "-wal", "-shm"]:
        f = db_path.with_suffix(db_path.suffix + suffix) if suffix else db_path
        f.unlink(missing_ok=True)


def restore_backup(backup_path: str) -> bool:
    """从备份恢复 — 恢复 .db + .db-wal + .db-shm

    步骤：
    1. 备份当前数据库（以防恢复失败）
    2. 删除当前的 .db、.db-wal、.db-shm
    3. 复制备份的 .db、.db-wal、.db-shm
    """
    src = Path(backup_path)
    if not src.exists():
        return False

    dst = get_db_path()
    try:
        # 先备份当前数据库
        create_backup("before_restore")

        # 删除当前的三个文件
        _remove_db_files(dst)

        # 复制备份的三个文件
        _copy_db_files(src, dst)

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
        # 计算总大小（含 WAL/SHM）
        total_size = stat.st_size
        for suffix in ["-wal", "-shm"]:
            sibling = bp.with_suffix(bp.suffix + suffix)
            if sibling.exists():
                total_size += sibling.stat().st_size
        backups.append({
            "name": bp.name,
            "path": str(bp),
            "size": total_size,
            "time": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })
    return backups
