"""Tests for OpenBB launcher convenience wrappers."""

from __future__ import annotations

import pytest

from fxmacrodata.openbb import launcher


def test_platform_api_launcher_forwards_args(monkeypatch: pytest.MonkeyPatch):
    """The API launcher should delegate to OpenBB's official CLI."""
    calls = []

    monkeypatch.setattr(launcher.shutil, "which", lambda name: f"/bin/{name}")
    monkeypatch.setattr(
        launcher.subprocess,
        "call",
        lambda command: calls.append(command) or 0,
    )

    with pytest.raises(SystemExit) as exc:
        launcher.platform_api(["--port", "6901"])

    assert exc.value.code == 0
    assert calls == [["/bin/openbb-api", "--port", "6901"]]


def test_mcp_launcher_forwards_args(monkeypatch: pytest.MonkeyPatch):
    """The MCP launcher should delegate to OpenBB's official CLI."""
    calls = []

    monkeypatch.setattr(launcher.shutil, "which", lambda name: f"/bin/{name}")
    monkeypatch.setattr(
        launcher.subprocess,
        "call",
        lambda command: calls.append(command) or 0,
    )

    with pytest.raises(SystemExit) as exc:
        launcher.mcp(["--default-categories", "fxmacrodata"])

    assert exc.value.code == 0
    assert calls == [["/bin/openbb-mcp", "--default-categories", "fxmacrodata"]]


def test_launcher_errors_when_openbb_cli_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path
):
    """Missing optional OpenBB executables should fail with installation guidance."""
    monkeypatch.setattr(launcher.shutil, "which", lambda name: None)
    monkeypatch.setattr(launcher.sys, "executable", str(tmp_path / "python.exe"))

    with pytest.raises(SystemExit) as exc:
        launcher.platform_api([])

    assert "fxmacrodata[openbb-api]" in str(exc.value)


def test_launcher_falls_back_to_venv_sibling_executable(
    monkeypatch: pytest.MonkeyPatch, tmp_path
):
    """Direct Windows console-script execution should find sibling OpenBB scripts."""
    scripts_dir = tmp_path / "Scripts"
    scripts_dir.mkdir()
    openbb_api = scripts_dir / "openbb-api.exe"
    openbb_api.write_text("", encoding="utf-8")
    calls = []

    monkeypatch.setattr(launcher.shutil, "which", lambda name: None)
    monkeypatch.setattr(launcher.sys, "executable", str(scripts_dir / "python.exe"))
    monkeypatch.setattr(
        launcher.subprocess,
        "call",
        lambda command: calls.append(command) or 0,
    )

    with pytest.raises(SystemExit) as exc:
        launcher.platform_api(["--port", "6901"])

    assert exc.value.code == 0
    assert calls == [[str(openbb_api), "--port", "6901"]]
