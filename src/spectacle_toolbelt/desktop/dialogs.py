"""Small KDE dialog boundary used by visible Toolbelt workflows."""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass

from spectacle_toolbelt.capture.area import ScreenRect


class DialogError(RuntimeError):
    """Raised when a required dialog interaction cannot continue."""


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


class KdeDialog:
    """KDialog-backed UI with a terminal fallback for non-KDE test/dev shells."""

    title = "Spectacle Toolbelt"

    def __init__(self) -> None:
        self._kdialog = shutil.which("kdialog")

    @property
    def is_graphical(self) -> bool:
        return self._kdialog is not None

    def choose_scroll_mode(self, default: str = "manual") -> str:
        if self._kdialog:
            result = self._run(
                [
                    self._kdialog,
                    "--title",
                    "Spectacle Toolbelt Scrolling Capture",
                    "--default",
                    default,
                    "--menu",
                    "Choose scrolling capture mode",
                    "manual",
                    "Manual / panoramic",
                    "auto-vertical",
                    "Auto vertical",
                    "auto-horizontal",
                    "Auto horizontal",
                ]
            )
            if result.returncode != 0:
                raise DialogError("scrolling capture cancelled")
            mode = result.stdout.strip()
            if mode:
                return mode
            return default

        self._require_terminal("choose a scrolling capture mode")
        print("Choose scrolling capture mode:")
        print("1. Manual / panoramic")
        print("2. Auto vertical")
        print("3. Auto horizontal")
        choice = input(f"Mode [{default}]: ").strip()
        return {
            "1": "manual",
            "2": "auto-vertical",
            "3": "auto-horizontal",
            "": default,
        }.get(choice, default)

    def choose_scroll_direction(self, default: str = "vertical") -> str:
        if self._kdialog:
            result = self._run(
                [
                    self._kdialog,
                    "--title",
                    "Spectacle Toolbelt Scrolling Capture",
                    "--default",
                    default,
                    "--menu",
                    "Choose manual scroll direction",
                    "vertical",
                    "Vertical",
                    "horizontal",
                    "Horizontal",
                ]
            )
            if result.returncode != 0:
                raise DialogError("scrolling capture cancelled")
            direction = result.stdout.strip()
            if direction:
                return direction
            return default

        self._require_terminal("choose a manual scroll direction")
        print("Choose manual scroll direction:")
        print("1. Vertical")
        print("2. Horizontal")
        choice = input(f"Direction [{default}]: ").strip()
        return {
            "1": "vertical",
            "2": "horizontal",
            "": default,
        }.get(choice, default)

    def prompt_url(self, *, initial: str = "") -> str | None:
        if self._kdialog:
            result = self._run(
                [
                    self._kdialog,
                    "--title",
                    "Spectacle Toolbelt Full-Page Web Capture",
                    "--inputbox",
                    "Enter the webpage URL to capture",
                    initial,
                ]
            )
            if result.returncode != 0:
                return None
            value = result.stdout.strip()
            return value or None

        self._require_terminal("enter a webpage URL")
        value = input("Webpage URL: ").strip()
        return value or None

    def show_message(self, message: str) -> None:
        if self._kdialog:
            self._run([self._kdialog, "--title", self.title, "--msgbox", message])
            return
        print(message)

    def show_error(self, message: str, details: str | None = None) -> None:
        if self._kdialog:
            if details:
                self._run([self._kdialog, "--title", self.title, "--detailederror", message, details])
            else:
                self._run([self._kdialog, "--title", self.title, "--error", message])
            return
        print(f"ERROR: {message}")
        if details:
            print(details)

    def show_passive(self, message: str, *, timeout_seconds: int = 4) -> None:
        if self._kdialog:
            self._run(
                [
                    self._kdialog,
                    "--title",
                    self.title,
                    "--passivepopup",
                    message,
                    str(timeout_seconds),
                ]
            )
            return
        print(message)

    def next_scroll_action(self, frame_count: int, *, mode: str, avoid_rect: ScreenRect | None = None) -> str:
        message = (
            f"Captured {frame_count} frame{'s' if frame_count != 1 else ''}.\n\n"
            "Scroll the content behind this prompt to the next position, "
            "then choose Capture Next.\n"
            "Toolbelt will capture the same viewport rectangle again.\n"
            "Choose Done to stitch and open the result in Spectacle."
        )
        if mode != "manual":
            message = (
                f"Captured {frame_count} frame{'s' if frame_count != 1 else ''}.\n\n"
                "Choose Capture Next to let Toolbelt scroll and capture another frame.\n"
                "Choose Done to stitch and open the result in Spectacle."
            )

        if self._kdialog:
            result = self._run(
                [
                    self._kdialog,
                    *_geometry_args_avoiding(avoid_rect),
                    "--title",
                    "Spectacle Toolbelt Scrolling Capture",
                    "--yes-label",
                    "Capture Next",
                    "--no-label",
                    "Done",
                    "--cancel-label",
                    "Cancel",
                    "--yesnocancel",
                    message,
                ]
            )
            if result.returncode == 0:
                return "capture-next"
            if result.returncode == 1:
                return "done"
            return "cancel"

        self._require_terminal("choose the next scrolling capture action")
        choice = input("[c]apture next, [d]one, [x] cancel: ").strip().casefold()
        if choice.startswith("d"):
            return "done"
        if choice.startswith("x") or choice.startswith("q"):
            return "cancel"
        return "capture-next"

    def _require_terminal(self, action: str) -> None:
        if not sys.stdin.isatty():
            raise DialogError(f"kdialog is required to {action} when no terminal stdin is available")

    def _run(self, argv: list[str]) -> CommandResult:
        completed = subprocess.run(argv, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return CommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


def _geometry_args_avoiding(avoid_rect: ScreenRect | None) -> list[str]:
    if avoid_rect is None:
        return []
    geometry = _dialog_geometry_avoiding(avoid_rect)
    return ["--geometry", geometry] if geometry else []


def _dialog_geometry_avoiding(avoid_rect: ScreenRect) -> str | None:
    monitors = _desktop_monitor_rects()
    if not monitors:
        return "560x220+24+24"

    fallback: tuple[int, int, int, int] | None = None
    for monitor in monitors:
        dialog_width = min(560, max(320, monitor.width - 48))
        dialog_height = min(220, max(160, monitor.height - 48))
        candidates = [
            (monitor.x + 24, monitor.y + 24),
            (monitor.x + monitor.width - dialog_width - 24, monitor.y + 24),
            (monitor.x + 24, monitor.y + monitor.height - dialog_height - 24),
            (
                monitor.x + monitor.width - dialog_width - 24,
                monitor.y + monitor.height - dialog_height - 24,
            ),
        ]
        if fallback is None:
            fallback = (dialog_width, dialog_height, monitor.x + 24, monitor.y + 24)
        for x, y in candidates:
            candidate = ScreenRect(x, y, dialog_width, dialog_height)
            if not _rects_overlap(candidate, avoid_rect):
                return _geometry(dialog_width, dialog_height, x, y)
    if fallback is None:
        return None
    return _geometry(*fallback)


def _desktop_monitor_rects() -> list[ScreenRect]:
    try:
        import gi

        gi.require_version("Gdk", "4.0")
        from gi.repository import Gdk

        display = Gdk.Display.get_default()
        if display is None:
            return []
        monitors = display.get_monitors()
        rects: list[ScreenRect] = []
        for index in range(monitors.get_n_items()):
            monitor = monitors.get_item(index)
            if monitor is None:
                continue
            geometry = monitor.get_geometry()
            rects.append(ScreenRect(int(geometry.x), int(geometry.y), int(geometry.width), int(geometry.height)))
        return rects
    except Exception:
        return []


def _rects_overlap(first: ScreenRect, second: ScreenRect) -> bool:
    return not (
        first.x + first.width <= second.x
        or second.x + second.width <= first.x
        or first.y + first.height <= second.y
        or second.y + second.height <= first.y
    )


def _geometry(width: int, height: int, x: int, y: int) -> str:
    return f"{width}x{height}{x:+d}{y:+d}"
