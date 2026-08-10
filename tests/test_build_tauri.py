"""Regression tests for release artifact isolation."""

from pathlib import Path

import build_tauri


def test_installer_build_passes_explicit_empty_signing_password(monkeypatch, tmp_path):
    captured = {}

    class Result:
        returncode = 0

    def fake_run(*_args, **kwargs):
        captured.update(kwargs["env"])
        return Result()

    monkeypatch.setattr(build_tauri.shutil, "which", lambda *_args, **_kwargs: "npm.cmd")
    monkeypatch.setattr(build_tauri.subprocess, "run", fake_run)
    monkeypatch.setattr(build_tauri, "TAURI_DIR", tmp_path)
    monkeypatch.setattr(build_tauri, "RELEASE_DIR", tmp_path)

    build_tauri.step2_build_tauri({}, "installers")

    assert "TAURI_SIGNING_PRIVATE_KEY_PASSWORD" in captured
    assert captured["TAURI_SIGNING_PRIVATE_KEY_PASSWORD"] == ""


def _configure_paths(monkeypatch, tmp_path: Path):
    project = tmp_path / "project"
    cargo_release = tmp_path / "cargo-target" / "release"
    package_output = project / "release"
    cargo_release.mkdir(parents=True)
    package_output.mkdir(parents=True)
    (project / "VERSION").write_text("4.5.5\n", encoding="utf-8")
    (cargo_release / "nexus-ui.exe").write_bytes(b"portable")

    monkeypatch.setattr(build_tauri, "PROJECT_DIR", project)
    monkeypatch.setattr(build_tauri, "RELEASE_DIR", cargo_release)
    monkeypatch.setattr(build_tauri, "PACKAGE_OUTPUT_DIR", package_output)
    return cargo_release, package_output


def test_portable_package_removes_stale_installers(monkeypatch, tmp_path):
    _, package_output = _configure_paths(monkeypatch, tmp_path)
    (package_output / "old.msi").write_bytes(b"old")
    (package_output / "old-setup.exe").write_bytes(b"old")
    (package_output / "latest.json").write_text("stale", encoding="utf-8")

    build_tauri.step3_package("portable")

    assert (package_output / "AI-Nexus-Assistant.exe").read_bytes() == b"portable"
    assert list(package_output.glob("*.msi")) == []
    assert list(package_output.glob("*-setup.exe")) == []
    assert not (package_output / "latest.json").exists()


def test_installer_package_only_copies_current_version(monkeypatch, tmp_path):
    cargo_release, package_output = _configure_paths(monkeypatch, tmp_path)
    msi_dir = cargo_release / "bundle" / "msi"
    nsis_dir = cargo_release / "bundle" / "nsis"
    msi_dir.mkdir(parents=True)
    nsis_dir.mkdir(parents=True)

    current_msi = msi_dir / "AI Nexus Assistant_4.5.5_x64_en-US.msi"
    current_nsis = nsis_dir / "AI Nexus Assistant_4.5.5_x64-setup.exe"
    current_msi.write_bytes(b"msi")
    current_nsis.write_bytes(b"nsis")
    Path(f"{current_msi}.sig").write_text("msi-signature", encoding="utf-8")
    Path(f"{current_nsis}.sig").write_text("nsis-signature", encoding="utf-8")
    (msi_dir / "AI Nexus Assistant_4.5.4_x64_en-US.msi").write_bytes(b"stale")
    (nsis_dir / "AI Nexus Assistant_4.5.4_x64-setup.exe").write_bytes(b"stale")

    build_tauri.step3_package("installers")

    release_msi = package_output / current_msi.name.replace(" ", "-")
    release_nsis = package_output / current_nsis.name.replace(" ", "-")
    assert release_msi.read_bytes() == b"msi"
    assert release_nsis.read_bytes() == b"nsis"
    assert Path(f"{release_msi}.sig").read_text(encoding="utf-8") == "msi-signature"
    assert Path(f"{release_nsis}.sig").read_text(encoding="utf-8") == "nsis-signature"
    assert not (package_output / "AI Nexus Assistant_4.5.4_x64_en-US.msi").exists()
    assert not (package_output / "AI Nexus Assistant_4.5.4_x64-setup.exe").exists()
