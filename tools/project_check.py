"""Project metadata and Windows build-environment preflight checks.

This script intentionally uses only the Python standard library so it can run
before project dependencies are installed.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.ok: list[str] = []

    def good(self, message: str) -> None:
        self.ok.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def print(self) -> None:
        for message in self.ok:
            print(f"[OK]    {message}")
        for message in self.warnings:
            print(f"[WARN]  {message}")
        for message in self.errors:
            print(f"[ERROR] {message}")
        print(
            f"\nSummary: {len(self.ok)} ok, "
            f"{len(self.warnings)} warning(s), {len(self.errors)} error(s)"
        )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _toml_value(path: Path, section: str, key: str) -> str | None:
    current = ""
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
            continue
        if current != section:
            continue
        match = re.match(rf"{re.escape(key)}\s*=\s*[\"']([^\"']+)[\"']", line)
        if match:
            return match.group(1)
    return None


def _regex_value(path: Path, pattern: str) -> str | None:
    match = re.search(pattern, path.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1) if match else None


def check_versions(report: Report) -> None:
    package_json = _read_json(ROOT / "nexus-ui" / "package.json")
    package_lock = _read_json(ROOT / "nexus-ui" / "package-lock.json")
    tauri_conf = _read_json(ROOT / "nexus-ui" / "src-tauri" / "tauri.conf.json")

    values = {
        "VERSION": VERSION,
        "pyproject.toml": _toml_value(ROOT / "pyproject.toml", "project", "version"),
        "nexus-ui/package.json": package_json.get("version"),
        "nexus-ui/package-lock.json": package_lock.get("version"),
        "tauri.conf.json": tauri_conf.get("version"),
        "Cargo.toml": _toml_value(
            ROOT / "nexus-ui" / "src-tauri" / "Cargo.toml", "package", "version"
        ),
        "Cargo.lock": _regex_value(
            ROOT / "nexus-ui" / "src-tauri" / "Cargo.lock",
            r'\[\[package\]\]\s+name\s*=\s*"nexus-ui"\s+version\s*=\s*"([^"]+)"',
        ),
        "client.ts": _regex_value(
            ROOT / "nexus-ui" / "src" / "api" / "client.ts",
            r'APP_VERSION\s*=\s*"([^"]+)"',
        ),
        "server.py": _regex_value(ROOT / "server.py", r'FastAPI\([^\n]+version="([^"]+)"'),
    }

    mismatches = {name: value for name, value in values.items() if value != VERSION}
    if mismatches:
        for name, value in mismatches.items():
            report.error(f"version mismatch: {name}={value!r}, expected {VERSION!r}")
    else:
        report.good(f"all release metadata uses version {VERSION}")

    root_lock_version = package_lock.get("packages", {}).get("", {}).get("version")
    if root_lock_version != VERSION:
        report.error(
            "nexus-ui/package-lock.json root package version is "
            f"{root_lock_version!r}, expected {VERSION!r}"
        )

    displays = {
        "LoginPage.tsx": ROOT / "nexus-ui" / "src" / "pages" / "LoginPage.tsx",
        "PySide main_window.py": ROOT / "app" / "ui" / "main_window.py",
    }
    for name, path in displays.items():
        if f"v{VERSION}" not in path.read_text(encoding="utf-8"):
            report.error(f"display version not synchronized in {name}")


def check_project_files(report: Report) -> None:
    required = [
        ROOT / "VERSION",
        ROOT / "build_latest_json.py",
        ROOT / "docs" / "WINDOWS-BUILD.md",
        ROOT / "scripts" / "windows" / "build-release.ps1",
        ROOT / "scripts" / "windows" / "install-local-toolchains.ps1",
        ROOT / "scripts" / "windows" / "install-vs-buildtools.ps1",
        ROOT / "scripts" / "windows" / "setup-build-env.ps1",
        ROOT / "tools" / "project_check.py",
        ROOT / "nexus-ui" / "package-lock.json",
        ROOT / "nexus-ui" / "src-tauri" / "Cargo.lock",
        ROOT / "open-webSearch" / "package-lock.json",
        ROOT / ".editorconfig",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        report.error(f"required project files missing: {', '.join(missing)}")
    else:
        report.good("Python, npm and Cargo project metadata/lock files are present")

    if (ROOT / ".git").exists() and shutil.which("git"):
        # Files inside the open-webSearch submodule are tracked by its own Git
        # index; the parent repository tracks the submodule gitlink itself.
        tracked_required = [
            path for path in required
            if path != ROOT / "open-webSearch" / "package-lock.json"
        ] + [ROOT / "open-webSearch"]
        untracked = []
        for path in tracked_required:
            relative = path.relative_to(ROOT).as_posix()
            completed = subprocess.run(
                ["git", "ls-files", "--error-unmatch", "--", relative],
                cwd=ROOT,
                capture_output=True,
                check=False,
                text=True,
            )
            if completed.returncode != 0:
                untracked.append(relative)
        if untracked:
            report.error(
                "required release workflow files are not tracked by Git: "
                + ", ".join(untracked)
            )
        else:
            report.good("all required release workflow files are tracked by Git")

    path_text = str(ROOT)
    if any(char in path_text for char in "&;!`'"):
        report.error(f"repository path contains shell-sensitive characters: {ROOT}")
    elif "OneDrive" in path_text:
        report.warn(f"repository is under OneDrive; file locking can break builds: {ROOT}")
    else:
        report.good(f"repository path is build-safe: {ROOT}")


def _build_toolchain_environment() -> dict[str, str]:
    """Return an environment that consistently exposes repo-local Rust."""
    environment = os.environ.copy()
    toolchain_root = ROOT / ".toolchains"
    cargo_home = toolchain_root / "cargo"
    rustup_home = toolchain_root / "rustup"
    cargo_bin = cargo_home / "bin"
    if cargo_bin.is_dir() and rustup_home.is_dir():
        environment["CARGO_HOME"] = str(cargo_home)
        environment["RUSTUP_HOME"] = str(rustup_home)
        existing_path = environment.get("PATH", "")
        environment["PATH"] = os.pathsep.join(
            [str(cargo_bin), existing_path] if existing_path else [str(cargo_bin)]
        )
    return environment


def _command_output(command: list[str], *, environment: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
        env=environment,
    )
    output = (completed.stdout or completed.stderr).strip().splitlines()
    return output[0] if output else f"exit={completed.returncode}"


def _find_vswhere() -> Path | None:
    candidates = [
        Path(os.environ.get("ProgramFiles(x86)", ""))
        / "Microsoft Visual Studio"
        / "Installer"
        / "vswhere.exe",
        Path(os.environ.get("ProgramFiles", ""))
        / "Microsoft Visual Studio"
        / "Installer"
        / "vswhere.exe",
    ]
    return next((path for path in candidates if path.is_file()), None)


def check_environment(report: Report, strict: bool) -> None:
    if platform.system() != "Windows":
        report.error("Windows release builds must run on Windows")

    version = sys.version_info
    if (version.major, version.minor) not in {(3, 10), (3, 11), (3, 12), (3, 13)}:
        report.error(f"unsupported Python for build: {platform.python_version()}")
    else:
        report.good(f"Python {platform.python_version()}: {sys.executable}")

    expected_venv = (ROOT / ".build-env" / "python").resolve()
    current_prefix = Path(sys.prefix).resolve()
    if current_prefix != expected_venv:
        message = f"build Python is not the managed venv: {current_prefix}"
        report.error(message) if strict else report.warn(message)
    else:
        report.good("Python runs from .build-env/python")

    toolchain_environment = _build_toolchain_environment()
    command_path = toolchain_environment.get("PATH")
    commands = {
        "node": ["node", "--version"],
        "npm": ["npm.cmd", "--version"],
        "rustc": ["rustc", "--version"],
        "cargo": ["cargo", "--version"],
        "git": ["git", "--version"],
    }
    for name, command in commands.items():
        resolved = shutil.which(command[0], path=command_path)
        if not resolved:
            report.error(f"{name} is not available on PATH")
            continue
        report.good(
            f"{name}: {_command_output(command, environment=toolchain_environment)} ({resolved})"
        )

    node = shutil.which("node", path=command_path)
    if node:
        node_version = _command_output([node, "--version"], environment=toolchain_environment)
        match = re.search(r"(\d+)", node_version)
        if not match or int(match.group(1)) < 18:
            report.error(f"Node.js 18+ x64 is required; found {node_version}")
        node_arch = _command_output([node, "-p", "process.arch"], environment=toolchain_environment)
        if node_arch != "x64":
            report.error(f"Node.js architecture must be x64; found {node_arch}")
        else:
            report.good("Node.js architecture is x64")

    rustc = shutil.which("rustc", path=command_path)
    if rustc:
        details = subprocess.run(
            [rustc, "-vV"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
            env=toolchain_environment,
        ).stdout
        host = re.search(r"^host:\s*(.+)$", details, re.MULTILINE)
        if not host or host.group(1).strip() != "x86_64-pc-windows-msvc":
            report.error("Rust host must be x86_64-pc-windows-msvc")
        else:
            report.good("Rust host is x86_64-pc-windows-msvc")

    vswhere = _find_vswhere()
    if not vswhere:
        report.error("vswhere.exe not found; install Visual Studio 2022 Build Tools")
    else:
        completed = subprocess.run(
            [
                str(vswhere),
                "-latest",
                "-products",
                "*",
                "-requires",
                "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                "-property",
                "installationPath",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        installation = completed.stdout.strip()
        if not installation:
            report.error("Visual Studio C++ x64 build tools were not found")
        else:
            report.good(f"Visual Studio C++ toolchain: {installation}")

    kit_roots = [
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Windows Kits" / "10",
        Path(os.environ.get("ProgramFiles", "")) / "Windows Kits" / "10",
    ]
    sdk_ok = False
    for root in kit_roots:
        include_root = root / "Include"
        lib_root = root / "Lib"
        if not include_root.is_dir() or not lib_root.is_dir():
            continue
        versions = sorted(include_root.iterdir(), reverse=True)
        sdk_ok = any(
            (version / "um" / "Windows.h").is_file()
            and (lib_root / version.name / "um" / "x64" / "kernel32.lib").is_file()
            for version in versions
        )
        if sdk_ok:
            report.good(f"Windows SDK: {root}")
            break
    if not sdk_ok:
        report.error("Windows 10/11 SDK x64 headers and libraries were not found")

    path_entries = [entry for entry in os.environ.get("PATH", "").split(os.pathsep) if entry]
    normalized = [os.path.normcase(os.path.abspath(entry)) for entry in path_entries]
    duplicates = sorted({entry for entry in normalized if normalized.count(entry) > 1})
    if duplicates:
        report.warn(f"PATH contains {len(duplicates)} duplicate entrie(s)")

    conflicting = [
        entry for entry in path_entries
        if any(marker in entry.lower() for marker in ("anaconda", "miniconda", "msys", "cygwin"))
    ]
    if conflicting:
        report.warn("PATH contains toolchains that may shadow MSVC: " + "; ".join(conflicting))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--environment", action="store_true", help="also validate the Windows build toolchain"
    )
    parser.add_argument(
        "--strict-environment",
        action="store_true",
        help="require the repository-managed Python virtual environment",
    )
    args = parser.parse_args()

    report = Report()
    check_versions(report)
    check_project_files(report)
    if args.environment or args.strict_environment:
        check_environment(report, strict=args.strict_environment)
    report.print()
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
