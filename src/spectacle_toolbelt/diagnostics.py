"""Local environment checks for Spectacle Toolbelt."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


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
        *_local_spectacle_launcher_checks(),
    )
    return DoctorReport(session_type=session_type, checks=checks)


def _local_spectacle_launcher_checks() -> tuple[ToolCheck, ...]:
    applications_dir = _xdg_data_home() / "applications"
    if not applications_dir.is_dir():
        return ()

    checks: list[ToolCheck] = []
    for path in sorted(applications_dir.glob("spectacle*.desktop")):
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if "Exec=" not in content:
            continue

        missing = [
            key
            for key in (
                "X-KDE-DBUS-Restricted-Interfaces=org.kde.KWin.ScreenShot2",
                "X-KDE-Wayland-Interfaces=org_kde_plasma_window_management,zkde_screencast_unstable_v1",
            )
            if key not in content
        ]
        checks.append(
            ToolCheck(
                name=f"{path.name} KWin authorization",
                available=not missing,
                path=str(path),
                required=False,
                note="ok" if not missing else f"missing {', '.join(missing)}",
            )
        )
    return tuple(checks)


def _xdg_data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
