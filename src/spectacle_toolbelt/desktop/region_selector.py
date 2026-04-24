"""GTK region selector used before fixed-area scrolling capture."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

from spectacle_toolbelt.capture.area import ScreenRect
from spectacle_toolbelt.capture.spectacle_adapter import CaptureError


def select_screen_region() -> ScreenRect:
    """Let the user drag a desktop rectangle once and return workspace geometry."""

    try:
        import gi

        gi.require_version("Gtk", "4.0")
        gi.require_version("Gdk", "4.0")
        from gi.repository import Gdk, Gtk
    except (ImportError, ValueError) as exc:
        raise CaptureError("GTK 4/PyGObject is required for scrolling region selection") from exc

    Gtk.init()
    display = Gdk.Display.get_default()
    if display is None:
        raise CaptureError("could not open a GTK display for region selection")

    result = _SelectorResult()
    app = Gtk.Application(application_id="io.github.ryanwinkler.spectacletoolbelt.RegionSelector")

    def on_activate(application: Gtk.Application) -> None:
        monitors = display.get_monitors()
        if monitors.get_n_items() < 1:
            result.error = "no monitors are available for region selection"
            application.quit()
            return

        monitor_infos: list[_MonitorInfo] = []
        for index in range(monitors.get_n_items()):
            monitor = monitors.get_item(index)
            if monitor is None:
                continue
            geometry = monitor.get_geometry()
            monitor_infos.append(
                _MonitorInfo(
                    rect=ScreenRect(int(geometry.x), int(geometry.y), int(geometry.width), int(geometry.height)),
                    scale=float(monitor.get_scale_factor()),
                )
            )
        if not monitor_infos:
            result.error = "no monitors are available for region selection"
            application.quit()
            return

        monitor_rects = [monitor.rect for monitor in monitor_infos]
        selection_validator = None
        if os.environ.get("XDG_SESSION_TYPE", "").casefold() != "wayland":
            selection_validator = lambda rect: _x11_mixed_scale_selection_error(rect, monitor_infos)
        selection = _SelectionState(_virtual_bounds(monitor_rects), validate=selection_validator)
        windows: list[_RegionSelectorWindow] = []

        def finish(rect: ScreenRect | None) -> None:
            if rect is not None:
                result.rect = rect
            else:
                result.cancelled = True
            for window in windows:
                window.close()
            application.quit()

        def redraw_all() -> None:
            for window in windows:
                window.redraw()

        for index in range(monitors.get_n_items()):
            monitor = monitors.get_item(index)
            if monitor is None:
                continue
            geometry = monitor.get_geometry()
            monitor_rect = ScreenRect(int(geometry.x), int(geometry.y), int(geometry.width), int(geometry.height))
            window = _RegionSelectorWindow(
                application,
                monitor_rect=monitor_rect,
                selection=selection,
                on_redraw=redraw_all,
                on_finish=finish,
            )
            windows.append(window)
            window.fullscreen_on_monitor(monitor)
            window.present()

    app.connect("activate", on_activate)
    app.run([])

    if result.rect is not None:
        return result.rect
    if result.error:
        raise CaptureError(result.error)
    raise CaptureError("scrolling region selection cancelled")


@dataclass
class _SelectorResult:
    rect: ScreenRect | None = None
    error: str | None = None
    cancelled: bool = False


@dataclass(frozen=True)
class _MonitorInfo:
    rect: ScreenRect
    scale: float


def _virtual_bounds(monitors: list[ScreenRect]) -> ScreenRect:
    min_x = min(monitor.x for monitor in monitors)
    min_y = min(monitor.y for monitor in monitors)
    max_x = max(monitor.x + monitor.width for monitor in monitors)
    max_y = max(monitor.y + monitor.height for monitor in monitors)
    return ScreenRect(min_x, min_y, max_x - min_x, max_y - min_y)


@dataclass
class _SelectionState:
    bounds: ScreenRect
    validate: Callable[[ScreenRect], str | None] | None = None
    start: tuple[float, float] | None = None
    current: tuple[float, float] | None = None

    def begin(self, x: float, y: float) -> None:
        point = self._clamp_point(x, y)
        self.start = point
        self.current = point

    def update(self, x: float, y: float) -> None:
        if self.start is None:
            return
        self.current = self._clamp_point(x, y)

    def rect(self) -> ScreenRect | None:
        if self.start is None or self.current is None:
            return None
        start_x, start_y = self.start
        current_x, current_y = self.current
        x = int(round(min(start_x, current_x)))
        y = int(round(min(start_y, current_y)))
        width = int(round(abs(current_x - start_x)))
        height = int(round(abs(current_y - start_y)))
        if width < 4 or height < 4:
            return None
        return ScreenRect(x, y, width, height)

    def draw_rect_for_monitor(self, monitor: ScreenRect) -> tuple[float, float, float, float] | None:
        rect = self.rect()
        if rect is None:
            return None
        return (
            float(rect.x - monitor.x),
            float(rect.y - monitor.y),
            float(rect.width),
            float(rect.height),
        )

    def validation_error(self) -> str | None:
        rect = self.rect()
        if rect is None or self.validate is None:
            return None
        return self.validate(rect)

    def _clamp_point(self, x: float, y: float) -> tuple[float, float]:
        max_x = self.bounds.x + self.bounds.width
        max_y = self.bounds.y + self.bounds.height
        return (
            min(max(x, self.bounds.x), max_x),
            min(max(y, self.bounds.y), max_y),
        )


class _RegionSelectorWindow:
    def __init__(
        self,
        application: object,
        *,
        monitor_rect: ScreenRect,
        selection: _SelectionState,
        on_redraw: Callable[[], None],
        on_finish: Callable[[ScreenRect | None], None],
    ) -> None:
        from gi.repository import Gdk, Gtk

        self.monitor_rect = monitor_rect
        self.selection = selection
        self.on_redraw = on_redraw
        self.on_finish = on_finish
        self.start: tuple[float, float] | None = None

        self.window = Gtk.ApplicationWindow(application=application)
        self.window.set_title("Spectacle Toolbelt Region Selector")
        self.window.set_decorated(False)
        self.window.set_modal(False)
        self.window.set_opacity(0.88)

        self.area = Gtk.DrawingArea()
        self.area.set_draw_func(self._draw)
        self.window.set_child(self.area)

        drag = Gtk.GestureDrag.new()
        drag.connect("drag-begin", self._drag_begin)
        drag.connect("drag-update", self._drag_update)
        drag.connect("drag-end", self._drag_end)
        drag.connect("cancel", self._drag_cancel)
        self.area.add_controller(drag)

        keys = Gtk.EventControllerKey.new()
        keys.connect("key-pressed", self._key_pressed)
        self.window.add_controller(keys)

        self.Gdk = Gdk

    def fullscreen_on_monitor(self, monitor: object) -> None:
        self.window.fullscreen_on_monitor(monitor)

    def present(self) -> None:
        self.window.present()

    def close(self) -> None:
        self.window.close()

    def redraw(self) -> None:
        self.area.queue_draw()

    def _drag_begin(self, _gesture: object, start_x: float, start_y: float) -> None:
        self.start = (start_x, start_y)
        self.selection.begin(self.monitor_rect.x + start_x, self.monitor_rect.y + start_y)
        self.on_redraw()

    def _drag_update(self, _gesture: object, offset_x: float, offset_y: float) -> None:
        if self.start is None:
            return
        start_x, start_y = self.start
        self.selection.update(
            self.monitor_rect.x + start_x + offset_x,
            self.monitor_rect.y + start_y + offset_y,
        )
        self.on_redraw()

    def _drag_end(self, _gesture: object, offset_x: float, offset_y: float) -> None:
        if self.start is None:
            self.on_finish(None)
            return
        start_x, start_y = self.start
        self.selection.update(
            self.monitor_rect.x + start_x + offset_x,
            self.monitor_rect.y + start_y + offset_y,
        )
        if self.selection.validation_error() is not None:
            self.on_redraw()
            return
        self.on_finish(self.selection.rect())

    def _drag_cancel(self, _gesture: object, _sequence: object | None = None) -> None:
        self.on_finish(None)

    def _key_pressed(self, _controller: object, keyval: int, _keycode: int, _state: int) -> bool:
        if keyval == self.Gdk.KEY_Escape:
            self.on_finish(None)
            return True
        return False

    def _draw(self, _area: object, cr: object, width: int, height: int) -> None:
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.45)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        validation_error = self.selection.validation_error()
        if validation_error:
            cr.set_source_rgba(1.0, 0.24, 0.16, 1.0)
        else:
            cr.set_source_rgba(1.0, 0.92, 0.0, 1.0)
        cr.select_font_face("Sans")
        cr.set_font_size(18)
        cr.move_to(24, 38)
        cr.show_text(validation_error or "Drag the scrolling viewport once. Esc cancels.")

        rect = self.selection.draw_rect_for_monitor(self.monitor_rect)
        if rect is None:
            return

        x, y, rect_width, rect_height = rect

        if validation_error:
            cr.set_source_rgba(1.0, 0.24, 0.16, 0.18)
        else:
            cr.set_source_rgba(1.0, 0.92, 0.0, 0.18)
        cr.rectangle(x, y, rect_width, rect_height)
        cr.fill()
        if validation_error:
            cr.set_source_rgba(1.0, 0.24, 0.16, 1.0)
        else:
            cr.set_source_rgba(1.0, 0.92, 0.0, 1.0)
        cr.set_line_width(3)
        cr.rectangle(x, y, rect_width, rect_height)
        cr.stroke()


def _x11_mixed_scale_selection_error(rect: ScreenRect, monitors: list[_MonitorInfo]) -> str | None:
    scales = {
        monitor.scale
        for monitor in monitors
        if _rects_overlap(rect, monitor.rect)
    }
    if len(scales) <= 1:
        return None
    return "X11 mixed-scale monitor spans are not supported. Select one scale group."


def _rects_overlap(first: ScreenRect, second: ScreenRect) -> bool:
    return not (
        first.x + first.width <= second.x
        or second.x + second.width <= first.x
        or first.y + first.height <= second.y
        or second.y + second.height <= first.y
    )
