"""Scrolling screenshot stitching for pre-captured frames."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Iterable

from PIL import Image, UnidentifiedImageError

DEFAULT_MAX_FRAMES = 24
DEFAULT_MAX_FRAME_PIXELS = 50_000_000
DEFAULT_MAX_TOTAL_INPUT_PIXELS = 180_000_000
DEFAULT_MAX_OUTPUT_PIXELS = 180_000_000


class StitchError(Exception):
    """Raised when frames cannot be stitched safely."""


@dataclass(frozen=True)
class JoinDiagnostic:
    """Diagnostic data for one frame-to-frame join."""

    frame_index: int
    status: str
    overlap_rows: int
    confidence: float
    appended_rows: int
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "frameIndex": self.frame_index,
            "status": self.status,
            "overlapRows": self.overlap_rows,
            "confidence": round(self.confidence, 6),
            "appendedRows": self.appended_rows,
            "message": self.message,
        }


@dataclass(frozen=True)
class StitchResult:
    """Stitched image plus serializable result metadata."""

    image: Image.Image = field(repr=False, compare=False)
    status: str
    frames: int
    stitched_frames: int
    width: int
    height: int
    diagnostics: tuple[JoinDiagnostic, ...]
    output_path: str | None = None
    end_detected: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "frames": self.frames,
            "stitchedFrames": self.stitched_frames,
            "width": self.width,
            "height": self.height,
            "outputPath": self.output_path,
            "endDetected": self.end_detected,
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
        }


@dataclass(frozen=True)
class _JoinMatch:
    status: str
    overlap_rows: int
    confidence: float
    message: str


def stitch_images(
    images: Iterable[Image.Image],
    *,
    direction: str = "vertical",
    min_confidence: float = 0.92,
    min_overlap_rows: int = 8,
    allow_partial: bool = True,
    stop_on_duplicate: bool = True,
    max_frames: int = DEFAULT_MAX_FRAMES,
    max_frame_pixels: int = DEFAULT_MAX_FRAME_PIXELS,
    max_total_input_pixels: int = DEFAULT_MAX_TOTAL_INPUT_PIXELS,
    max_output_pixels: int = DEFAULT_MAX_OUTPUT_PIXELS,
) -> StitchResult:
    """Stitch screenshots captured in scroll order."""

    if direction not in {"vertical", "horizontal"}:
        raise StitchError("direction must be vertical or horizontal")

    frames = [_normalize_image(image) for image in images]
    if direction == "horizontal":
        frames = [_transpose_for_horizontal(frame) for frame in frames]

    if not frames:
        raise StitchError("at least one frame is required")
    _validate_limits(
        frames,
        max_frames=max_frames,
        max_frame_pixels=max_frame_pixels,
        max_total_input_pixels=max_total_input_pixels,
    )
    if not 0.0 <= min_confidence <= 1.0:
        raise StitchError("min_confidence must be between 0.0 and 1.0")
    if min_overlap_rows < 1:
        raise StitchError("min_overlap_rows must be at least 1")
    if max_output_pixels < 1:
        raise StitchError("max_output_pixels must be at least 1")

    width = frames[0].width
    for index, frame in enumerate(frames):
        if frame.width != width:
            raise StitchError(
                f"frame {index} width {frame.width} does not match first frame width {width}"
            )

    stitched = frames[0].copy()
    _ensure_output_within_limit(stitched, max_output_pixels=max_output_pixels)
    diagnostics: list[JoinDiagnostic] = []
    status = "complete"
    stitched_frames = 1
    end_detected = False

    for frame_index, frame in enumerate(frames[1:], start=1):
        match = _find_join(
            stitched,
            frame,
            min_overlap_rows=min_overlap_rows,
            min_confidence=min_confidence,
        )

        if match.status == "duplicate-end":
            diagnostics.append(
                JoinDiagnostic(
                    frame_index=frame_index,
                    status=match.status,
                    overlap_rows=match.overlap_rows,
                    confidence=match.confidence,
                    appended_rows=0,
                    message=match.message,
                )
            )
            end_detected = True
            if stop_on_duplicate:
                break
            continue

        if match.status == "joined":
            appended_rows = frame.height - match.overlap_rows
            stitched = _append_frame(stitched, frame, crop_top=match.overlap_rows)
            _ensure_output_within_limit(stitched, max_output_pixels=max_output_pixels)
            stitched_frames += 1
            diagnostics.append(
                JoinDiagnostic(
                    frame_index=frame_index,
                    status=match.status,
                    overlap_rows=match.overlap_rows,
                    confidence=match.confidence,
                    appended_rows=appended_rows,
                    message=match.message,
                )
            )
            continue

        if not allow_partial:
            raise StitchError(
                f"could not find a reliable overlap before frame {frame_index} "
                f"(best confidence {match.confidence:.3f})"
            )

        stitched = _append_frame(stitched, frame, crop_top=0)
        _ensure_output_within_limit(stitched, max_output_pixels=max_output_pixels)
        stitched_frames += 1
        status = "partial"
        diagnostics.append(
            JoinDiagnostic(
                frame_index=frame_index,
                status="no-overlap",
                overlap_rows=match.overlap_rows,
                confidence=match.confidence,
                appended_rows=frame.height,
                message=match.message,
            )
        )

    if direction == "horizontal":
        stitched = _transpose_for_horizontal(stitched)
        diagnostics = [_horizontal_diagnostic(diagnostic) for diagnostic in diagnostics]

    return StitchResult(
        image=stitched,
        status=status,
        frames=len(frames),
        stitched_frames=stitched_frames,
        width=stitched.width,
        height=stitched.height,
        diagnostics=tuple(diagnostics),
        end_detected=end_detected,
    )


def stitch_files(
    frame_paths: Iterable[str | Path],
    output_path: str | Path,
    *,
    direction: str = "vertical",
    min_confidence: float = 0.92,
    min_overlap_rows: int = 8,
    allow_partial: bool = True,
    overwrite: bool = False,
    max_frames: int = DEFAULT_MAX_FRAMES,
    max_frame_pixels: int = DEFAULT_MAX_FRAME_PIXELS,
    max_total_input_pixels: int = DEFAULT_MAX_TOTAL_INPUT_PIXELS,
    max_output_pixels: int = DEFAULT_MAX_OUTPUT_PIXELS,
) -> StitchResult:
    """Load frame files, stitch them, and write the resulting image."""

    paths = [Path(path) for path in frame_paths]
    if len(paths) > max_frames:
        raise StitchError(f"too many frames: {len(paths)} exceeds max_frames {max_frames}")

    output = Path(output_path)
    if output.exists() and not overwrite:
        raise StitchError(f"output already exists: {output} (use --force to overwrite)")

    frames: list[Image.Image] = []
    total_pixels = 0
    for path in paths:
        try:
            with Image.open(path) as image:
                frame_pixels = _pixel_count(image)
                if frame_pixels > max_frame_pixels:
                    raise StitchError(
                        f"frame is too large: {path} has {frame_pixels} pixels, "
                        f"limit is {max_frame_pixels}"
                    )
                total_pixels += frame_pixels
                if total_pixels > max_total_input_pixels:
                    raise StitchError(
                        f"input set is too large: {total_pixels} pixels, "
                        f"limit is {max_total_input_pixels}"
                    )
                frames.append(image.copy())
        except FileNotFoundError as exc:
            raise StitchError(f"frame does not exist: {path}") from exc
        except (OSError, UnidentifiedImageError) as exc:
            raise StitchError(f"could not read frame image: {path}") from exc

    result = stitch_images(
        frames,
        direction=direction,
        min_confidence=min_confidence,
        min_overlap_rows=min_overlap_rows,
        allow_partial=allow_partial,
        max_frames=max_frames,
        max_frame_pixels=max_frame_pixels,
        max_total_input_pixels=max_total_input_pixels,
        max_output_pixels=max_output_pixels,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    _save_image(result.image, output, overwrite=overwrite)
    return replace(result, output_path=str(output))


def _normalize_image(image: Image.Image) -> Image.Image:
    if image.width < 1 or image.height < 1:
        raise StitchError("frames must have non-zero dimensions")
    if image.mode != "RGBA":
        return image.convert("RGBA")
    return image.copy()


def _transpose_for_horizontal(image: Image.Image) -> Image.Image:
    return image.transpose(Image.Transpose.TRANSPOSE)


def _horizontal_diagnostic(diagnostic: JoinDiagnostic) -> JoinDiagnostic:
    return replace(diagnostic, message=diagnostic.message.replace("vertical", "horizontal"))


def _validate_limits(
    frames: list[Image.Image],
    *,
    max_frames: int,
    max_frame_pixels: int,
    max_total_input_pixels: int,
) -> None:
    if max_frames < 1:
        raise StitchError("max_frames must be at least 1")
    if max_frame_pixels < 1:
        raise StitchError("max_frame_pixels must be at least 1")
    if max_total_input_pixels < 1:
        raise StitchError("max_total_input_pixels must be at least 1")
    if len(frames) > max_frames:
        raise StitchError(f"too many frames: {len(frames)} exceeds max_frames {max_frames}")

    total_pixels = 0
    for index, frame in enumerate(frames):
        frame_pixels = _pixel_count(frame)
        if frame_pixels > max_frame_pixels:
            raise StitchError(
                f"frame {index} is too large: {frame_pixels} pixels, limit is {max_frame_pixels}"
            )
        total_pixels += frame_pixels
        if total_pixels > max_total_input_pixels:
            raise StitchError(
                f"input set is too large: {total_pixels} pixels, limit is {max_total_input_pixels}"
            )


def _pixel_count(image: Image.Image) -> int:
    return image.width * image.height


def _ensure_output_within_limit(image: Image.Image, *, max_output_pixels: int) -> None:
    output_pixels = _pixel_count(image)
    if output_pixels > max_output_pixels:
        raise StitchError(
            f"stitched output is too large: {output_pixels} pixels, limit is {max_output_pixels}"
        )


def _save_image(image: Image.Image, output: Path, *, overwrite: bool) -> None:
    if overwrite:
        image.save(output)
        return

    try:
        with output.open("xb") as file:
            image.save(file, format=_output_format(output))
    except FileExistsError as exc:
        raise StitchError(f"output already exists: {output} (use --force to overwrite)") from exc


def _output_format(output: Path) -> str:
    suffix = output.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "JPEG"
    if suffix == ".webp":
        return "WEBP"
    return "PNG"


def _find_join(
    previous: Image.Image,
    current: Image.Image,
    *,
    min_overlap_rows: int,
    min_confidence: float,
) -> _JoinMatch:
    previous_rows = _row_bytes(previous)
    current_rows = _row_bytes(current)

    if previous.height >= current.height and previous_rows[-current.height :] == current_rows:
        return _JoinMatch(
            status="duplicate-end",
            overlap_rows=current.height,
            confidence=1.0,
            message="frame is identical to the current stitch tail; treating it as scroll end",
        )

    max_overlap = min(previous.height, current.height)
    effective_min_overlap = min(min_overlap_rows, max_overlap)

    for overlap_rows in range(max_overlap, effective_min_overlap - 1, -1):
        if previous_rows[-overlap_rows:] == current_rows[:overlap_rows]:
            return _JoinMatch(
                status="joined",
                overlap_rows=overlap_rows,
                confidence=1.0,
                message="exact vertical overlap found",
            )

    best_overlap, best_confidence = _best_sampled_overlap(
        previous,
        current,
        min_overlap_rows=effective_min_overlap,
        max_overlap_rows=max_overlap,
    )
    if best_confidence >= min_confidence:
        return _JoinMatch(
            status="joined",
            overlap_rows=best_overlap,
            confidence=best_confidence,
            message="sampled vertical overlap met confidence threshold",
        )

    return _JoinMatch(
        status="no-overlap",
        overlap_rows=best_overlap,
        confidence=best_confidence,
        message="no overlap met confidence threshold",
    )


def _row_bytes(image: Image.Image) -> tuple[bytes, ...]:
    raw = image.tobytes()
    row_size = image.width * len(image.getbands())
    return tuple(raw[offset : offset + row_size] for offset in range(0, len(raw), row_size))


def _best_sampled_overlap(
    previous: Image.Image,
    current: Image.Image,
    *,
    min_overlap_rows: int,
    max_overlap_rows: int,
) -> tuple[int, float]:
    best_overlap = 0
    best_confidence = 0.0
    for overlap_rows in range(max_overlap_rows, min_overlap_rows - 1, -1):
        confidence = _sampled_confidence(previous, current, overlap_rows)
        if confidence > best_confidence:
            best_overlap = overlap_rows
            best_confidence = confidence
    return best_overlap, best_confidence


def _sampled_confidence(previous: Image.Image, current: Image.Image, overlap_rows: int) -> float:
    previous_pixels = previous.load()
    current_pixels = current.load()
    row_indices = _sample_indices(overlap_rows, limit=32)
    column_indices = _sample_indices(previous.width, limit=64)
    total = len(row_indices) * len(column_indices)
    if total == 0:
        return 0.0

    matches = 0
    previous_start = previous.height - overlap_rows
    for row in row_indices:
        previous_y = previous_start + row
        current_y = row
        for column in column_indices:
            if previous_pixels[column, previous_y] == current_pixels[column, current_y]:
                matches += 1
    return matches / total


def _sample_indices(size: int, *, limit: int) -> tuple[int, ...]:
    if size <= limit:
        return tuple(range(size))
    if limit == 1:
        return (0,)
    return tuple(round(index * (size - 1) / (limit - 1)) for index in range(limit))


def _append_frame(base: Image.Image, frame: Image.Image, *, crop_top: int) -> Image.Image:
    append = frame.crop((0, crop_top, frame.width, frame.height))
    if append.height == 0:
        return base.copy()
    stitched = Image.new(base.mode, (base.width, base.height + append.height))
    stitched.paste(base, (0, 0))
    stitched.paste(append, (0, base.height))
    return stitched
