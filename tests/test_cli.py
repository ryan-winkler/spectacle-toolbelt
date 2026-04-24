from __future__ import annotations

import json
from unittest.mock import patch

from PIL import Image

from spectacle_toolbelt.cli import main


def _striped_image(width: int, height: int, *, offset: int = 0) -> Image.Image:
    image = Image.new("RGBA", (width, height))
    pixels = image.load()
    for y in range(height):
        value = y + offset
        color = ((value * 31) % 256, (value * 47) % 256, (value * 59) % 256, 255)
        for x in range(width):
            pixels[x, y] = color
    return image


def test_stitch_command_writes_debug_json_parent_directory(tmp_path, capsys) -> None:
    full = _striped_image(4, 8)
    first_path = tmp_path / "frame-001.png"
    second_path = tmp_path / "frame-002.png"
    output_path = tmp_path / "out" / "stitched.png"
    debug_path = tmp_path / "debug" / "nested" / "stitched.json"
    full.crop((0, 0, 4, 5)).save(first_path)
    full.crop((0, 3, 4, 8)).save(second_path)

    exit_code = main(
        [
            "stitch",
            str(first_path),
            str(second_path),
            "--output",
            str(output_path),
            "--debug-json",
            str(debug_path),
            "--min-overlap-rows",
            "1",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "complete: wrote" in captured.out
    assert output_path.exists()
    assert json.loads(debug_path.read_text(encoding="utf-8"))["status"] == "complete"


def test_open_in_spectacle_command_reports_handoff(tmp_path, capsys) -> None:
    image = tmp_path / "capture.png"
    image.write_bytes(b"png-ish")

    with (
        patch("spectacle_toolbelt.output.editor_handoff.shutil.which", return_value="/usr/bin/spectacle"),
        patch("spectacle_toolbelt.output.editor_handoff.subprocess.Popen"),
    ):
        exit_code = main(["open-in-spectacle", str(image)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "opened in Spectacle editor" in captured.out


def test_stitch_command_can_use_default_output_path(tmp_path, capsys) -> None:
    full = _striped_image(4, 8)
    first_path = tmp_path / "frame-001.png"
    second_path = tmp_path / "frame-002.png"
    default_output = tmp_path / "Scrolling Screenshot.png"
    full.crop((0, 0, 4, 5)).save(first_path)
    full.crop((0, 3, 4, 8)).save(second_path)

    with patch("spectacle_toolbelt.output.files.timestamped_output_path", return_value=default_output):
        exit_code = main(
            [
                "stitch",
                str(first_path),
                str(second_path),
                "--min-overlap-rows",
                "1",
            ]
        )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert f"complete: wrote {default_output}" in captured.out
    assert default_output.exists()


def test_stitch_command_keeps_success_when_editor_handoff_error_occurs(tmp_path, capsys) -> None:
    from spectacle_toolbelt.output.editor_handoff import EditorHandoffError

    full = _striped_image(4, 8)
    first_path = tmp_path / "frame-001.png"
    second_path = tmp_path / "frame-002.png"
    output_path = tmp_path / "stitched.png"
    full.crop((0, 0, 4, 5)).save(first_path)
    full.crop((0, 3, 4, 8)).save(second_path)

    with patch(
        "spectacle_toolbelt.output.editor_handoff.open_in_spectacle",
        side_effect=EditorHandoffError("missing spectacle"),
    ):
        exit_code = main(
            [
                "stitch",
                str(first_path),
                str(second_path),
                "--output",
                str(output_path),
                "--open-in-spectacle",
                "--min-overlap-rows",
                "1",
            ]
        )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert f"complete: wrote {output_path}" in captured.out
    assert "editor handoff failed: missing spectacle" in captured.err
    assert output_path.exists()
