"""Filesystem output helpers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def default_screenshot_dir() -> Path:
    pictures = Path.home() / "Pictures" / "Screenshots"
    return pictures


def timestamped_output_path(prefix: str = "Scrolling Screenshot") -> Path:
    stamp = datetime.now().strftime("%Y-%m-%d %H.%M.%S")
    return default_screenshot_dir() / f"{prefix} {stamp}.png"
