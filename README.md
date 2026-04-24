# Spectacle Toolbelt

Spectacle Toolbelt is a companion extension kit for KDE Spectacle. It is not a
fork, replacement, or patched Spectacle build.

The project adds power-user workflows around Spectacle through normal desktop
integration points: command-line tools, local launchers, desktop actions, and
future service-menu entries. Spectacle remains the screenshot application.
Toolbelt handles the things that sit just outside Spectacle's current scope:
scrolling capture, repeatable image transforms, OCR workflows, redaction,
documentation capture, and export automation.

## Status

`v0.1` is pre-alpha. The first usable wedge is scrolling capture.

Current scaffold:

- `spectacle-toolbelt doctor` checks local capture and helper-tool support.
- `spectacle-toolbelt stitch FRAME... --output OUTPUT.png` stitches
  pre-captured scroll frames.
- `spectacle-toolbelt scroll --manual --output OUTPUT.png` is the planned
  user-facing scrolling workflow and currently reports that the workflow is
  still scaffolded.
- `transform`, `redact`, `ocr`, `qr`, and `markdown` commands are present as
  roadmap stubs so desktop actions and issue reports can use stable names from
  the start.
- Desktop integration installs Toolbelt-owned launchers only. It does not edit
  Spectacle files, KDE system files, or user shortcuts.

## v0.1: Scrolling Capture

The v0.1 target is a local workflow for capturing content that is taller than
the visible screen:

1. Select or capture a region with Spectacle.
2. Capture multiple frames while the content scrolls.
3. Detect overlapping rows between consecutive frames.
4. Stitch the frames into one PNG.
5. Mark the result as partial when overlap confidence is too low.

The first implementation path is intentionally conservative:

- Manual/panoramic mode comes first because it works across more Wayland
  setups and is easier to debug.
- Automatic scrolling is a later enhancement and will depend on what the
  active desktop session allows.
- Stitching diagnostics should be inspectable so users can report artifacts
  without uploading sensitive screenshots.

Example:

```bash
spectacle-toolbelt stitch frame-001.png frame-002.png frame-003.png \
  --output scrolled-page.png \
  --debug-json scrolled-page.debug.json
```

## Roadmap

The broader project direction is a Spectacle companion toolbelt:

- Scrolling capture: manual first, then assisted automatic scrolling where the
  session permits it.
- Smart stitching: artifact detection, partial-output reporting, horizontal
  tolerance, fixed-header handling, and debug overlays.
- ImageMagick-style presets: resize, trim, border, watermark, blur, compare,
  format conversion, and save-variant workflows behind safe named presets.
- OCR workflows: copy text, searchable sidecar text, QR/barcode reading, and
  local text extraction.
- Redaction: blur, pixelate, block, and future OCR-assisted redaction of email
  addresses, access keys, tokens, and other sensitive patterns.
- Documentation capture: step markers, click trails, numbered callouts, and
  markdown export for runbooks and support notes.
- Screenshot library helpers: local metadata, tags, OCR index files, and
  repeatable naming.
- KDE integration: service menus, KRunner/global shortcut recipes, and upstream
  Spectacle integration proposals when a workflow proves stable.

## Wayland and X11 Caveats

Screenshot tools are constrained by the desktop session.

Wayland:

- Wayland intentionally limits arbitrary screen capture, input injection, and
  app control. Toolbelt should rely on Spectacle, portals, KDE-supported APIs,
  and explicit user actions.
- Automatic scrolling may not be available for every app. Manual mode is the
  baseline fallback.
- Clipboard helpers usually require `wl-copy` from `wl-clipboard`.

X11:

- X11 allows more automation, but that also means higher risk. Toolbelt should
  still avoid surprising input injection and should keep automation explicit.
- Clipboard helpers usually require `xclip` or `xsel`.

Both sessions:

- Fixed headers, lazy-loaded content, animations, video, cursor movement, and
  translucent UI can cause stitching artifacts.
- Scrolling pages that change layout while capturing may produce partial output.
- Reports should include diagnostics and reproduction details, not private
  screenshots unless the reporter has already redacted them.

## Install

Requirements:

- KDE Spectacle on `PATH`
- Python 3.10+
- Pillow
- Optional: ImageMagick 7 (`magick`) or ImageMagick 6 (`convert`)
- Optional: `wl-copy`, `xclip`, or `xsel` for clipboard workflows
- Optional: `notify-send` for desktop notifications

Local development install:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
spectacle-toolbelt doctor
```

Install desktop launchers into your user XDG applications directory:

```bash
scripts/install-local.sh --dry-run
scripts/install-local.sh
```

Remove only Toolbelt-owned desktop launchers:

```bash
scripts/uninstall-local.sh --dry-run
scripts/uninstall-local.sh
```

The install scripts copy only the `.desktop` files shipped in this repository.
They refuse to overwrite or delete a target file unless it contains the
`X-Spectacle-Toolbelt-Owned=true` marker.

## Development

Run the CLI from a checkout:

```bash
source .venv/bin/activate
spectacle-toolbelt doctor
spectacle-toolbelt --help
```

Run quick checks:

```bash
python -m compileall src
python -m pytest
bash -n scripts/install-local.sh scripts/uninstall-local.sh
```

If the `tests/` directory has not been created yet, `pytest` may report that no
test path exists. The compile and shell checks are still useful smoke tests for
the current scaffold.

Validate desktop files when `desktop-file-validate` is installed:

```bash
desktop-file-validate desktop/*.desktop
```

## Privacy and Security

Toolbelt is local-first:

- No cloud upload is part of v0.1.
- No telemetry is collected.
- Screenshots, OCR output, debug JSON, and stitched images stay on the local
  machine unless the user moves or uploads them.
- Future integrations that send data outside the machine must be opt-in and
  clearly documented.

Screenshots often contain secrets. Treat every screenshot as sensitive by
default:

- Redact private content before filing issues or sharing examples.
- Do not paste API keys, session cookies, tokens, personal messages, or customer
  data into issue reports.
- Prefer cropped/recreated examples for stitching bugs.
- Be careful with untrusted input files. ImageMagick-backed workflows must stay
  behind constrained presets and should not execute arbitrary user-provided
  command strings.

## Relationship to Spectacle

This project depends on Spectacle and respects its boundaries. It should make
Spectacle more useful without asking users to install a fork or replace KDE
components.

If a Toolbelt workflow becomes mature, reliable, and broadly useful, the next
step is to propose the behavior or integration hook upstream instead of keeping
it as permanent parallel infrastructure.
