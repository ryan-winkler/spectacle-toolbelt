# Spectacle Toolbelt

Spectacle Toolbelt is a companion extension kit for KDE Spectacle. It is not a
fork, replacement, or patched Spectacle build.

The project adds power-user workflow glue around Spectacle through normal KDE
integration points: command-line tools, Spectacle launcher app actions,
Dolphin/KIO service menus, and documented shortcut recipes. Spectacle remains
the screenshot application and the intended native GUI home for mature
features.

Toolbelt does not replace Spectacle's annotation editor, OCR action, QR scan
flow, desktop actions, D-Bus capture surface, or KGlobalAccel shortcuts. It
composes with those surfaces and provides a proving ground for missing workflows
such as scrolling capture, repeatable transform presets, Markdown export, and
documentation asset handling.

## Status

`v0.1` is pre-alpha. The first usable wedge is visible scrolling capture plus
full-page web capture.

Current implementation:

- `spectacle-toolbelt doctor` checks local capture and helper-tool support.
- `spectacle-toolbelt scroll` starts a KDE-visible scrolling capture workflow
  with mode choice, Spectacle region capture, Capture Next, Done, Cancel, frame
  count, stitch diagnostics, and Spectacle editor handoff.
- `spectacle-toolbelt web-fullpage` captures a complete webpage PNG. It tries
  active Chromium-family tab metadata first when available, then prompts for a
  URL. The installed launcher declares `Ctrl+Alt+W` as its KDE shortcut.
- `spectacle-toolbelt stitch FRAME... [--output OUTPUT.png]` stitches
  pre-captured scroll frames. Without `--output`, Toolbelt writes to the
  Spectacle/XDG screenshots folder with a collision-resistant timestamped name.
- `spectacle-toolbelt open-in-spectacle IMAGE` opens an image in Spectacle's
  native annotation editor via `spectacle --edit-existing`.
- `transform`, `redact`, `ocr`, `qr`, and `markdown` commands are present as
  CLI roadmap stubs so issue reports can use stable names from the start. They
  are not installed into the GUI and are not claims that Toolbelt owns
  Spectacle-native features.
- Desktop integration installs Toolbelt-owned guide, scrolling capture, and
  full-page web capture launchers, adds a reversible user-local Spectacle
  launcher app-action override, and installs working Dolphin/KIO service menus.
  It does not edit Spectacle's system files.

## What Spectacle Already Owns

Toolbelt should reuse these Spectacle-native capabilities instead of duplicating
them:

- capture modes: full desktop, current monitor, active window, selected/window
  under cursor, and rectangular region
- recording modes: region, screen, and window
- CLI/background capture: `--background`, `--region`, `--output`,
  `--copy-image`, `--copy-path`, `--delay`, and `--onclick`
- native editor handoff: `spectacle --edit-existing <file>`
- D-Bus capture and recording methods
- `.desktop` actions and KGlobalAccel global shortcuts
- annotation editor tools: crop, select, freehand, highlighter, line, arrow,
  rectangle, ellipse, pixelate, blur, text, and number stamp
- OCR action: Extract Text
- QR scanning in the export flow
- notifications with open and annotate actions

## Native GUI Direction

The end-state UX for serious features should be native Spectacle UI, not a
parallel app. For scrolling capture, that means a Spectacle capture mode/action,
selection overlay controls, Done/Cancel, progress, frame count, partial-result
states, and final handoff to Spectacle's editor.

Toolbelt's launcher actions, CLI, and service menus are the bridge:

- prove algorithms and edge cases
- generate diagnostics and fixtures
- provide useful KDE-standard fallback workflows
- produce upstream-ready proposals and implementation evidence for Spectacle

## v0.1: Scrolling Capture

The v0.1 target is a local workflow for capturing content that is taller than
the visible screen:

1. Select or capture a region with Spectacle.
2. Capture multiple frames while the content scrolls.
3. Detect overlapping rows between consecutive frames.
4. Stitch the frames into one PNG.
5. Mark the result as partial when overlap confidence is too low.

The first external implementation path is intentionally conservative but usable:

