from __future__ import annotations

from unittest.mock import patch

import pytest

from spectacle_toolbelt.capture.area import ScreenRect
from spectacle_toolbelt.desktop.dialogs import DialogError, KdeDialog, _dialog_geometry_avoiding


class NoTerminalStdin:
    def isatty(self) -> bool:
        return False


def test_choose_scroll_mode_requires_kdialog_without_terminal_stdin() -> None:
    with (
        patch("spectacle_toolbelt.desktop.dialogs.shutil.which", return_value=None),
        patch("spectacle_toolbelt.desktop.dialogs.sys.stdin", NoTerminalStdin()),
    ):
        dialog = KdeDialog()

        with pytest.raises(DialogError, match="kdialog is required"):
            dialog.choose_scroll_mode()


def test_prompt_url_requires_kdialog_without_terminal_stdin() -> None:
    with (
        patch("spectacle_toolbelt.desktop.dialogs.shutil.which", return_value=None),
        patch("spectacle_toolbelt.desktop.dialogs.sys.stdin", NoTerminalStdin()),
    ):
        dialog = KdeDialog()

        with pytest.raises(DialogError, match="kdialog is required"):
            dialog.prompt_url()


def test_choose_scroll_direction_requires_kdialog_without_terminal_stdin() -> None:
    with (
        patch("spectacle_toolbelt.desktop.dialogs.shutil.which", return_value=None),
        patch("spectacle_toolbelt.desktop.dialogs.sys.stdin", NoTerminalStdin()),
    ):
        dialog = KdeDialog()

        with pytest.raises(DialogError, match="kdialog is required"):
            dialog.choose_scroll_direction()


def test_next_scroll_action_requires_kdialog_without_terminal_stdin() -> None:
    with (
        patch("spectacle_toolbelt.desktop.dialogs.shutil.which", return_value=None),
        patch("spectacle_toolbelt.desktop.dialogs.sys.stdin", NoTerminalStdin()),
    ):
        dialog = KdeDialog()

        with pytest.raises(DialogError, match="kdialog is required"):
            dialog.next_scroll_action(1, mode="manual")


def test_next_action_geometry_avoids_selected_capture_rect() -> None:
    with patch(
        "spectacle_toolbelt.desktop.dialogs._desktop_monitor_rects",
        return_value=[ScreenRect(0, 0, 1920, 1080)],
    ):
        assert _dialog_geometry_avoiding(ScreenRect(0, 0, 900, 500)) == "560x220+1336+24"


def test_next_action_geometry_uses_real_monitors_not_virtual_gap() -> None:
    with patch(
        "spectacle_toolbelt.desktop.dialogs._desktop_monitor_rects",
        return_value=[
            ScreenRect(0, 300, 1000, 700),
            ScreenRect(1000, 0, 1000, 700),
        ],
    ):
        assert _dialog_geometry_avoiding(ScreenRect(1000, 0, 600, 500)) == "560x220+24+324"
