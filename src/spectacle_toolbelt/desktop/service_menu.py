"""KDE desktop and service-menu install target helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


OWNER_MARKER = "X-Spectacle-Toolbelt-Owned=true"


@dataclass(frozen=True)
class InstallTarget:
    source_subdir: str
    destination_subdir: str
    filenames: tuple[str, ...]


DESKTOP_TARGET = InstallTarget(
    source_subdir="desktop",
    destination_subdir="applications",
    filenames=(
        "io.github.ryanwinkler.spectacle-toolbelt.desktop",
        "io.github.ryanwinkler.spectacle-toolbelt-scroll.desktop",
        "io.github.ryanwinkler.spectacle-toolbelt-transform.desktop",
        "io.github.ryanwinkler.spectacle-toolbelt-redact.desktop",
        "io.github.ryanwinkler.spectacle-toolbelt-copy-markdown.desktop",
    ),
)

SERVICE_MENU_TARGET = InstallTarget(
    source_subdir="servicemenus",
    destination_subdir="kio/servicemenus",
    filenames=(
        "io.github.ryanwinkler.spectacle-toolbelt-open-in-spectacle.desktop",
        "io.github.ryanwinkler.spectacle-toolbelt-stitch.desktop",
    ),
)


def xdg_data_home(home: Path, env_value: str | None = None) -> Path:
    return Path(env_value) if env_value else home / ".local" / "share"
