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


def test_guide_command_uses_kde_dialog_when_available(capsys) -> None:
    def which(command: str) -> str | None:
        return "/usr/bin/kdialog" if command == "kdialog" else None

    with (
        patch("spectacle_toolbelt.desktop.guide.shutil.which", side_effect=which),
        patch("spectacle_toolbelt.desktop.guide.subprocess.run") as run,
    ):
        run.return_value.returncode = 0

        exit_code = main(["guide"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""
    assert run.call_args.args[0][0] == "/usr/bin/kdialog"
    assert "Spectacle Toolbelt" in run.call_args.args[0]


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


def test_stitch_command_refuses_existing_debug_json_without_force(tmp_path, capsys) -> None:
    full = _striped_image(4, 8)
    first_path = tmp_path / "frame-001.png"
    second_path = tmp_path / "frame-002.png"
    output_path = tmp_path / "stitched.png"
    debug_path = tmp_path / "stitched.json"
    full.crop((0, 0, 4, 5)).save(first_path)
    full.crop((0, 3, 4, 8)).save(second_path)
    debug_path.write_text("existing", encoding="utf-8")

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
    assert exit_code == 1
    assert "debug json already exists" in captured.err
    assert not output_path.exists()


def test_stitch_command_natural_sort_orders_frames_by_filename(tmp_path, capsys) -> None:
    full = _striped_image(4, 10)
    frame_1 = tmp_path / "frame-1.png"
    frame_2 = tmp_path / "frame-2.png"
    frame_10 = tmp_path / "frame-10.png"
    output_path = tmp_path / "stitched.png"
    full.crop((0, 0, 4, 4)).save(frame_1)
    full.crop((0, 3, 4, 7)).save(frame_2)
    full.crop((0, 6, 4, 10)).save(frame_10)

    exit_code = main(
        [
            "stitch",
            str(frame_10),
            str(frame_2),
            str(frame_1),
            "--natural-sort",
            "--output",
            str(output_path),
            "--min-overlap-rows",
            "1",
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    assert Image.open(output_path).size == full.size


def test_scroll_command_runs_manual_capture_workflow(tmp_path, capsys) -> None:
    output_path = tmp_path / "scroll.png"

    with patch("spectacle_toolbelt.scroll.controller.run_scroll_capture") as run:
        run.return_value.status = "complete"
        run.return_value.output_path = output_path
        run.return_value.frames = 2

        exit_code = main(["scroll", "--manual", "--output", str(output_path), "--no-open-in-spectacle"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert f"complete: wrote {output_path} from 2 frames" in captured.out
    request = run.call_args.args[0]
    assert request.mode == "manual"
    assert request.output == output_path
    assert request.open_in_spectacle is False


def test_web_fullpage_command_captures_url(tmp_path, capsys) -> None:
    output_path = tmp_path / "page.png"

    with patch("spectacle_toolbelt.web.fullpage.capture_fullpage_web") as capture:
        capture.return_value.status = "complete"
        capture.return_value.output_path = output_path
        capture.return_value.url = "https://example.com/"
        capture.return_value.copied_to_clipboard = False

        exit_code = main(
            [
                "web-fullpage",
                "--url",
                "https://example.com/",
                "--output",
                str(output_path),
                "--no-copy",
                "--no-open-in-spectacle",
            ]
        )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert f"complete: wrote {output_path}" in captured.out
    request = capture.call_args.args[0]
    assert request.url == "https://example.com/"
    assert request.output == output_path
    assert request.copy_to_clipboard is False
    assert request.open_in_spectacle is False
