"""路径工具 — 处理 PyInstaller 打包和开发环境的路径差异"""

import sys
import os
from pathlib import Path


def get_app_dir() -> Path:
    """获取应用根目录（exe 所在目录或项目根目录）"""
    if getattr(sys, "frozen", False):
        # PyInstaller 打包后
        return Path(sys.executable).parent
    else:
        return Path(__file__).resolve().parent.parent.parent


def get_data_dir() -> Path:
    """获取数据目录，不存在则创建"""
    data_dir = get_app_dir() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_config_dir() -> Path:
    """获取配置目录"""
    config_dir = get_app_dir() / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_backup_dir() -> Path:
    """获取备份目录"""
    backup_dir = get_data_dir() / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def get_export_dir() -> Path:
    """获取导出目录"""
    export_dir = get_data_dir() / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    return export_dir
