"""Visible scrolling capture workflow controller."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from spectacle_toolbelt.capture.spectacle_adapter import CaptureError, capture_region
from spectacle_toolbelt.desktop.dialogs import DialogError, KdeDialog
from spectacle_toolbelt.output.editor_handoff import EditorHandoffError, open_in_spectacle
from spectacle_toolbelt.output.files import timestamped_output_path
from spectacle_toolbelt.scroll.stitch_engine import StitchError, stitch_files

SCROLL_MODES = ("manual", "auto-vertical", "auto-horizontal")


class ScrollCaptureError(RuntimeError):
    """Raised when the scrolling capture workflow cannot continue."""


class ScrollDialog(Protocol):
    def choose_scroll_mode(self, default: str) -> str: ...

    def show_message(self, message: str) -> None: ...

    def show_error(self, message: str, details: str | None = None) -> None: ...

    def next_scroll_action(self, frame_count: int, *, mode: str) -> str: ...


CaptureFrame = Callable[[Path], Path]
OpenEditor = Callable[[Path], object]


@dataclass(frozen=True)
class ScrollCaptureRequest:
    output: Path | None = None
    mode: str | None = None
    manual: bool = False
    max_frames: int = 24
    min_confidence: float = 0.92
    min_overlap_rows: int = 8
    open_in_spectacle: bool = True
    force: bool = False
    scroll_delay_seconds: float = 0.8


@dataclass(frozen=True)
class ScrollCapturePlan:
    mode: str
    output: Path
    max_frames: int


@dataclass(frozen=True)
class ScrollCaptureOutcome:
    status: str
    output_path: Path
    frames: int
    debug_json_path: Path
    opened_in_spectacle: bool = False


def plan_scroll_capture(request: ScrollCaptureRequest, *, session_type: str) -> ScrollCapturePlan:
    output = request.output or timestamped_output_path()
    mode = request.mode or ("manual" if request.manual or session_type == "wayland" else "auto-vertical")
    _validate_mode(mode)
    return ScrollCapturePlan(mode=mode, output=output, max_frames=request.max_frames)


def run_scroll_capture(
    request: ScrollCaptureRequest,
    *,
    dialog: ScrollDialog | None = None,
    capture_frame: CaptureFrame = capture_region,
    open_editor: OpenEditor = open_in_spectacle,
) -> ScrollCaptureOutcome:
    """Run a visible scrolling capture session."""

    if request.max_frames < 1:
        raise ScrollCaptureError("max_frames must be at least 1")
    if request.output and request.output.exists() and not request.force:
        raise ScrollCaptureError(f"output already exists: {request.output} (use --force to overwrite)")

    ui = dialog or KdeDialog()
    requested_mode = request.mode or ("manual" if request.manual else "manual")
    if request.mode is None and not request.manual:
        try:
            requested_mode = ui.choose_scroll_mode("manual")
        except DialogError as exc:
            raise ScrollCaptureError(str(exc)) from exc
    _validate_mode(requested_mode)

    mode = _usable_mode(requested_mode, ui)
    output_path = request.output or timestamped_output_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    debug_json_path = output_path.with_suffix(output_path.suffix + ".debug.json")
    if debug_json_path.exists() and not request.force:
        raise ScrollCaptureError(f"debug json already exists: {debug_json_path} (use --force to overwrite)")

    with tempfile.TemporaryDirectory(prefix="spectacle-toolbelt-scroll-") as temp_dir:
        frame_dir = Path(temp_dir)
        frames: list[Path] = []

        ui.show_message(
            "Select the first scroll frame with Spectacle.\n\n"
            "For best stitching, keep the same region for each frame and leave visible overlap."
        )
        frames.append(_capture_numbered_frame(frame_dir, len(frames), capture_frame))

        while len(frames) < request.max_frames:
            action = ui.next_scroll_action(len(frames), mode=mode)
            if action == "cancel":
                raise ScrollCaptureError("scrolling capture cancelled")
            if action == "done":
                break
            if action != "capture-next":
                raise ScrollCaptureError(f"unknown scrolling action: {action}")

            if mode == "manual":
                ui.show_message(
                    "Scroll the content to the next position, then select the same region again."
                )
            else:
                _scroll_for_mode(mode)
                time.sleep(max(0.0, request.scroll_delay_seconds))

            frames.append(_capture_numbered_frame(frame_dir, len(frames), capture_frame))

        direction = "horizontal" if requested_mode == "auto-horizontal" else "vertical"
        try:
            stitch_result = stitch_files(
                frames,
                output_path,
                direction=direction,
                min_confidence=request.min_confidence,
                min_overlap_rows=request.min_overlap_rows,
                max_frames=request.max_frames,
                overwrite=request.force,
            )
        except StitchError as exc:
            raise ScrollCaptureError(str(exc)) from exc

    _write_debug_json(debug_json_path, stitch_result.to_dict(), overwrite=request.force)
    opened = False
    if request.open_in_spectacle:
        try:
            open_editor(output_path)
            opened = True
        except EditorHandoffError as exc:
            ui.show_error("The capture was stitched, but Spectacle did not open.", str(exc))

    return ScrollCaptureOutcome(
        status=stitch_result.status,
        output_path=output_path,
        frames=len(frames),
        debug_json_path=debug_json_path,
        opened_in_spectacle=opened,
    )


def _capture_numbered_frame(frame_dir: Path, index: int, capture_frame: CaptureFrame) -> Path:
    path = frame_dir / f"frame-{index + 1:03d}.png"
    try:
        captured = capture_frame(path)
    except CaptureError as exc:
        raise ScrollCaptureError(str(exc)) from exc
    if not captured.exists():
        raise ScrollCaptureError(f"capture did not create {captured}")
    return captured


def _usable_mode(mode: str, dialog: ScrollDialog) -> str:
    if mode == "manual":
        return mode
    if os.environ.get("XDG_SESSION_TYPE", "").casefold() == "wayland":
        dialog.show_error(
            "Automatic scrolling is not available in this Wayland session.",
            "Toolbelt cannot safely synthesize scroll input for arbitrary Wayland apps. "
            "Manual scrolling capture will be used instead.",
        )
        return "manual"
    if shutil.which("xdotool") is None:
        dialog.show_error(
            "Automatic scrolling needs xdotool on this session.",
            "Manual scrolling capture will be used instead.",
        )
        return "manual"
    return mode


def _scroll_for_mode(mode: str) -> None:
    xdotool = shutil.which("xdotool")
    if xdotool is None:
        raise ScrollCaptureError("xdotool is required for automatic scrolling")

    if mode == "auto-vertical":
        buttons = ("5",)
    elif mode == "auto-horizontal":
        buttons = ("7",)
    else:
        return

    for button in buttons:
        completed = subprocess.run(
            [xdotool, "click", "--repeat", "6", "--delay", "35", button],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        if completed.returncode != 0:
            raise ScrollCaptureError(f"automatic scroll failed: {completed.stderr.strip()}")


def _write_debug_json(path: Path, payload: dict[str, object], *, overwrite: bool) -> None:
    mode = "w" if overwrite else "x"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open(mode, encoding="utf-8") as file:
        json.dump(payload, file, indent=2)


def _validate_mode(mode: str) -> None:
    if mode not in SCROLL_MODES:
        raise ScrollCaptureError(f"unknown scroll mode: {mode}")
