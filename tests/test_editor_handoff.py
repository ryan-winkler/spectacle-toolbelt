from __future__ import annotations

from unittest.mock import patch

import pytest

from spectacle_toolbelt.output.editor_handoff import (
    EditorHandoffError,
    build_edit_existing_command,
    open_in_spectacle,
)


def test_build_edit_existing_command_defaults_to_new_instance(tmp_path) -> None:
    image = tmp_path / "capture.png"

    command = build_edit_existing_command(image)

    assert command.argv == ("spectacle", "--new-instance", "--edit-existing", str(image))


def test_open_in_spectacle_rejects_missing_file(tmp_path) -> None:
    with pytest.raises(EditorHandoffError, match="image does not exist"):
        open_in_spectacle(tmp_path / "missing.png")


def test_open_in_spectacle_runs_spectacle_for_existing_file(tmp_path) -> None:
    image = tmp_path / "capture.png"
    image.write_bytes(b"png-ish")

    with (
        patch("spectacle_toolbelt.output.editor_handoff.shutil.which", return_value="/usr/bin/spectacle"),
        patch("spectacle_toolbelt.output.editor_handoff.subprocess.Popen") as popen,
    ):
        command = open_in_spectacle(image)

    assert command.argv == ("spectacle", "--new-instance", "--edit-existing", str(image))
    popen.assert_called_once_with(command.argv, start_new_session=True)
