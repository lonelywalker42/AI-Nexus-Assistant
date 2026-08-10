"""一键构建 Tauri 便携版

步骤:
1. 构建 Python 后端 sidecar (PyInstaller)
2. 构建 Tauri 应用 (本地 Tauri CLI — 自动构建前端+嵌入+打包)
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
CARGO_TARGET_DIR = Path(
    os.environ.get("CARGO_TARGET_DIR", TAURI_DIR / "src-tauri" / "target")
).resolve()
RELEASE_DIR = CARGO_TARGET_DIR / "release"
BINARIES_DIR = TAURI_DIR / "src-tauri" / "binaries"
PACKAGE_OUTPUT_DIR = PROJECT_DIR / "release"


def get_package_mode() -> str:
    """Return and validate the requested Tauri packaging mode."""
    package_mode = os.environ.get("NEXUS_TAURI_PACKAGE_MODE", "portable")
    if package_mode not in {"portable", "installers"}:
        raise RuntimeError(
            "NEXUS_TAURI_PACKAGE_MODE must be 'portable' or 'installers', "
            f"got {package_mode!r}"
        )
    return package_mode


def _find_vswhere() -> Path | None:
    """查找 Visual Studio Installer 自带的 vswhere.exe。"""
    candidates = [
        Path(os.environ.get("PROGRAMFILES(X86)", ""))
        / "Microsoft Visual Studio" / "Installer" / "vswhere.exe",
        Path(os.environ.get("PROGRAMFILES", ""))
        / "Microsoft Visual Studio" / "Installer" / "vswhere.exe",
    ]
    return next((path for path in candidates if path.is_file()), None)


def _find_vs_installation() -> Path | None:
    """查找带 C++ x64 工具链的 Visual Studio 2022 安装。"""
    vswhere = _find_vswhere()
    if not vswhere:
        return None
    result = subprocess.run(
        [
            str(vswhere), "-latest", "-products", "*",
            "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
            "-property", "installationPath",
        ],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    installation = result.stdout.strip()
    return Path(installation) if installation else None


def _find_msvc() -> Path | None:
    """自动查找 MSVC 工具链目录（最新版本）"""
    # 1. 通过 vswhere.exe 查找（VS Installer 标准工具）
    vswhere = _find_vswhere()
    if vswhere:
        try:
            result = subprocess.run(
                [str(vswhere), "-latest", "-products", "*", "-property", "installationPath"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                vc_tools = Path(result.stdout.strip()) / "VC" / "Tools" / "MSVC"
                versions = sorted(vc_tools.iterdir(), reverse=True) if vc_tools.exists() else []
                if versions:
                    return versions[0]
        except Exception:
            pass

    # 2. 常见安装路径回退
    candidates = [
        Path("C:/Program Files/Microsoft Visual Studio/2022"),
        Path("C:/Program Files/Microsoft Visual Studio/2019"),
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft Visual Studio/2022",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft Visual Studio/2019",
    ]
    for vs_dir in candidates:
        for edition in ["Enterprise", "Professional", "Community", "BuildTools"]:
            vc_tools = vs_dir / edition / "VC" / "Tools" / "MSVC"
            if vc_tools.exists():
                versions = sorted(vc_tools.iterdir(), reverse=True)
                if versions:
                    return versions[0]
    return None


def _find_windows_sdk() -> Path | None:
    """自动查找 Windows SDK 目录（最新版本）"""
    kit_bases = [
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Windows Kits" / "10",
        Path("C:/Program Files/Windows Kits/10"),
    ]
    for kit_base in kit_bases:
        lib_dir = kit_base / "Lib"
        if lib_dir.exists():
            versions = sorted(lib_dir.iterdir(), reverse=True)
            for v in versions:
                if (v / "um" / "x64").exists():
                    return v
        inc_dir = kit_base / "Include"
        if inc_dir.exists():
            versions = sorted(inc_dir.iterdir(), reverse=True)
            for v in versions:
                if (v / "ucrt").exists():
                    return v
    return None


def _load_vsdevcmd_env(env: dict[str, str]) -> dict[str, str]:
    """通过 VsDevCmd.bat 加载完整 MSVC/SDK 环境，而不是手工拼 PATH。"""
    installation = _find_vs_installation()
    if not installation:
        raise RuntimeError(
            "未找到包含 C++ x64 工具链的 Visual Studio 2022 Build Tools。\n"
            "请安装 Microsoft.VisualStudio.Workload.VCTools 和 Windows 10/11 SDK。"
        )

    vsdevcmd = installation / "Common7" / "Tools" / "VsDevCmd.bat"
    if not vsdevcmd.is_file():
        raise RuntimeError(f"VsDevCmd.bat 不存在: {vsdevcmd}")

    command = f'call "{vsdevcmd}" -no_logo -arch=x64 -host_arch=x64 >nul && set'
    result = subprocess.run(
        # Run the vetted command string through cmd.exe itself. Passing it as a
        # list makes Python escape the quotes around a path with spaces, which
        # then prevents cmd.exe from finding VsDevCmd.bat.
        command,
        shell=True,
        executable=os.environ.get("COMSPEC", "cmd.exe"),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(f"加载 Visual Studio 开发环境失败: {result.stderr.strip()}")

    loaded = env.copy()
    for line in result.stdout.splitlines():
        if "=" not in line or line.startswith("="):
            continue
        key, value = line.split("=", 1)
        canonical_key = next((item for item in loaded if item.upper() == key.upper()), key)
        loaded[canonical_key] = value
    return loaded


def setup_msvc_env():
    """设置可复现的 MSVC 编译环境（自动检测安装路径）。"""
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    # 已在 VS Developer PowerShell/CMD 中时可复用；否则加载 VsDevCmd。
    if not (env.get("VSCMD_VER") and shutil.which("link.exe", path=env.get("PATH"))):
        env = _load_vsdevcmd_env(env)

    msvc_base = _find_msvc()
    sdk_base = _find_windows_sdk()
    print(f"MSVC: {msvc_base or '由 VsDevCmd 管理'}")
    print(f"SDK:  {sdk_base or env.get('WindowsSdkDir', '由 VsDevCmd 管理')}")

    if not shutil.which("link.exe", path=env.get("PATH")):
        raise RuntimeError("MSVC linker link.exe 未出现在 VsDevCmd PATH 中")
    if not shutil.which("cargo.exe", path=env.get("PATH")):
        raise RuntimeError("cargo.exe 未出现在 PATH 中；请安装 Rust MSVC toolchain")
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


def step2_build_tauri(env, package_mode: str):
    """Step 2: 构建 Tauri 应用（前端+壳+嵌入前端资源）"""
    print("\n" + "=" * 60)
    print("Step 2: Building Tauri app (frontend + shell)...")
    print("=" * 60)

    # 本地 Tauri CLI 会自动执行:
    #   1. beforeBuildCommand (npm run build → Vite 构建前端)
    #   2. cargo build --release (编译 Rust 壳)
    #   3. 嵌入 dist/ 到 exe 中
    #   4. 生成 MSI/NSIS 安装包
    npm = shutil.which("npm.cmd", path=env.get("PATH"))
    if not npm:
        print("ERROR: npm.cmd not found on PATH")
        sys.exit(1)

    # 通过 package.json 中的本地 Tauri CLI 构建，避免调用全局 npx/tauri。
    scripts = {
        "portable": "tauri:build:portable",
        "installers": "tauri:build",
    }
    script = scripts[package_mode]
    if package_mode == "installers":
        # PowerShell removes variables assigned an empty string. Passing the
        # environment from Python preserves an explicit empty password so an
        # unencrypted updater key never triggers an interactive prompt.
        env.setdefault("TAURI_SIGNING_PRIVATE_KEY_PASSWORD", "")
    print(f"Tauri package mode: {package_mode}")
    result = subprocess.run(
        [npm, "run", script],
        cwd=TAURI_DIR,
        env=env,
        shell=False,
    )
    if result.returncode != 0:
        print("ERROR: Tauri build failed")
        sys.exit(1)

    exe = RELEASE_DIR / "nexus-ui.exe"
    if exe.exists():
        print(f"Tauri exe: {exe} ({exe.stat().st_size / 1024 / 1024:.1f} MB)")
    else:
        print(f"WARNING: {exe} not found")


def step3_package(package_mode: str):
    """Step 3: 整理发布文件"""
    print("\n" + "=" * 60)
    print("Step 3: Packaging release...")
    print("=" * 60)

    release_dir = PACKAGE_OUTPUT_DIR
    if release_dir.exists():
        shutil.rmtree(release_dir)
    release_dir.mkdir(parents=True, exist_ok=True)

    # 复制 Tauri exe
    tauri_exe = RELEASE_DIR / "nexus-ui.exe"
    if tauri_exe.exists():
        shutil.copy2(tauri_exe, release_dir / "AI-Nexus-Assistant.exe")
        print(f"  -> {release_dir / 'AI-Nexus-Assistant.exe'}")

    # 复制 WebView2 loader（如果存在）
    for dll in RELEASE_DIR.glob("*.dll"):
        shutil.copy2(dll, release_dir / dll.name)
        print(f"  -> {release_dir / dll.name}")

    # 复制五子棋 AI 模型文件（如果存在）
    model_src = PROJECT_DIR / "data" / "gomoku_model.onnx"
    data_dst = release_dir / "data"
    data_dst.mkdir(parents=True, exist_ok=True)
    if model_src.exists():
        shutil.copy2(model_src, data_dst / "gomoku_model.onnx")
        print(f"  -> {data_dst / 'gomoku_model.onnx'} ({model_src.stat().st_size / 1024:.1f} KB)")
    else:
        print(f"  WARNING: {model_src} not found, LV.7 will use heuristic fallback")

    # 复制 open-webSearch 目录（AI Chat Web Search 需要 Node.js 运行时）
    ows_src = PROJECT_DIR / "open-webSearch"
    ows_dst = release_dir / "open-webSearch"
    if ows_src.exists():
        if ows_dst.exists():
            try:
                shutil.rmtree(ows_dst)
            except PermissionError:
                print(f"  WARNING: 无法删除 {ows_dst}，跳过更新")
        if not ows_dst.exists():
            ows_dst.mkdir(parents=True)
        for item in ["build", "node_modules", "package.json"]:
            src_item = ows_src / item
            if src_item.exists():
                if src_item.is_dir():
                    shutil.copytree(src_item, ows_dst / item)
                else:
                    shutil.copy2(src_item, ows_dst / item)
        ows_size = sum(f.stat().st_size for f in ows_dst.rglob("*") if f.is_file())
        print(f"  -> {ows_dst} ({ows_size / 1024 / 1024:.1f} MB)")
    else:
        print("  WARNING: open-webSearch/ not found, web search will fallback to DuckDuckGo")

    # Only installer builds may populate installer artifacts. Filter by the
    # canonical version as the Cargo target can contain bundles from old runs.
    if package_mode == "installers":
        version = (PROJECT_DIR / "VERSION").read_text(encoding="utf-8").strip()
        bundle_dir = RELEASE_DIR / "bundle"
        installer_patterns = ("msi/*.msi", "nsis/*-setup.exe")
        copied_installers = 0
        for pattern in installer_patterns:
            for installer in bundle_dir.glob(pattern):
                if f"_{version}_" not in installer.name:
                    continue
                destination = release_dir / installer.name
                shutil.copy2(installer, destination)
                copied_installers += 1
                print(f"  -> {destination}")
        if copied_installers != 2:
            raise RuntimeError(
                f"Expected one MSI and one NSIS installer for {version}, "
                f"copied {copied_installers}"
            )

        signature_patterns = ("msi/*.msi.sig", "nsis/*-setup.exe.sig")
        copied_signatures = 0
        for pattern in signature_patterns:
            for signature in bundle_dir.glob(pattern):
                if f"_{version}_" not in signature.name:
                    continue
                shutil.copy2(signature, release_dir / signature.name)
                copied_signatures += 1
                print(f"  -> {release_dir / signature.name}")
        if copied_signatures != 2:
            raise RuntimeError(
                f"Expected MSI and NSIS updater signatures for {version}, "
                f"copied {copied_signatures} signatures"
            )

    # 统计
    total = sum(f.stat().st_size for f in release_dir.iterdir() if f.is_file())
    print(f"\nRelease package: {release_dir}")
    print(f"Total size: {total / 1024 / 1024:.1f} MB")


def main():
    print("AI Nexus Assistant — Tauri Portable Build")
    print("=" * 60)

    try:
        env = setup_msvc_env()
        package_mode = get_package_mode()
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        sys.exit(2)

    preflight = subprocess.run(
        [sys.executable, "tools/project_check.py", "--strict-environment"],
        cwd=PROJECT_DIR,
        env=env,
    )
    if preflight.returncode != 0:
        print("ERROR: Build environment preflight failed")
        sys.exit(preflight.returncode)

    step1_build_sidecar()
    step2_build_tauri(env, package_mode)
    step3_package(package_mode)
    if package_mode == "installers":
        from build_latest_json import generate_latest_json

        manifest = generate_latest_json(PACKAGE_OUTPUT_DIR)
        print(f"  -> {manifest}")

    print("\n" + "=" * 60)
    print("BUILD COMPLETE!")
    print(f"Release: {PROJECT_DIR / 'release'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
