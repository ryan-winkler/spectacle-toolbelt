"""Adapter boundary for invoking KDE Spectacle."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


class CaptureError(RuntimeError):
    """Raised when the Spectacle capture adapter cannot capture a frame."""


@dataclass(frozen=True)
class CaptureCommand:
    argv: tuple[str, ...]


def build_region_capture_command(output: Path, *, background: bool = True) -> CaptureCommand:
    argv = ["spectacle", "--region", "--output", str(output)]
    if background:
        argv.insert(1, "--background")
    return CaptureCommand(argv=tuple(argv))


def ensure_spectacle_available() -> str:
    path = shutil.which("spectacle")
    if path is None:
        raise CaptureError("KDE Spectacle is not available on PATH")
    return path


def capture_region(output: Path) -> Path:
    ensure_spectacle_available()
    command = build_region_capture_command(output)
    completed = subprocess.run(command.argv, check=False)
    if completed.returncode != 0:
        raise CaptureError(f"Spectacle exited with {completed.returncode}")
    if not output.exists():
        raise CaptureError(f"Spectacle did not create {output}")
    return output
