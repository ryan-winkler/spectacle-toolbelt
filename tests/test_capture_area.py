from __future__ import annotations

import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from spectacle_toolbelt.capture.area import (
    ScreenRect,
    _X11Monitor,
    _capture_area_kwin,
    _capture_area_x11,
    _x11_scale_factor_from_monitors,
    _x11_virtual_origin_from_xrandr,
)
from spectacle_toolbelt.capture.spectacle_adapter import CaptureError


def test_screen_rect_rejects_empty_geometry() -> None:
    with pytest.raises(ValueError, match="non-zero"):
        ScreenRect(0, 0, 0, 10)


def test_capture_area_x11_uses_fixed_geometry(tmp_path) -> None:
    output = tmp_path / "frame.png"
    rect = ScreenRect(10, 20, 300, 400)

    def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        output.write_bytes(b"png")
        return subprocess.CompletedProcess(command, 0, "", "")

    with (
        patch("spectacle_toolbelt.capture.area._x11_virtual_origin", return_value=(0, 0)),
        patch("spectacle_toolbelt.capture.area._x11_scale_factor", return_value=1.0),
        patch("spectacle_toolbelt.capture.area.shutil.which", return_value="/usr/bin/import"),
        patch("spectacle_toolbelt.capture.area.subprocess.run", side_effect=run) as subprocess_run,
    ):
        assert _capture_area_x11(output, rect) == output

    assert subprocess_run.call_args.args[0] == [
        "/usr/bin/import",
        "-window",
        "root",
        "-crop",
        "300x400+10+20",
        str(output),
    ]


def test_capture_area_x11_translates_negative_monitor_offsets(tmp_path) -> None:
    output = tmp_path / "frame.png"
    rect = ScreenRect(-1920, -120, 300, 400)

    def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        output.write_bytes(b"png")
        return subprocess.CompletedProcess(command, 0, "", "")

    with (
        patch("spectacle_toolbelt.capture.area._x11_virtual_origin", return_value=(-1920, -120)),
        patch("spectacle_toolbelt.capture.area._x11_scale_factor", return_value=1.0),
        patch("spectacle_toolbelt.capture.area.shutil.which", return_value="/usr/bin/import"),
        patch("spectacle_toolbelt.capture.area.subprocess.run", side_effect=run) as subprocess_run,
    ):
        assert _capture_area_x11(output, rect) == output

    assert subprocess_run.call_args.args[0][4] == "300x400+0+0"


def test_capture_area_x11_scales_logical_rect_to_root_pixels(tmp_path) -> None:
    output = tmp_path / "frame.png"
    rect = ScreenRect(10, 20, 300, 400)

    def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        output.write_bytes(b"png")
        return subprocess.CompletedProcess(command, 0, "", "")

    with (
        patch("spectacle_toolbelt.capture.area._x11_virtual_origin", return_value=(0, 0)),
        patch("spectacle_toolbelt.capture.area._x11_scale_factor", return_value=2.0),
        patch("spectacle_toolbelt.capture.area.shutil.which", return_value="/usr/bin/import"),
        patch("spectacle_toolbelt.capture.area.subprocess.run", side_effect=run) as subprocess_run,
    ):
        assert _capture_area_x11(output, rect) == output

    assert subprocess_run.call_args.args[0][4] == "600x800+20+40"


def test_x11_scale_factor_rejects_mixed_scale_selection() -> None:
    monitors = [
        _X11Monitor(ScreenRect(0, 0, 100, 100), 1.0),
        _X11Monitor(ScreenRect(100, 0, 100, 100), 2.0),
    ]

    with pytest.raises(CaptureError, match="different scale factors"):
        _x11_scale_factor_from_monitors(ScreenRect(90, 10, 30, 40), monitors)


def test_x11_scale_factor_allows_monitor_gap_selection_with_same_scale() -> None:
    monitors = [
        _X11Monitor(ScreenRect(0, 0, 100, 100), 1.0),
        _X11Monitor(ScreenRect(120, 0, 100, 100), 1.0),
    ]

    assert _x11_scale_factor_from_monitors(ScreenRect(90, 10, 40, 40), monitors) == 1.0


def test_capture_area_x11_rejects_negative_offsets_without_monitor_origin(tmp_path) -> None:
    with (
        patch("spectacle_toolbelt.capture.area._x11_virtual_origin", return_value=None),
        patch("spectacle_toolbelt.capture.area.shutil.which", return_value="/usr/bin/import"),
    ):
        with pytest.raises(CaptureError, match="negative desktop coordinates"):
            _capture_area_x11(tmp_path / "frame.png", ScreenRect(-100, 20, 300, 400))


def test_capture_area_x11_honors_configured_import_command(tmp_path) -> None:
    output = tmp_path / "frame.png"
    custom_import = tmp_path / "magick-import"

    def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        output.write_bytes(b"png")
        return subprocess.CompletedProcess(command, 0, "", "")

    with (
        patch.dict(
            "spectacle_toolbelt.capture.area.os.environ",
            {"SPECTACLE_TOOLBELT_IMPORT_COMMAND": str(custom_import)},
        ),
        patch("spectacle_toolbelt.capture.area.os.access", return_value=True),
        patch("spectacle_toolbelt.capture.area._x11_virtual_origin", return_value=(0, 0)),
        patch("spectacle_toolbelt.capture.area._x11_scale_factor", return_value=1.0),
        patch("spectacle_toolbelt.capture.area.shutil.which") as which,
        patch("spectacle_toolbelt.capture.area.subprocess.run", side_effect=run) as subprocess_run,
    ):
        assert _capture_area_x11(output, ScreenRect(10, 20, 300, 400)) == output

    assert subprocess_run.call_args.args[0][0] == str(custom_import)
    which.assert_not_called()


def test_x11_virtual_origin_from_xrandr_handles_negative_monitor_layout() -> None:
    xrandr_output = "\n".join(
        [
            "Screen 0: minimum 8 x 8, current 4480 x 1440, maximum 32767 x 32767",
            "DP-1 connected 1920x1080-1920+0 (normal left inverted right x axis y axis) 530mm x 300mm",
            "HDMI-1 connected primary 2560x1440+0-120 (normal left inverted right x axis y axis) 600mm x 340mm",
        ]
    )

    with (
        patch("spectacle_toolbelt.capture.area.shutil.which", return_value="/usr/bin/xrandr"),
        patch(
            "spectacle_toolbelt.capture.area.subprocess.run",
            return_value=subprocess.CompletedProcess(["xrandr", "--query"], 0, xrandr_output, ""),
        ),
    ):
        assert _x11_virtual_origin_from_xrandr() == (-1920, -120)


def test_capture_area_kwin_wraps_bus_lookup_errors(tmp_path) -> None:
    class FakeBus:
        def get_object(self, _service: str, _path: str) -> object:
            raise RuntimeError("service missing")

    fake_dbus = SimpleNamespace(SessionBus=lambda: FakeBus())

    with patch.dict(sys.modules, {"dbus": fake_dbus}):
        with pytest.raises(CaptureError, match="KWin fixed-region capture failed"):
            _capture_area_kwin(tmp_path / "frame.png", ScreenRect(1, 2, 3, 4))
