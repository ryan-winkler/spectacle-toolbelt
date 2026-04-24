from __future__ import annotations

from spectacle_toolbelt.capture.area import ScreenRect
from spectacle_toolbelt.desktop.region_selector import (
    _MonitorInfo,
    _RegionSelectorWindow,
    _SelectionState,
    _virtual_bounds,
    _x11_mixed_scale_selection_error,
)


def test_selection_state_spans_multiple_monitors() -> None:
    left = ScreenRect(0, 0, 1920, 1080)
    right = ScreenRect(1920, 0, 1920, 1080)
    selection = _SelectionState(_virtual_bounds([left, right]))

    selection.begin(1800, 100)
    selection.update(2100, 420)

    assert selection.rect() == ScreenRect(1800, 100, 300, 320)
    assert selection.draw_rect_for_monitor(left) == (1800.0, 100.0, 300.0, 320.0)
    assert selection.draw_rect_for_monitor(right) == (-120.0, 100.0, 300.0, 320.0)


def test_selection_state_clamps_to_virtual_desktop_bounds() -> None:
    left = ScreenRect(-1920, 0, 1920, 1080)
    primary = ScreenRect(0, 0, 2560, 1440)
    selection = _SelectionState(_virtual_bounds([left, primary]))

    selection.begin(-100, 50)
    selection.update(3200, 2000)

    assert selection.rect() == ScreenRect(-100, 50, 2660, 1390)


def test_x11_mixed_scale_validator_rejects_cross_scale_selection() -> None:
    monitors = [
        _MonitorInfo(ScreenRect(0, 0, 100, 100), 1.0),
        _MonitorInfo(ScreenRect(100, 0, 100, 100), 2.0),
    ]

    assert _x11_mixed_scale_selection_error(ScreenRect(90, 10, 30, 40), monitors) is not None
    assert _x11_mixed_scale_selection_error(ScreenRect(10, 10, 30, 40), monitors) is None


def test_invalid_selection_drag_end_keeps_selector_open() -> None:
    finished: list[ScreenRect | None] = []
    redraws: list[None] = []
    selection = _SelectionState(
        ScreenRect(0, 0, 200, 100),
        validate=lambda _rect: "invalid selection",
    )
    window = _RegionSelectorWindow.__new__(_RegionSelectorWindow)
    window.monitor_rect = ScreenRect(0, 0, 200, 100)
    window.selection = selection
    window.on_redraw = lambda: redraws.append(None)
    window.on_finish = finished.append

    window._drag_begin(object(), 10, 10)
    window._drag_end(object(), 40, 40)

    assert finished == []
    assert redraws


def test_region_selector_cancelled_drag_finishes_selection() -> None:
    finished: list[ScreenRect | None] = []
    window = _RegionSelectorWindow.__new__(_RegionSelectorWindow)
    window.on_finish = finished.append

    window._drag_cancel(object(), object())

    assert finished == [None]
