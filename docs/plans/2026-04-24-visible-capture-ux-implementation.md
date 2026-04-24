# Visible Capture UX Implementation Plan

Date: 2026-04-24
Status: Implemented

## Goal

Replace the current scaffold-only experience with visible KDE entry points for
the approved Snagit/ShareX parity slice:

- explicit scrolling capture launcher and CLI workflow
- manual frame capture with Capture Next, Done, Cancel, frame count, and status
- automatic mode command surface that attempts desktop scrolling where supported
  and falls back clearly when not supported
- vertical and horizontal automatic modes only; bidirectional capture is not
  advertised until a real grid/bidirectional stitcher exists
- full-page web capture launcher and CLI workflow for `Ctrl+Alt+W`
- output handoff to Spectacle's native editor

## Approach

Keep Toolbelt as a companion application. Use Spectacle for region capture and
editor handoff, KDE `kdialog` for the first visible workflow, and a browser
automation backend for webpage capture. Do not intercept normal Spectacle
shortcuts.

## Files

- `src/spectacle_toolbelt/cli.py`
- `src/spectacle_toolbelt/scroll/controller.py`
- `src/spectacle_toolbelt/capture/spectacle_adapter.py`
- `src/spectacle_toolbelt/web/fullpage.py`
- `src/spectacle_toolbelt/desktop/dialogs.py`
- `desktop/io.github.ryanwinkler.spectacle-toolbelt-scroll.desktop`
- `desktop/io.github.ryanwinkler.spectacle-toolbelt-web-fullpage.desktop`
- `scripts/install-local.sh`
- `scripts/uninstall-local.sh`
- `README.md`
- `docs/integration/kde-shortcuts.md`
- `tests/test_cli.py`
- `tests/test_service_menu_install.py`
- new focused tests for scrolling sessions and web capture helpers

## Steps

1. Add tests for the desired visible surfaces:
   - `scroll` no longer reports scaffold-only.
   - `scroll --manual` delegates to a session runner.
   - desktop install includes guide, scrolling capture, and full-page web
     capture launchers.
   - `web-fullpage --url` captures through the browser backend and reports the
     output.

2. Implement scrolling session runner:
   - allocate a temporary frame directory.
   - capture frames through Spectacle.
   - use KDE dialogs for mode selection and frame loop.
   - support Capture Next, Done, Cancel.
   - write debug JSON next to the output.
   - open completed or partial results in Spectacle.

3. Implement browser full-page command:
   - validate URL scheme.
   - attempt active-tab resolution through Chrome/Chromium DevTools metadata.
   - prompt for URL via `kdialog` when no URL is supplied or resolved.
   - capture with a headless Chromium-family browser and CDP.
   - copy the image to clipboard when `wl-copy` or `xclip` exists.
   - open output in Spectacle when requested.

4. Add KDE launchers:
   - `Spectacle Toolbelt Scrolling Capture`
   - `Spectacle Toolbelt Full-Page Web Capture`
   - set `X-KDE-Shortcuts=Ctrl+Alt+W` on the full-page web launcher.
   - add reversible user-local Spectacle app actions for the same workflows.

5. Update docs to describe the UI honestly:
   - scrolling capture now appears as a launcher/action.
   - manual mode is usable now.
   - automatic mode is platform-gated.
   - `Ctrl+Alt+W` is Toolbelt-owned and does not affect normal Spectacle
     screenshots.

6. Verify:
   - `python -m pytest`
   - `scripts/install-local.sh`
   - `spectacle-toolbelt doctor`
   - `spectacle-toolbelt scroll --help`
   - `spectacle-toolbelt web-fullpage --help`
   - KDE service cache refresh succeeds or reports the manual command.
