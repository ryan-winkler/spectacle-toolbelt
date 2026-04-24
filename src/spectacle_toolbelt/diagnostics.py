"""Local environment checks for Spectacle Toolbelt."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolCheck:
    name: str
    available: bool
    path: str | None = None
    required: bool = False
    note: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "available": self.available,
            "path": self.path,
            "required": self.required,
            "note": self.note,
        }


@dataclass(frozen=True)
class DoctorReport:
    session_type: str
    checks: tuple[ToolCheck, ...]

    @property
    def is_usable(self) -> bool:
        return all(check.available for check in self.checks if check.required)

    def to_dict(self) -> dict[str, object]:
        return {
            "sessionType": self.session_type,
            "usable": self.is_usable,
            "checks": [check.to_dict() for check in self.checks],
        }

    def to_text(self) -> str:
        lines = [
            "Spectacle Toolbelt doctor",
            f"session: {self.session_type}",
            f"usable: {'yes' if self.is_usable else 'no'}",
            "",
        ]
        for check in self.checks:
            status = "ok" if check.available else "missing"
            required = "required" if check.required else "optional"
            suffix = f" ({check.note})" if check.note else ""
            path = f" -> {check.path}" if check.path else ""
            lines.append(f"- {check.name}: {status} [{required}]{path}{suffix}")
        return "\n".join(lines)


def _tool(name: str, *, required: bool = False, note: str | None = None) -> ToolCheck:
    path = shutil.which(name)
    return ToolCheck(
        name=name,
        available=path is not None,
        path=path,
        required=required,
        note=note,
    )


def run_doctor() -> DoctorReport:
    session_type = os.environ.get("XDG_SESSION_TYPE", "unknown")
    clipboard_candidates = (
        _tool("wl-copy", note="Wayland clipboard"),
        _tool("xclip", note="X11 clipboard"),
        _tool("xsel", note="X11 clipboard"),
    )
    checks = (
        _tool("spectacle", required=True, note="capture adapter"),
        _tool("magick", note="ImageMagick 7"),
        _tool("convert", note="ImageMagick 6 compatibility"),
        *clipboard_candidates,
        _tool("notify-send", note="desktop notifications"),
    )
    return DoctorReport(session_type=session_type, checks=checks)
