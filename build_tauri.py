"""一键构建 Tauri 便携版

步骤:
1. 构建 Python 后端 sidecar (PyInstaller)
2. 构建 Tauri 前端 + 壳 (cargo build)
3. 输出: nexus-ui/src-tauri/target/release/nexus-ui.exe + nexus-server.exe

最终发布文件在 nexus-ui/src-tauri/target/release/ 目录下。
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
TAURI_DIR = PROJECT_DIR / "nexus-ui"
RELEASE_DIR = TAURI_DIR / "src-tauri" / "target" / "release"
BINARIES_DIR = TAURI_DIR / "src-tauri" / "binaries"

# MSVC 环境（需要根据实际安装路径调整）
MSVC_BASE = "D:/VisualStudioBuild/VisualStudio/VC/Tools/MSVC/14.51.36231"
SDK_BASE = "C:/Program Files (x86)/Windows Kits/10/Lib/10.0.26100.0"


def setup_msvc_env():
    """设置 MSVC 编译环境变量"""
    env = os.environ.copy()
    env["LIB"] = f"{MSVC_BASE}/lib/x64;{SDK_BASE}/um/x64;{SDK_BASE}/ucrt/x64"
    env["INCLUDE"] = (
        f"{MSVC_BASE}/include;"
        f"C:/Program Files (x86)/Windows Kits/10/Include/10.0.26100.0/ucrt;"
        f"C:/Program Files (x86)/Windows Kits/10/Include/10.0.26100.0/um;"
        f"C:/Program Files (x86)/Windows Kits/10/Include/10.0.26100.0/shared"
    )
    cargo_home = Path.home() / ".cargo" / "bin"
    env["PATH"] = f"{cargo_home};{env['PATH']}"
    return env


def step1_build_sidecar():
    """Step 1: 构建 Python 后端 sidecar"""
    print("=" * 60)
    print("Step 1: Building Python backend sidecar...")
    print("=" * 60)

    # 运行 build_server.py
    result = subprocess.run(
        [sys.executable, "build_server.py"],
        cwd=PROJECT_DIR,
    )
    if result.returncode != 0:
        print("ERROR: Sidecar build failed")
        sys.exit(1)

    # build_server.py 输出到 release/ 目录
    sidecar = PROJECT_DIR / "release" / "nexus-server-x86_64-pc-windows-msvc.exe"
    if not sidecar.exists():
        print(f"ERROR: Sidecar not found at {sidecar}")
        sys.exit(1)

    # 同时复制到 Tauri binaries 目录（供 Tauri bundler 使用）
    BINARIES_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(sidecar, BINARIES_DIR / sidecar.name)

    print(f"Sidecar: {sidecar} ({sidecar.stat().st_size / 1024 / 1024:.1f} MB)")
    return sidecar


def step2_build_frontend():
    """Step 2: 构建前端"""
    print("\n" + "=" * 60)
    print("Step 2: Building frontend (Vite)...")
    print("=" * 60)

    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=TAURI_DIR,
        shell=True,
    )
    if result.returncode != 0:
        print("ERROR: Frontend build failed")
        sys.exit(1)

    print("Frontend built successfully")


def step3_build_tauri(env):
    """Step 3: 构建 Tauri Rust 壳"""
    print("\n" + "=" * 60)
    print("Step 3: Building Tauri shell (Rust)...")
    print("=" * 60)

    result = subprocess.run(
        ["cargo", "build", "--release"],
        cwd=TAURI_DIR / "src-tauri",
        env=env,
    )
    if result.returncode != 0:
        print("ERROR: Tauri build failed")
        sys.exit(1)

    exe = RELEASE_DIR / "nexus-ui.exe"
    if exe.exists():
        print(f"Tauri exe: {exe} ({exe.stat().st_size / 1024 / 1024:.1f} MB)")
    else:
        print(f"WARNING: {exe} not found")


def step4_package():
    """Step 4: 整理发布文件"""
    print("\n" + "=" * 60)
    print("Step 4: Packaging release...")
    print("=" * 60)

    release_dir = PROJECT_DIR / "release"

    # 复制 Tauri exe
    tauri_exe = RELEASE_DIR / "nexus-ui.exe"
    if tauri_exe.exists():
        shutil.copy2(tauri_exe, release_dir / "AI-Nexus-Assistant.exe")
        print(f"  -> {release_dir / 'AI-Nexus-Assistant.exe'}")

    # 复制 WebView2 loader（如果存在）
    for dll in RELEASE_DIR.glob("*.dll"):
        shutil.copy2(dll, release_dir / dll.name)
        print(f"  -> {release_dir / dll.name}")

    # 统计
    total = sum(f.stat().st_size for f in release_dir.iterdir() if f.is_file())
    print(f"\nRelease package: {release_dir}")
    print(f"Total size: {total / 1024 / 1024:.1f} MB")


def main():
    print("AI Nexus Assistant — Tauri Portable Build")
    print("=" * 60)

    env = setup_msvc_env()
    step1_build_sidecar()
    step2_build_frontend()
    step3_build_tauri(env)
    step4_package()

    print("\n" + "=" * 60)
    print("BUILD COMPLETE!")
    print(f"Release: {PROJECT_DIR / 'release'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
