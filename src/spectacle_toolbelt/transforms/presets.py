"""Named transform presets for future ImageMagick/Pillow workflows."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TransformPreset:
    name: str
    steps: tuple[str, ...]
    description: str


BUILTIN_PRESETS = {
    "privacy-strip": TransformPreset(
        name="privacy-strip",
        steps=("strip-metadata",),
        description="Remove metadata before sharing.",
    ),
    "docs-clean": TransformPreset(
        name="docs-clean",
        steps=("strip-metadata", "trim-border", "compress-png"),
        description="Prepare a screenshot for documentation.",
    ),
}
