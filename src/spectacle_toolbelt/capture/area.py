"""Fixed-area capture helpers for scrolling sessions."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from spectacle_toolbelt.capture.spectacle_adapter import CaptureError


_XRANDR_CONNECTED_GEOMETRY_RE = re.compile(r"\b\d+x\d+([+-]\d+)([+-]\d+)\b")


@dataclass(frozen=True)
class ScreenRect:
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width < 1 or self.height < 1:
            raise ValueError("capture rectangle must have non-zero dimensions")

    @property
    def geometry(self) -> str:
        return f"{self.x},{self.y} {self.width}x{self.height}"


@dataclass(frozen=True)
class _X11Monitor:
    rect: ScreenRect
    scale: float


def capture_area(output: Path, rect: ScreenRect) -> Path:
    """Capture the same desktop rectangle without asking the user to reselect."""

    session_type = os.environ.get("XDG_SESSION_TYPE", "").casefold()
    if session_type == "wayland":
        return _capture_area_kwin(output, rect)
    return _capture_area_x11(output, rect)


def _capture_area_kwin(output: Path, rect: ScreenRect) -> Path:
    try:
        import dbus
    except ImportError as exc:
        raise CaptureError("dbus-python is required for fixed-region Wayland capture") from exc

    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        bus = dbus.SessionBus()
        screenshot = bus.get_object("org.kde.KWin", "/org/kde/KWin/ScreenShot2")
        iface = dbus.Interface(screenshot, "org.kde.KWin.ScreenShot2")
        with output.open("wb") as file:
            fd = dbus.types.UnixFd(file.fileno())
            iface.CaptureArea(
                int(rect.x),
                int(rect.y),
                dbus.UInt32(rect.width),
                dbus.UInt32(rect.height),
                {},
                fd,
                timeout=30,
            )
    except Exception as exc:
        message = str(exc)
        if "NoAuthorized" in message or "not authorized" in message:
            raise CaptureError(
                "KWin denied fixed-region capture. Launch scrolling capture from the installed "
                "KDE Toolbelt entry or Spectacle app action so KDE applies the screenshot "
                "authorization metadata."
            ) from exc
        raise CaptureError(f"KWin fixed-region capture failed: {message}") from exc

    _ensure_capture_written(output)
    return output


def _capture_area_x11(output: Path, rect: ScreenRect) -> Path:
    import_command = _resolve_import_command()
    if import_command is None:
        raise CaptureError("ImageMagick import is required for fixed-region X11 capture")
    pixel_rect = _x11_pixel_rect(rect)

    output.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [
            import_command,
            "-window",
            "root",
            "-crop",
            (
                f"{pixel_rect.width}x{pixel_rect.height}"
                f"{_signed_offset(pixel_rect.x)}{_signed_offset(pixel_rect.y)}"
            ),
            str(output),
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        raise CaptureError(f"fixed-region X11 capture failed: {completed.stderr.strip()}")
    _ensure_capture_written(output)
    return output


def _ensure_capture_written(output: Path) -> None:
    if not output.exists():
        raise CaptureError(f"fixed-region capture did not create {output}")
    if output.stat().st_size == 0:
        raise CaptureError(f"fixed-region capture wrote an empty file: {output}")


def _signed_offset(value: int) -> str:
    return f"{value:+d}"


def _resolve_import_command() -> str | None:
    configured = os.environ.get("SPECTACLE_TOOLBELT_IMPORT_COMMAND") or "import"
    if "/" in configured:
        return configured if os.access(configured, os.X_OK) else None
    return shutil.which(configured)


def _x11_crop_offsets(rect: ScreenRect) -> tuple[int, int]:
    origin = _x11_virtual_origin()
    if origin is None:
        if rect.x < 0 or rect.y < 0:
            raise CaptureError(
                "X11 fixed-region capture needs monitor geometry to translate "
                "negative desktop coordinates"
            )
        return rect.x, rect.y

    crop_x = rect.x - origin[0]
    crop_y = rect.y - origin[1]
    if crop_x < 0 or crop_y < 0:
        raise CaptureError("X11 fixed-region capture rectangle is outside the virtual desktop")
    return crop_x, crop_y


def _x11_pixel_rect(rect: ScreenRect) -> ScreenRect:
    crop_x, crop_y = _x11_crop_offsets(rect)
    scale = _x11_scale_factor(rect)
    return ScreenRect(
        int(round(crop_x * scale)),
        int(round(crop_y * scale)),
        max(1, int(round(rect.width * scale))),
        max(1, int(round(rect.height * scale))),
    )


def _x11_scale_factor(rect: ScreenRect) -> float:
    return _x11_scale_factor_from_gdk(rect) or 1.0


def _x11_scale_factor_from_gdk(rect: ScreenRect) -> float | None:
    try:
        import gi

        gi.require_version("Gdk", "4.0")
        from gi.repository import Gdk

        display = Gdk.Display.get_default()
        if display is None:
            return None
        monitors = display.get_monitors()
        layouts: list[_X11Monitor] = []
        for index in range(monitors.get_n_items()):
            monitor = monitors.get_item(index)
            if monitor is None:
                continue
            geometry = monitor.get_geometry()
            layouts.append(
                _X11Monitor(
                    ScreenRect(int(geometry.x), int(geometry.y), int(geometry.width), int(geometry.height)),
                    float(monitor.get_scale_factor()),
                )
            )
        return _x11_scale_factor_from_monitors(rect, layouts)
    except CaptureError:
        raise
    except Exception:
        return None


def _x11_scale_factor_from_monitors(rect: ScreenRect, monitors: list[_X11Monitor]) -> float | None:
    scales: set[float] = set()
    for monitor in monitors:
        overlap = _intersection(rect, monitor.rect)
        if overlap is None:
            continue
        scales.add(monitor.scale)
    if not scales:
        return None
    if len(scales) > 1:
        raise CaptureError("X11 fixed-region capture cannot span monitors with different scale factors")
    return next(iter(scales))


def _intersection(first: ScreenRect, second: ScreenRect) -> ScreenRect | None:
    x1 = max(first.x, second.x)
    y1 = max(first.y, second.y)
    x2 = min(first.x + first.width, second.x + second.width)
    y2 = min(first.y + first.height, second.y + second.height)
    if x2 <= x1 or y2 <= y1:
        return None
    return ScreenRect(x1, y1, x2 - x1, y2 - y1)


def _x11_virtual_origin() -> tuple[int, int] | None:
    gdk_origin = _x11_virtual_origin_from_gdk()
    if gdk_origin is not None:
        return gdk_origin
    return _x11_virtual_origin_from_xrandr()


def _x11_virtual_origin_from_gdk() -> tuple[int, int] | None:
    try:
        import gi

        gi.require_version("Gdk", "4.0")
        from gi.repository import Gdk

        display = Gdk.Display.get_default()
        if display is None:
            return None
        monitors = display.get_monitors()
        xs: list[int] = []
        ys: list[int] = []
        for index in range(monitors.get_n_items()):
            monitor = monitors.get_item(index)
            if monitor is None:
                continue
            geometry = monitor.get_geometry()
            xs.append(int(geometry.x))
            ys.append(int(geometry.y))
        if not xs or not ys:
            return None
        return min(xs), min(ys)
    except Exception:
        return None


def _x11_virtual_origin_from_xrandr() -> tuple[int, int] | None:
    xrandr = shutil.which("xrandr")
    if xrandr is None:
        return None

    completed = subprocess.run(
        [xrandr, "--query"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if completed.returncode != 0:
        return None

    xs: list[int] = []
    ys: list[int] = []
    for line in completed.stdout.splitlines():
        if " connected " not in line:
            continue
        match = _XRANDR_CONNECTED_GEOMETRY_RE.search(line)
        if match is None:
            continue
        xs.append(int(match.group(1)))
        ys.append(int(match.group(2)))
    if not xs or not ys:
        return None
    return min(xs), min(ys)
