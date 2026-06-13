"""构建 Python FastAPI 后端为独立 exe

使用专用最小 venv 构建，避免 PyInstaller 从共享 venv 拉入无关依赖。
输出: D:/ai_coding_research/release/nexus-server-x86_64-pc-windows-msvc.exe
"""

import subprocess
import sys
import shutil
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
BINARY_NAME = "nexus-server-x86_64-pc-windows-msvc"
RELEASE_DIR = PROJECT_DIR / "release"
BUILD_VENV = PROJECT_DIR / ".build-venv"

# server.py 运行时需要的最小依赖集
SERVER_DEPS = [
    "fastapi",
    "uvicorn[standard]",   # 包含 httptools/h11 等
    "sqlalchemy",
    "pydantic",
    "requests",
]


def create_build_venv():
    """创建专用最小 venv"""
    print("Creating minimal build venv...")
    if BUILD_VENV.exists():
        shutil.rmtree(BUILD_VENV)

    subprocess.run(
        [sys.executable, "-m", "venv", str(BUILD_VENV)],
        check=True,
    )

    pip = BUILD_VENV / ("Scripts/pip.exe" if sys.platform == "win32" else "bin/pip")
    subprocess.run(
        [str(pip), "install", "--no-cache-dir", *SERVER_DEPS],
        check=True,
    )
    print(f"Build venv ready: {BUILD_VENV}")


def build():
    """在专用 venv 中构建 exe"""
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)

    # 清理旧构建产物
    for d in [PROJECT_DIR / "build", PROJECT_DIR / "dist"]:
        if d.exists():
            shutil.rmtree(d)

    # 确保 build venv 存在
    if not (BUILD_VENV / "Scripts/python.exe").exists():
        create_build_venv()

    venv_python = str(BUILD_VENV / "Scripts/python.exe")

    args = [
        venv_python, "-m", "PyInstaller",
        "--name", BINARY_NAME,
        "--onefile",
        "--console",
        "--noconfirm",
        "--strip",
        "--paths", str(PROJECT_DIR),
        # 隐藏导入
        "--hidden-import", "app",
        "--hidden-import", "app.models",
        "--hidden-import", "app.models.task",
        "--hidden-import", "app.models.paper",
        "--hidden-import", "app.models.model_config",
        "--hidden-import", "app.models.search_history",
        "--hidden-import", "app.models.experiment",
        "--hidden-import", "app.models.knowledge",
        "--hidden-import", "app.models.chat",
        "--hidden-import", "app.services",
        "--hidden-import", "app.services.task_service",
        "--hidden-import", "app.services.experiment_service",
        "--hidden-import", "app.services.knowledge_service",
        "--hidden-import", "app.services.chat_service",
        "--hidden-import", "app.services.backup_service",
        "--hidden-import", "app.search",
        "--hidden-import", "app.search.engine",
        "--hidden-import", "app.search.scorer",
        "--hidden-import", "app.search.citation",
        "--hidden-import", "app.search.enricher",
        "--hidden-import", "app.search.sources",
        "--hidden-import", "app.search.sources.base",
        "--hidden-import", "app.search.sources.openalex",
        "--hidden-import", "app.search.sources.arxiv",
        "--hidden-import", "app.search.sources.semantic_scholar",
        "--hidden-import", "app.search.sources.crossref",
        "--hidden-import", "app.search.sources.pubmed",
        "--hidden-import", "app.search.sources.google_scholar",
        "--hidden-import", "app.search.sources.scopus",
        "--hidden-import", "app.ai",
        "--hidden-import", "app.ai.router",
        "--hidden-import", "app.utils",
        "--hidden-import", "app.utils.paths",
        "--hidden-import", "app.db",
        "--hidden-import", "uvicorn",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "httptools",
        "--hidden-import", "h11",
        "--hidden-import", "sqlalchemy.dialects.sqlite",
        "--hidden-import", "pydantic",
        "--hidden-import", "fastapi",
        "--hidden-import", "starlette",
        # 排除标准库中不需要的
        "--exclude-module", "tkinter",
        "--exclude-module", "unittest",
        "--exclude-module", "doctest",
        "--exclude-module", "test",
        "--exclude-module", "xmlrpc",
        "--exclude-module", "cgi",
        "--exclude-module", "cgitb",
        "--exclude-module", "dbm",
        "--exclude-module", "distutils",
        # 入口
        "server.py",
    ]

    print(f"Building: {BINARY_NAME}")
    result = subprocess.run(args, cwd=PROJECT_DIR)

    if result.returncode != 0:
        print("Build FAILED")
        sys.exit(1)

    # 复制到 release 目录
    src = PROJECT_DIR / "dist" / f"{BINARY_NAME}.exe"
    dst = RELEASE_DIR / f"{BINARY_NAME}.exe"

    if src.exists():
        shutil.copy2(src, dst)
        size_mb = dst.stat().st_size / 1024 / 1024
        print(f"\nBuilt: {dst}")
        print(f"Size: {size_mb:.1f} MB")
    else:
        print(f"ERROR: {src} not found")
        sys.exit(1)


def clean():
    """清理构建产物和临时 venv"""
    for d in [PROJECT_DIR / "build", PROJECT_DIR / "dist", BUILD_VENV]:
        if d.exists():
            shutil.rmtree(d)
            print(f"Removed: {d}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        clean()
    else:
        build()
