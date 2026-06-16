"""open-webSearch 守护进程管理

启动 / 停止 open-webSearch Node.js 守护进程（默认端口 3210）。
server.py 启动时调用 start_search_service()，退出时自动清理。
"""

import atexit
import logging
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# 全局子进程引用
_proc: subprocess.Popen | None = None

# 默认端口，与 open-webSearch 一致
DEFAULT_PORT = 3210


def _find_node() -> str | None:
    """查找 node 可执行文件"""
    return shutil.which("node")


def _find_open_websearch_dir() -> Path | None:
    """查找 open-webSearch 目录（开发模式 vs 冻结模式）

    冻结模式下按优先级查找:
    1. _MEIPASS/open-webSearch/  (PyInstaller --add-data 嵌入)
    2. exe同级/open-webSearch/   (外部部署，exe 旁放置)
    3. cwd/open-webSearch/       (从 release 目录启动)
    """
    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", ""))
        exe_dir = Path(sys.executable).parent

        for base in [meipass, exe_dir, Path.cwd()]:
            if not base:
                continue
            candidate = base / "open-webSearch"
            if candidate.exists() and (candidate / "build" / "index.js").exists():
                return candidate
    else:
        # 开发模式：项目根目录下的 open-webSearch 子模块
        candidate = Path(__file__).resolve().parent.parent.parent / "open-webSearch"
        if candidate.exists():
            return candidate
    return None


def _is_port_open(port: int, host: str = "127.0.0.1", timeout: float = 1.0) -> bool:
    """检查端口是否已被占用"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError):
        return False


def _wait_for_ready(port: int, timeout: float = 10.0) -> bool:
    """等待守护进程就绪"""
    import httpx

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            resp = httpx.get(f"http://127.0.0.1:{port}/health", timeout=2.0)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "ok":
                    return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def start_search_service(port: int = DEFAULT_PORT) -> bool:
    """启动 open-webSearch 守护进程

    Returns:
        True if the service is running (started by us or already running).
    """
    global _proc

    # 如果已经在运行，直接返回
    if _is_port_open(port):
        logger.info(f"搜索服务已在端口 {port} 运行")
        return True

    node = _find_node()
    if not node:
        logger.warning("未找到 Node.js，搜索服务无法启动，将回退到 DuckDuckGo 直接搜索")
        return False

    ows_dir = _find_open_websearch_dir()
    if not ows_dir:
        logger.warning("未找到 open-webSearch 目录，搜索服务无法启动")
        return False

    entry = ows_dir / "build" / "index.js"
    if not entry.exists():
        logger.warning(f"open-webSearch 未构建（{entry} 不存在），请先运行 npm run build")
        return False

    env = os.environ.copy()
    # 强制 daemon 模式只启用 HTTP（不需要 stdio MCP）
    env["MODE"] = "http"

    try:
        # Windows: 不弹出控制台窗口
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW

        _proc = subprocess.Popen(
            [node, str(entry), "serve", "--host", "127.0.0.1", "--port", str(port)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(ows_dir),
            **kwargs,
        )
        logger.info(f"正在启动搜索服务 (PID={_proc.pid})，端口 {port}...")

        if _wait_for_ready(port, timeout=15.0):
            logger.info(f"搜索服务已就绪，端口 {port}")
            # 注册退出清理
            atexit.register(stop_search_service)
            return True
        else:
            logger.warning("搜索服务启动超时，将回退到 DuckDuckGo 直接搜索")
            stop_search_service()
            return False

    except Exception as e:
        logger.warning(f"启动搜索服务失败: {e}，将回退到 DuckDuckGo 直接搜索")
        return False


def stop_search_service():
    """停止守护进程"""
    global _proc
    if _proc is None:
        return

    try:
        if sys.platform == "win32":
            _proc.terminate()
        else:
            _proc.send_signal(signal.SIGTERM)

        try:
            _proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _proc.kill()
            _proc.wait(timeout=3)

        logger.info("搜索服务已停止")
    except Exception as e:
        logger.warning(f"停止搜索服务时出错: {e}")
    finally:
        _proc = None


def is_search_service_running(port: int = DEFAULT_PORT) -> bool:
    """检查搜索服务是否正在运行"""
    return _is_port_open(port)
