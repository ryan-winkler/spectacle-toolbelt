"""Small KDE dialog boundary used by visible Toolbelt workflows."""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass


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

    def next_scroll_action(self, frame_count: int, *, mode: str) -> str:
        message = (
            f"Captured {frame_count} frame{'s' if frame_count != 1 else ''}.\n\n"
            "Scroll the content to the next position, then choose Capture Next.\n"
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
