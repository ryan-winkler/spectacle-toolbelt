"""Command-line entrypoint for Spectacle Toolbelt."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from spectacle_toolbelt.diagnostics import run_doctor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spectacle-toolbelt",
        description="Companion extension workflows for KDE Spectacle.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Report local capture/tooling support.")
    doctor.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")

    stitch = subparsers.add_parser("stitch", help="Stitch pre-captured scroll frames.")
    stitch.add_argument("frames", nargs="+", type=Path, help="Frame images in capture order.")
    stitch.add_argument("-o", "--output", required=True, type=Path, help="Output PNG path.")
    stitch.add_argument(
        "--min-confidence",
        type=float,
        default=0.92,
        help="Minimum overlap confidence before marking output partial.",
    )
    stitch.add_argument(
        "--min-overlap-rows",
        type=int,
        default=8,
        help="Minimum rows required for a reliable overlap match.",
    )
    stitch.add_argument("--debug-json", type=Path, help="Optional path for stitch diagnostics.")

    scroll = subparsers.add_parser("scroll", help="Start a scrolling capture workflow.")
    scroll.add_argument("-o", "--output", type=Path, help="Output PNG path.")
    scroll.add_argument(
        "--manual",
        action="store_true",
        help="Use manual/panoramic mode instead of automatic scrolling.",
    )

    transform = subparsers.add_parser("transform", help="Run a named image transform preset.")
    transform.add_argument("image", nargs="?", type=Path, help="Input image path.")
    transform.add_argument("--preset", default="docs-clean", help="Preset name.")

    redact = subparsers.add_parser("redact", help="Create a redacted image copy.")
    redact.add_argument("image", nargs="?", type=Path, help="Input image path.")
    redact.add_argument("--policy", default="default", help="Redaction policy name.")

    ocr = subparsers.add_parser("ocr", help="Extract text from an image.")
    ocr.add_argument("image", nargs="?", type=Path, help="Input image path.")
    ocr.add_argument("--copy", action="store_true", help="Copy extracted text.")

    qr = subparsers.add_parser("qr", help="Read QR/barcode content from an image.")
    qr.add_argument("image", nargs="?", type=Path, help="Input image path.")

    markdown = subparsers.add_parser("markdown", help="Copy or print Markdown for an image.")
    markdown.add_argument("image", nargs="?", type=Path, help="Input image path.")
    markdown.add_argument("--copy", action="store_true", help="Copy Markdown to clipboard.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        report = run_doctor()
        if args.json:
            print(json.dumps(report.to_dict(), indent=2))
            return 0
        print(report.to_text())
        return 0 if report.is_usable else 2

    if args.command == "stitch":
        from spectacle_toolbelt.scroll.stitch_engine import StitchError, stitch_files

        try:
            result = stitch_files(
                args.frames,
                args.output,
                min_confidence=args.min_confidence,
                min_overlap_rows=args.min_overlap_rows,
            )
        except StitchError as exc:
            print(f"stitch failed: {exc}", file=sys.stderr)
            return 1
        if args.debug_json:
            args.debug_json.parent.mkdir(parents=True, exist_ok=True)
            args.debug_json.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        print(f"{result.status}: wrote {args.output} from {result.frames} frames")
        return 0 if result.status != "failed" else 1

    if args.command == "scroll":
        mode = "manual" if args.manual else "automatic"
        print(
            "scroll capture is scaffolded for v0.1; "
            f"requested mode={mode}. Use `stitch` for captured frames today."
        )
        return 2

    if args.command in {"transform", "redact", "ocr", "qr", "markdown"}:
        print(
            f"{args.command} is part of the Spectacle Toolbelt roadmap and is not "
            "implemented in v0.1 yet."
        )
        return 2

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
