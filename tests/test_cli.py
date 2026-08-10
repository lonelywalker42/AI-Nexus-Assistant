"""Tests for the optional desktop console entry point."""

from unittest.mock import patch


def test_nexus_entrypoint_explains_missing_desktop_extra(capsys):
    from app.cli import main

    with patch("app.cli.importlib.util.find_spec", return_value=None):
        assert main() == 2

    error = capsys.readouterr().err
    assert ".[desktop]" in error
    assert "optional desktop dependencies" in error
