"""PyInstaller 构建脚本"""

import os
import sys
import shutil
from pathlib import Path


def build():
    """构建 Windows EXE"""
    project_dir = Path(__file__).parent
    dist_dir = project_dir / "dist"
    build_dir = project_dir / "build"

    # 清理旧构建
    for d in [dist_dir, build_dir]:
        if d.exists():
            shutil.rmtree(d)

    # PyInstaller 参数
    args = [
        "pyinstaller",
        "--name=AI-Nexus-Assistant",
        "--windowed",           # 无控制台窗口
        "--onedir",             # 单目录模式（启动更快）
        "--noconfirm",          # 不确认覆盖
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        # 添加数据文件
        f"--add-data=config;config",
        # 隐藏导入
        "--hidden-import=sqlalchemy.dialects.sqlite",
        "--hidden-import=app.models",
        "--hidden-import=app.models.task",
        "--hidden-import=app.models.paper",
        "--hidden-import=app.models.model_config",
        "--hidden-import=app.models.search_history",
        "--hidden-import=app.models.experiment",
        "--hidden-import=app.models.knowledge",
        "--hidden-import=app.models.chat",
        # 入口
        "main.py",
    ]

    # 如果有图标
    icon_path = project_dir / "config" / "icon.ico"
    if icon_path.exists():
        args.insert(-1, f"--icon={icon_path}")

    os.chdir(project_dir)
    print(f"Building with: {' '.join(args)}")
    exit_code = os.system(" ".join(args))

    if exit_code == 0:
        print(f"\nBuild successful! Output: {dist_dir / 'AI-Nexus-Assistant'}")
    else:
        print(f"\nBuild failed with exit code {exit_code}")

    return exit_code


if __name__ == "__main__":
    sys.exit(build())
