from __future__ import annotations

from unittest.mock import patch

import pytest

from spectacle_toolbelt.desktop.dialogs import DialogError, KdeDialog


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
