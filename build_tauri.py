"""一键构建 Tauri 便携版

步骤:
1. 构建 Python 后端 sidecar (PyInstaller)
2. 构建 Tauri 应用 (npx tauri build — 自动构建前端+嵌入+打包)
3. 整理到 release/ 目录

最终发布文件在 release/ 目录下。
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

    result = subprocess.run(
        [sys.executable, "build_server.py"],
        cwd=PROJECT_DIR,
    )
    if result.returncode != 0:
        print("ERROR: Sidecar build failed")
        sys.exit(1)

    sidecar = PROJECT_DIR / "release" / "nexus-server-x86_64-pc-windows-msvc.exe"
    if not sidecar.exists():
        print(f"ERROR: Sidecar not found at {sidecar}")
        sys.exit(1)

    # 复制到 Tauri binaries 目录（供 Rust include_bytes 嵌入）
    BINARIES_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(sidecar, BINARIES_DIR / sidecar.name)

    # 删除 release 中的独立 sidecar（已嵌入主 exe）
    sidecar.unlink()

    print(f"Sidecar: {sidecar.name} ({BINARIES_DIR.joinpath(sidecar.name).stat().st_size / 1024 / 1024:.1f} MB) -> embedded in Tauri exe")
    return sidecar


def step2_build_tauri(env):
    """Step 2: 构建 Tauri 应用（前端+壳+嵌入前端资源）"""
    print("\n" + "=" * 60)
    print("Step 2: Building Tauri app (frontend + shell)...")
    print("=" * 60)

    # npx tauri build 会自动执行:
    #   1. beforeBuildCommand (npm run build → Vite 构建前端)
    #   2. cargo build --release (编译 Rust 壳)
    #   3. 嵌入 dist/ 到 exe 中
    #   4. 生成 MSI/NSIS 安装包
    result = subprocess.run(
        ["npx", "tauri", "build"],
        cwd=TAURI_DIR,
        env=env,
        shell=True,
    )
    if result.returncode != 0:
        print("ERROR: Tauri build failed")
        sys.exit(1)

    exe = RELEASE_DIR / "nexus-ui.exe"
    if exe.exists():
        print(f"Tauri exe: {exe} ({exe.stat().st_size / 1024 / 1024:.1f} MB)")
    else:
        print(f"WARNING: {exe} not found")


def step3_package():
    """Step 3: 整理发布文件"""
    print("\n" + "=" * 60)
    print("Step 3: Packaging release...")
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
    step2_build_tauri(env)
    step3_package()

    print("\n" + "=" * 60)
    print("BUILD COMPLETE!")
    print(f"Release: {PROJECT_DIR / 'release'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
