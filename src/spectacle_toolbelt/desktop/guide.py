"""Small KDE-facing guide for discovering installed Toolbelt actions."""

from __future__ import annotations

import shutil
import subprocess


GUIDE_TEXT = """Spectacle Toolbelt is installed.

Use it from the KDE launcher:

1. Spectacle Toolbelt Scrolling Capture
   Starts the visible scrolling capture workflow with mode choice,
   Capture Next, Done, Cancel, frame count, stitching, and Spectacle editor
   handoff.

2. Spectacle Toolbelt Full-Page Web Capture
   Captures the active Chromium-family tab when DevTools metadata is available,
   otherwise prompts for a URL. The default shortcut is Ctrl+Alt+W.

Use it from Spectacle:

3. Right-click Spectacle in the KDE launcher or task manager, then choose
   Scrolling Capture or Full-Page Web Capture.

Use it from Dolphin:

4. Stitch existing scrolling frames
   Select 2-24 PNG, JPEG, or WebP frames, right-click, then choose:
   Actions > Spectacle Toolbelt > Stitch with Spectacle Toolbelt

5. Open an image in Spectacle's editor
   Select one image, right-click, then choose:
   Actions > Spectacle Toolbelt > Open in Spectacle Editor

Command-line equivalents:

spectacle-toolbelt scroll
spectacle-toolbelt web-fullpage
spectacle-toolbelt stitch --natural-sort frame-*.png --open-in-spectacle
spectacle-toolbelt open-in-spectacle image.png
spectacle-toolbelt doctor
"""


def show_guide() -> int:
    """Show an installed-use guide with KDE tools when available."""

    kdialog = shutil.which("kdialog")
    if kdialog:
        completed = subprocess.run(
            [kdialog, "--title", "Spectacle Toolbelt", "--msgbox", GUIDE_TEXT],
            check=False,
        )
        return completed.returncode

    notify_send = shutil.which("notify-send")
    if notify_send:
        subprocess.run(
            [
                notify_send,
                "Spectacle Toolbelt",
                "Launch Scrolling Capture or Full-Page Web Capture from KDE.",
            ],
            check=False,
        )

    print(GUIDE_TEXT)
    return 0