- Manual/panoramic mode is available now from the KDE launcher and CLI.
- Automatic vertical and horizontal modes are exposed. They use explicit X11
  scroll input when supported and fall back to manual mode on restricted Wayland
  sessions. Bidirectional capture remains reserved for native Spectacle/grid
  session support so Toolbelt does not advertise a mode it cannot stitch
  correctly.
- Stitching diagnostics should be inspectable so users can report artifacts
  without uploading sensitive screenshots.
- Stitched output opens in Spectacle's existing editor for annotation, OCR, QR,
  copy, save, and share workflows.

Example:

```bash
spectacle-toolbelt scroll
spectacle-toolbelt scroll --manual --output scrolled-page.png
spectacle-toolbelt web-fullpage --url https://example.com/
```

## Roadmap

The broader project direction is a Spectacle companion toolbelt that leads back
to Spectacle-native UX:

- Scrolling capture: manual first, then assisted automatic scrolling where the
  session permits it, with native Spectacle UI as the target.
- Smart stitching: artifact detection, partial-output reporting, horizontal
  tolerance, fixed-header handling, and debug overlays.
- ImageMagick-style presets: resize, trim, border, watermark, blur, compare,
  format conversion, and save-variant workflows behind safe named presets.
- Spectacle editor handoff: open stitched/generated images in Spectacle for
  annotation, OCR, QR scanning, copy, save, and share workflows.
- Redaction workflow glue: use Spectacle-owned blur/pixelate/manual annotation
  where possible; only add policy/automation where Spectacle does not already
  own the interaction.
- Documentation workflow glue: Markdown export, sidecar metadata, consistent
  asset naming, and guide sequencing around Spectacle-edited images.
- Screenshot library helpers: local metadata, tags, OCR index files, and
  repeatable naming.
- KDE integration: Dolphin/KIO service menus, KRunner/global shortcut recipes,
  and upstream Spectacle integration proposals/MRs when a workflow proves stable.

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

### KWin Authorization Errors

On Plasma Wayland, custom Spectacle launchers must declare the same restricted
interfaces as Spectacle's own desktop file. If KWin reports that the process is
not authorized to take a screenshot, run `spectacle-toolbelt doctor` and check
for local `spectacle*.desktop` entries missing the KWin authorization keys.

## Install

Requirements:

- KDE Spectacle on `PATH`
- Python 3.10+
- Pillow
- websockets
- `kdialog` for KDE-native launcher dialogs. Terminal CLI use can fall back to
  stdin prompts, but `.desktop` launcher workflows intentionally fail closed
  instead of hanging when no dialog tool is available.
- Optional: Chromium, Google Chrome, or Chromium Browser for full-page web
  capture
- Optional: `xdotool` for active-tab matching and automatic scrolling on X11
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

Install the KDE launchers and service menus into your user XDG data directories:

```bash
scripts/install-local.sh --dry-run
scripts/install-local.sh
```

Remove Toolbelt-owned local integration files:

```bash
scripts/uninstall-local.sh --dry-run
scripts/uninstall-local.sh
```

The install scripts install three visible launchers:

- `Spectacle Toolbelt`
- `Spectacle Toolbelt Scrolling Capture`
- `Spectacle Toolbelt Full-Page Web Capture`

They also install two Spectacle app actions into a user-local
`org.kde.spectacle.desktop` override so right-clicking Spectacle in the KDE
launcher/task manager exposes:

- `Scrolling Capture`
- `Full-Page Web Capture`

The installer copies the system Spectacle desktop file first, preserves its
KWin authorization keys, then appends Toolbelt actions. Uninstalling removes
only the Toolbelt-owned user override and falls back to the system Spectacle
desktop file.

The scripts also install Dolphin/KIO service-menu surfaces and clean up older
Toolbelt-owned launcher stubs. They refuse to overwrite or delete a target file
unless it contains the `X-Spectacle-Toolbelt-Owned=true` marker. Installed
entries are rewritten to use the resolved Toolbelt executable, so KDE does not
need to inherit your activated virtualenv. The scripts refresh KDE's service
cache automatically when `kbuildsycoca6` or `kbuildsycoca5` is available.

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

Check KDE service-menu structure:

```bash
rg "Type=Service|ServiceTypes=KonqPopupMenu/Plugin|X-Spectacle-Toolbelt-Owned=true" servicemenus/*.desktop
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
