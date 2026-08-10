"""Tests for Tauri updater manifest generation."""

import json

import pytest

from build_latest_json import find_signed_updater, generate_latest_json


def test_generate_latest_json_uses_signed_nsis_installer(tmp_path):
    installer = tmp_path / "AI Nexus Assistant_4.5.5_x64-setup.exe"
    installer.write_bytes(b"installer")
    signature = tmp_path / f"{installer.name}.sig"
    signature.write_text("signed-value\n", encoding="utf-8")

    output = generate_latest_json(tmp_path, "4.5.5")
    manifest = json.loads(output.read_text(encoding="utf-8"))
    windows = manifest["platforms"]["windows-x86_64"]

    assert windows["signature"] == "signed-value"
    assert windows["url"].endswith(
        "/AI-Nexus-Assistant_4.5.5_x64-setup.exe"
    )


def test_signed_updater_requires_signature(tmp_path):
    (tmp_path / "AI Nexus Assistant_4.5.5_x64-setup.exe").write_bytes(b"installer")

    with pytest.raises(RuntimeError, match="signature"):
        find_signed_updater(tmp_path, "4.5.5")
