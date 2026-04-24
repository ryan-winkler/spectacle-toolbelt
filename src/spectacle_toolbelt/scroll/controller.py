"""High-level scrolling capture controller scaffold."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ScrollCaptureRequest:
    output: Path
    manual: bool = False
    max_frames: int = 40


@dataclass(frozen=True)
class ScrollCapturePlan:
    mode: str
    output: Path
    max_frames: int


def plan_scroll_capture(request: ScrollCaptureRequest, *, session_type: str) -> ScrollCapturePlan:
    mode = "manual" if request.manual or session_type == "wayland" else "automatic"
    return ScrollCapturePlan(mode=mode, output=request.output, max_frames=request.max_frames)
