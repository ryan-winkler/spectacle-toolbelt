"""Small KDE-facing guide for discovering installed Toolbelt actions."""

from __future__ import annotations

import shutil
import subprocess


GUIDE_TEXT = """Spectacle Toolbelt is installed.

Use it from Dolphin:

1. Stitch scrolling frames
   Select 2-24 PNG, JPEG, or WebP frames, right-click, then choose:
   Actions > Spectacle Toolbelt > Stitch with Spectacle Toolbelt

2. Open an image in Spectacle's editor
   Select one image, right-click, then choose:
   Actions > Spectacle Toolbelt > Open in Spectacle Editor

Command-line equivalents:

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
                "Use Dolphin Actions > Spectacle Toolbelt on selected image files.",
            ],
            check=False,
        )

    print(GUIDE_TEXT)
    return 0
