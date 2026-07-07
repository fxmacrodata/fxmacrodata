"""Convenience launchers for FXMacroData OpenBB integrations."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, NoReturn, Optional


def _find_console_script(executable_name: str) -> Optional[str]:
    executable = shutil.which(executable_name)
    if executable is not None:
        return executable

    scripts_dir = Path(sys.executable).resolve().parent
    candidates = [scripts_dir / executable_name]
    if not executable_name.endswith(".exe"):
        candidates.append(scripts_dir / f"{executable_name}.exe")

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return None


def _run_console_script(
    executable_name: str,
    args: Optional[Iterable[str]] = None,
    install_hint: str = "",
) -> NoReturn:
    executable = _find_console_script(executable_name)
    if executable is None:
        hint = f" Install {install_hint} first." if install_hint else ""
        raise SystemExit(f"Could not find '{executable_name}' on PATH.{hint}")

    command = [executable, *(list(args) if args is not None else sys.argv[1:])]
    raise SystemExit(subprocess.call(command))


def platform_api(argv: Optional[List[str]] = None) -> NoReturn:
    """Launch OpenBB Platform API with the installed FXMacroData extension."""
    _run_console_script(
        "openbb-api",
        argv,
        "fxmacrodata[openbb-api]",
    )


def mcp(argv: Optional[List[str]] = None) -> NoReturn:
    """Launch OpenBB MCP with the installed FXMacroData extension."""
    _run_console_script(
        "openbb-mcp",
        argv,
        "fxmacrodata[mcp]",
    )
