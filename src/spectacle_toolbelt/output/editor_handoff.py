"""Handoff helpers for opening images in Spectacle's native editor."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


class EditorHandoffError(RuntimeError):
    """Raised when Toolbelt cannot hand an image to Spectacle."""


@dataclass(frozen=True)
class EditorHandoffCommand:
    argv: tuple[str, ...]


def build_edit_existing_command(image_path: str | Path, *, new_instance: bool = True) -> EditorHandoffCommand:
    path = Path(image_path)
    argv = ["spectacle"]
    if new_instance:
        argv.append("--new-instance")
    argv.extend(["--edit-existing", str(path)])
    return EditorHandoffCommand(argv=tuple(argv))


def ensure_spectacle_available() -> str:
    path = shutil.which("spectacle")
    if path is None:
        raise EditorHandoffError("KDE Spectacle is not available on PATH")
    return path


def open_in_spectacle(image_path: str | Path) -> EditorHandoffCommand:
    path = Path(image_path)
    if not path.exists():
        raise EditorHandoffError(f"image does not exist: {path}")
    if not path.is_file():
        raise EditorHandoffError(f"image is not a file: {path}")
    ensure_spectacle_available()
    command = build_edit_existing_command(path)
    try:
        subprocess.Popen(command.argv, start_new_session=True)
    except OSError as exc:
        raise EditorHandoffError(f"could not launch Spectacle: {exc}") from exc
    return command
