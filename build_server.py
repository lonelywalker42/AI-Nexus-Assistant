"""构建 Python FastAPI 后端为独立 exe

输出: D:/ai_coding_research/release/nexus-server-x86_64-pc-windows-msvc.exe
"""

import subprocess
import sys
import shutil
import os
import stat
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
BINARY_NAME = "nexus-server-x86_64-pc-windows-msvc"
RELEASE_DIR = PROJECT_DIR / "release"

# server 不需要的重量级模块 — 从 venv 中排除
EXCLUDE_MODULES = [
    # GUI
    "PyQt5", "PyQt6", "PySide6", "tkinter",
    # AI/ML (torch 4.4GB 等)
    "torch", "transformers", "onnxruntime", "onnx",
    "chromadb", "chromadb_rust_bindings",
    # 科学计算
    "scipy", "numpy", "pandas", "sklearn", "sympy",
    "numba", "llvmlite", "scs",
    # 可视化
    "matplotlib", "vtk", "vtkmodules", "pyarrow", "PIL",
    # PDF (fitz/pymupdf 需要保留 — PDF 导入功能依赖)
    "pdfminer",
    # 网络/云
    "kubernetes", "selenium",
    # 其他大型包
    "casadi", "pymavlink", "streamlit", "pydeck",
    "nuitka", "babel", "tqdm", "rich", "typer",
    # 标准库
    "unittest", "doctest", "test", "xmlrpc",
    "cgi", "cgitb", "dbm",
]


def _rmtree_retry(path: Path, retries: int = 5, delay: float = 1.0):
    """删除目录，Windows 文件锁时自动重试"""

    def _on_error(func, fpath, exc_info):
        """处理只读文件和权限问题"""
        os.chmod(fpath, stat.S_IWRITE)
        func(fpath)

    for attempt in range(retries):
        try:
            shutil.rmtree(path, onerror=_on_error)
            return
        except PermissionError:
            if attempt < retries - 1:
                print(f"  目录被占用，{delay}s 后重试 ({attempt + 1}/{retries})...")
                time.sleep(delay)
            else:
                print(f"  WARNING: 无法删除 {path}，跳过清理")
                return


def build():
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)

    # 清理旧构建产物
    for d in [PROJECT_DIR / "build", PROJECT_DIR / "dist"]:
        if d.exists():
            _rmtree_retry(d)

    args = [
        sys.executable, "-m", "PyInstaller",
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
        "--hidden-import", "app.models.review",
        "--hidden-import", "app.services",
        "--hidden-import", "app.services.task_service",
        "--hidden-import", "app.services.experiment_service",
        "--hidden-import", "app.services.knowledge_service",
        "--hidden-import", "app.services.chat_service",
        "--hidden-import", "app.services.paper_service",
        "--hidden-import", "app.services.backup_service",
        "--hidden-import", "app.services.pdf_service",
        "--hidden-import", "app.services.metrics_service",
        "--hidden-import", "app.services.citation_service",
        "--hidden-import", "app.services.export_service",
        "--hidden-import", "app.services.workspace_service",
        "--hidden-import", "app.services.writing_service",
        "--hidden-import", "app.search",
        "--hidden-import", "app.search.engine",
        "--hidden-import", "app.search.scorer",
        "--hidden-import", "app.search.citation",
        "--hidden-import", "app.search.enricher",
        "--hidden-import", "app.search.fts",
        "--hidden-import", "app.search.vectors",
        "--hidden-import", "app.search.hybrid",
        "--hidden-import", "app.search.topics",
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
        "--hidden-import", "app.ai.web_search",
        "--hidden-import", "app.ai.search_service",
        "--hidden-import", "app.ai.tools",
        "--hidden-import", "app.ai.tools.paper_tool",
        "--hidden-import", "app.ai.tools.knowledge_tool",
        "--hidden-import", "app.ai.tools.experiment_tool",
        "--hidden-import", "app.ai.tools.academic_tool",
        "--hidden-import", "app.ai.agents",
        "--hidden-import", "app.ai.agents.workflow",
        "--hidden-import", "app.ai.agents.review_agent",
        "--hidden-import", "app.ai.agents.writing_agent",
        "--hidden-import", "app.ai.agents.experiment_agent",
        "--hidden-import", "app.ai.agents.peer_review_agent",
        "--hidden-import", "app.ai.agents.debate_agent",
        "--hidden-import", "app.ai.mcp_client",
        "--hidden-import", "app.services.pdf_fetch",
        "--hidden-import", "app.services.pdf_converter",
        "--hidden-import", "app.services.arxiv_service",
        "--hidden-import", "app.services.import_service",
        "--hidden-import", "app.services.audit_service",
        "--hidden-import", "bs4",
        "--hidden-import", "lxml",
        "--hidden-import", "defusedxml",
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
        "--hidden-import", "openai",
        "--hidden-import", "anthropic",
        # 排除不需要的模块
        *[item for m in EXCLUDE_MODULES for item in ("--exclude-module", m)],
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

        # 同时复制到 Tauri binaries 目录（用于嵌入式 sidecar）
        tauri_binaries = PROJECT_DIR / "nexus-ui" / "src-tauri" / "binaries"
        if tauri_binaries.exists():
            tauri_dst = tauri_binaries / f"{BINARY_NAME}.exe"
            shutil.copy2(src, tauri_dst)
            print(f"Copied to Tauri: {tauri_dst}")
    else:
        print(f"ERROR: {src} not found")
        sys.exit(1)

    # 复制 open-webSearch 目录到 release（需要 Node.js 运行时）
    ows_src = PROJECT_DIR / "open-webSearch"
    ows_dst = RELEASE_DIR / "open-webSearch"
    if ows_src.exists():
        # 只复制必要的文件：build/ + package.json + node_modules/
        if ows_dst.exists():
            try:
                _rmtree_retry(ows_dst)
            except Exception:
                pass
        if not ows_dst.exists():
            ows_dst.mkdir(parents=True)
        for item in ["build", "node_modules", "package.json"]:
            src_item = ows_src / item
            dst_item = ows_dst / item
            if src_item.exists():
                try:
                    if src_item.is_dir():
                        if dst_item.exists():
                            shutil.rmtree(dst_item, onerror=lambda _f, _p, _e: os.chmod(_p, stat.S_IWRITE))
                        shutil.copytree(src_item, dst_item)
                    else:
                        shutil.copy2(src_item, dst_item)
                except PermissionError:
                    print(f"  SKIP: {dst_item} (被占用)")
        ows_size = sum(f.stat().st_size for f in ows_dst.rglob("*") if f.is_file())
        print(f"open-webSearch: {ows_dst} ({ows_size / 1024 / 1024:.1f} MB)")
    else:
        print("WARNING: open-webSearch/ not found, web search will fallback to DuckDuckGo")


def clean():
    """清理构建产物"""
    for d in [PROJECT_DIR / "build", PROJECT_DIR / "dist",
              PROJECT_DIR / ".build-venv"]:
        if d.exists():
            _rmtree_retry(d)
            print(f"Removed: {d}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        clean()
    else:
        build()
