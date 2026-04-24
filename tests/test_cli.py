from __future__ import annotations

import json

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
