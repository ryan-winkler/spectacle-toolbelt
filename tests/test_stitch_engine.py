from __future__ import annotations

import json

import pytest
from PIL import Image

from spectacle_toolbelt.scroll.stitch_engine import (
    StitchError,
    JoinDiagnostic,
    StitchResult,
    stitch_files,
    stitch_images,
)


def _striped_image(width: int, height: int, *, offset: int = 0) -> Image.Image:
    image = Image.new("RGBA", (width, height))
    pixels = image.load()
    for y in range(height):
        value = y + offset
        color = ((value * 31) % 256, (value * 47) % 256, (value * 59) % 256, 255)
        for x in range(width):
            pixels[x, y] = color
    return image


def test_stitch_images_exact_overlap_success() -> None:
    full = _striped_image(5, 9)
    first = full.crop((0, 0, 5, 6))
    second = full.crop((0, 3, 5, 9))

    result = stitch_images([first, second], min_overlap_rows=1)

    assert result.status == "complete"
    assert result.frames == 2
    assert result.stitched_frames == 2
    assert result.image.size == full.size
    assert result.image.tobytes() == full.tobytes()
    assert result.diagnostics == (
        JoinDiagnostic(
            frame_index=1,
            status="joined",
            overlap_rows=3,
            confidence=1.0,
            appended_rows=3,
            message="exact vertical overlap found",
        ),
    )


def test_stitch_images_identical_frame_detects_end() -> None:
    frame = _striped_image(4, 6)

    result = stitch_images([frame, frame.copy()], min_overlap_rows=1)

    assert result.status == "complete"
    assert result.end_detected is True
    assert result.frames == 2
    assert result.stitched_frames == 1
    assert result.image.size == frame.size
    assert result.diagnostics[0].status == "duplicate-end"
    assert result.diagnostics[0].overlap_rows == frame.height
    assert result.diagnostics[0].appended_rows == 0


def test_stitch_images_no_overlap_returns_partial_when_allowed() -> None:
    first = Image.new("RGBA", (3, 4), (255, 0, 0, 255))
    second = Image.new("RGBA", (3, 4), (0, 0, 255, 255))

    result = stitch_images([first, second], min_overlap_rows=1, allow_partial=True)

    assert result.status == "partial"
    assert result.image.size == (3, 8)
    assert result.diagnostics[0].status == "no-overlap"
    assert result.diagnostics[0].overlap_rows == 0
    assert result.diagnostics[0].confidence == 0.0
    assert result.diagnostics[0].appended_rows == second.height


def test_stitch_images_no_overlap_fails_when_partial_is_disabled() -> None:
    first = Image.new("RGBA", (3, 4), (255, 0, 0, 255))
    second = Image.new("RGBA", (3, 4), (0, 0, 255, 255))

    with pytest.raises(StitchError, match="could not find a reliable overlap"):
        stitch_images([first, second], min_overlap_rows=1, allow_partial=False)


def test_stitch_images_width_mismatch_fails() -> None:
    first = Image.new("RGBA", (3, 4), (255, 0, 0, 255))
    second = Image.new("RGBA", (4, 4), (255, 0, 0, 255))

    with pytest.raises(StitchError, match="width"):
        stitch_images([first, second])


def test_stitch_files_writes_output_and_result_serializes(tmp_path) -> None:
    full = _striped_image(4, 8)
    first = full.crop((0, 0, 4, 5))
    second = full.crop((0, 3, 4, 8))
    first_path = tmp_path / "first.png"
    second_path = tmp_path / "second.png"
    output_path = tmp_path / "stitched.png"
    first.save(first_path)
    second.save(second_path)

    result = stitch_files(
        [first_path, second_path],
        output_path,
        min_overlap_rows=1,
    )

    serialized = result.to_dict()
    assert output_path.exists()
    assert serialized["outputPath"] == str(output_path)
    assert serialized["status"] == "complete"
    assert "image" not in serialized
    assert serialized["diagnostics"] == [result.diagnostics[0].to_dict()]
    json.dumps(serialized)
    assert isinstance(result, StitchResult)


def test_stitch_files_refuses_existing_output_without_force(tmp_path) -> None:
    frame_path = tmp_path / "frame.png"
    output_path = tmp_path / "stitched.png"
    _striped_image(4, 4).save(frame_path)
    output_path.write_bytes(b"existing")

    with pytest.raises(StitchError, match="output already exists"):
        stitch_files([frame_path], output_path)


def test_stitch_files_can_force_overwrite_existing_output(tmp_path) -> None:
    frame_path = tmp_path / "frame.png"
    output_path = tmp_path / "stitched.png"
    _striped_image(4, 4).save(frame_path)
    output_path.write_bytes(b"existing")

    result = stitch_files([frame_path], output_path, overwrite=True)

    assert result.output_path == str(output_path)
    assert output_path.read_bytes() != b"existing"


def test_stitch_images_enforces_frame_count_limit() -> None:
    frames = [_striped_image(2, 2), _striped_image(2, 2), _striped_image(2, 2)]

    with pytest.raises(StitchError, match="too many frames"):
        stitch_images(frames, max_frames=2)


def test_stitch_images_enforces_output_pixel_limit() -> None:
    first = Image.new("RGBA", (3, 4), (255, 0, 0, 255))
    second = Image.new("RGBA", (3, 4), (0, 0, 255, 255))

    with pytest.raises(StitchError, match="stitched output is too large"):
        stitch_images([first, second], min_overlap_rows=1, max_output_pixels=20)
