from __future__ import annotations

from pathlib import Path

from PIL import Image

import pytest

from spectacle_toolbelt.capture.area import ScreenRect
from spectacle_toolbelt.desktop.dialogs import DialogError
from spectacle_toolbelt.scroll.controller import ScrollCaptureError, ScrollCaptureRequest, run_scroll_capture


class FakeDialog:
    def __init__(self) -> None:
        self.next_actions = ["capture-next", "done"]
        self.messages: list[str] = []
        self.avoid_rects: list[ScreenRect | None] = []

    def choose_scroll_mode(self, default: str) -> str:
        return default

    def choose_scroll_direction(self, default: str) -> str:
        return default

    def show_message(self, message: str) -> None:
        self.messages.append(message)

    def show_error(self, message: str, details: str | None = None) -> None:
        self.messages.append(message)

    def next_scroll_action(
        self,
        frame_count: int,
        *,
        mode: str,
        avoid_rect: ScreenRect | None = None,
    ) -> str:
        self.avoid_rects.append(avoid_rect)
        return self.next_actions.pop(0)


def test_manual_scroll_capture_captures_until_done(monkeypatch, tmp_path) -> None:
    full = _striped_image(4, 8)
    captures = [
        full.crop((0, 0, 4, 5)),
        full.crop((0, 3, 4, 8)),
    ]

    selected_regions: list[ScreenRect] = []
    captured_regions: list[ScreenRect] = []
    sleeps: list[float] = []
    events: list[tuple[str, ScreenRect | float]] = []
    rect = ScreenRect(10, 20, 4, 5)

    def record_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        events.append(("sleep", seconds))

    monkeypatch.setattr("spectacle_toolbelt.scroll.controller.time.sleep", record_sleep)

    def select_region() -> ScreenRect:
        selected_regions.append(rect)
        events.append(("select", rect))
        return rect

    def capture_frame(path: Path, region: ScreenRect) -> Path:
        captured_regions.append(region)
        events.append(("capture", region))
        captures.pop(0).save(path)
        return path

    opened: list[Path] = []
    dialog = FakeDialog()
    result = run_scroll_capture(
        ScrollCaptureRequest(
            output=tmp_path / "stitched.png",
            mode="manual",
            open_in_spectacle=True,
            min_overlap_rows=1,
            dialog_settle_seconds=0.25,
        ),
        dialog=dialog,
        select_region=select_region,
        capture_area_frame=capture_frame,
        open_editor=lambda path: opened.append(path),
    )

    assert result.status == "complete"
    assert result.output_path == tmp_path / "stitched.png"
    assert result.frames == 2
    assert result.output_path.exists()
    assert Image.open(result.output_path).size == full.size
    assert opened == [result.output_path]
    assert result.debug_json_path.exists()
    assert selected_regions == [rect]
    assert captured_regions == [rect, rect]
    assert dialog.avoid_rects == [rect, rect]
    assert sleeps == [0.25, 0.25]
    assert events[:3] == [("select", rect), ("sleep", 0.25), ("capture", rect)]


def test_scroll_capture_wraps_mode_picker_cancel(tmp_path) -> None:
    class CancelDialog(FakeDialog):
        def choose_scroll_mode(self, default: str) -> str:
            raise DialogError("scrolling capture cancelled")

    with pytest.raises(ScrollCaptureError, match="cancelled"):
        run_scroll_capture(
            ScrollCaptureRequest(output=tmp_path / "stitched.png"),
            dialog=CancelDialog(),
            select_region=lambda: ScreenRect(0, 0, 4, 4),
            capture_area_frame=lambda path, _region: path,
        )


def test_auto_horizontal_fallback_preserves_horizontal_stitch_direction(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    full = _striped_horizontal_image(8, 4)
    captures = [
        full.crop((0, 0, 5, 4)),
        full.crop((3, 0, 8, 4)),
    ]

    def capture_frame(path: Path, _region: ScreenRect) -> Path:
        captures.pop(0).save(path)
        return path

    result = run_scroll_capture(
        ScrollCaptureRequest(
            output=tmp_path / "stitched.png",
            mode="auto-horizontal",
            open_in_spectacle=False,
            min_overlap_rows=1,
            dialog_settle_seconds=0,
        ),
        dialog=FakeDialog(),
        select_region=lambda: ScreenRect(10, 20, 5, 4),
        capture_area_frame=capture_frame,
    )

    assert result.status == "complete"
    assert Image.open(result.output_path).size == full.size
    assert Image.open(result.output_path).tobytes() == full.tobytes()


def test_manual_scroll_capture_can_stitch_horizontally(tmp_path) -> None:
    full = _striped_horizontal_image(8, 4)
    captures = [
        full.crop((0, 0, 5, 4)),
        full.crop((3, 0, 8, 4)),
    ]

    def capture_frame(path: Path, _region: ScreenRect) -> Path:
        captures.pop(0).save(path)
        return path

    result = run_scroll_capture(
        ScrollCaptureRequest(
            output=tmp_path / "stitched.png",
            mode="manual",
            direction="horizontal",
            open_in_spectacle=False,
            min_overlap_rows=1,
            dialog_settle_seconds=0,
        ),
        dialog=FakeDialog(),
        select_region=lambda: ScreenRect(10, 20, 5, 4),
        capture_area_frame=capture_frame,
    )

    assert result.status == "complete"
    assert Image.open(result.output_path).size == full.size
    assert Image.open(result.output_path).tobytes() == full.tobytes()


def test_manual_scroll_capture_prompts_for_direction(tmp_path) -> None:
    class HorizontalDialog(FakeDialog):
        def choose_scroll_direction(self, default: str) -> str:
            return "horizontal"

    full = _striped_horizontal_image(8, 4)
    captures = [
        full.crop((0, 0, 5, 4)),
        full.crop((3, 0, 8, 4)),
    ]

    def capture_frame(path: Path, _region: ScreenRect) -> Path:
        captures.pop(0).save(path)
        return path

    result = run_scroll_capture(
        ScrollCaptureRequest(
            output=tmp_path / "stitched.png",
            mode="manual",
            open_in_spectacle=False,
            min_overlap_rows=1,
            dialog_settle_seconds=0,
        ),
        dialog=HorizontalDialog(),
        select_region=lambda: ScreenRect(10, 20, 5, 4),
        capture_area_frame=capture_frame,
    )

    assert result.status == "complete"
    assert Image.open(result.output_path).size == full.size


def _striped_image(width: int, height: int, *, offset: int = 0) -> Image.Image:
    image = Image.new("RGBA", (width, height))
    pixels = image.load()
    for y in range(height):
        value = y + offset
        color = ((value * 31) % 256, (value * 47) % 256, (value * 59) % 256, 255)
        for x in range(width):
            pixels[x, y] = color
    return image


def _striped_horizontal_image(width: int, height: int, *, offset: int = 0) -> Image.Image:
    image = Image.new("RGBA", (width, height))
    pixels = image.load()
    for x in range(width):
        value = x + offset
        color = ((value * 31) % 256, (value * 47) % 256, (value * 59) % 256, 255)
        for y in range(height):
            pixels[x, y] = color
    return image
