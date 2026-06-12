"""构建 Python FastAPI 后端为独立 exe (Tauri sidecar)

输出: nexus-ui/src-tauri/binaries/nexus-server-x86_64-pc-windows-msvc.exe
Tauri 会在启动时自动执行此 sidecar。
"""

import subprocess
import sys
import shutil
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
BINARY_NAME = "nexus-server-x86_64-pc-windows-msvc"
OUTPUT_DIR = PROJECT_DIR / "nexus-ui" / "src-tauri" / "binaries"


def build():
    import os
    os_sep = ";" if sys.platform == "win32" else ":"

    # 清理
    for d in [PROJECT_DIR / "build", PROJECT_DIR / "dist"]:
        if d.exists():
            shutil.rmtree(d)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    args = [
        sys.executable, "-m", "PyInstaller",
        "--name", BINARY_NAME,
        "--onefile",
        "--console",
        "--noconfirm",
        "--hidden-import", "app.models",
        "--hidden-import", "app.models.task",
        "--hidden-import", "app.models.paper",
        "--hidden-import", "app.models.model_config",
        "--hidden-import", "app.models.search_history",
        "--hidden-import", "app.models.experiment",
        "--hidden-import", "app.models.knowledge",
        "--hidden-import", "app.models.chat",
        "--hidden-import", "app.services.task_service",
        "--hidden-import", "app.services.experiment_service",
        "--hidden-import", "app.services.knowledge_service",
        "--hidden-import", "app.services.chat_service",
        "--hidden-import", "app.services.backup_service",
        "--hidden-import", "app.search.engine",
        "--hidden-import", "app.search.sources.openalex",
        "--hidden-import", "app.search.sources.arxiv",
        "--hidden-import", "app.search.sources.semantic_scholar",
        "--hidden-import", "app.search.sources.crossref",
        "--hidden-import", "app.search.sources.pubmed",
        "--hidden-import", "app.search.sources.google_scholar",
        "--hidden-import", "app.search.sources.scopus",
        "--hidden-import", "app.ai.router",
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
        "--hidden-import", "sqlalchemy.dialects.sqlite",
        "--exclude-module", "PyQt5",
        "--exclude-module", "PyQt6",
        f"--add-data=config{os_sep}config",
        "server.py",
    ]

    print(f"Building sidecar: {BINARY_NAME}")

    result = subprocess.run(args, cwd=PROJECT_DIR)

    if result.returncode != 0:
        print("Build FAILED")
        sys.exit(1)

    # 复制到 Tauri binaries 目录
    src = PROJECT_DIR / "dist" / BINARY_NAME
    if sys.platform == "win32":
        src = src.with_suffix(".exe")

    dst = OUTPUT_DIR / src.name

    if src.exists():
        shutil.copy2(src, dst)
        print(f"\nSidecar built: {dst}")
        print(f"Size: {dst.stat().st_size / 1024 / 1024:.1f} MB")
    else:
        print(f"ERROR: {src} not found")
        sys.exit(1)


if __name__ == "__main__":
    build()
