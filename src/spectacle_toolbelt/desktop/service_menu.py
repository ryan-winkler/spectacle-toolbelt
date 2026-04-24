"""KDE service-menu install target helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


OWNER_MARKER = "X-Spectacle-Toolbelt-Owned=true"


@dataclass(frozen=True)
class InstallTarget:
    source_subdir: str
    destination_subdir: str
    filenames: tuple[str, ...]


SERVICE_MENU_TARGET = InstallTarget(
    source_subdir="servicemenus",
    destination_subdir="kio/servicemenus",
    filenames=(
        "io.github.ryanwinkler.spectacle-toolbelt-open-in-spectacle.desktop",
        "io.github.ryanwinkler.spectacle-toolbelt-stitch.desktop",
    ),
)

KF5_SERVICE_MENU_TARGET = InstallTarget(
    source_subdir="servicemenus",
    destination_subdir="kservices5/ServiceMenus",
    filenames=SERVICE_MENU_TARGET.filenames,
)

SERVICE_MENU_TARGETS = (SERVICE_MENU_TARGET, KF5_SERVICE_MENU_TARGET)


def xdg_data_home(home: Path, env_value: str | None = None) -> Path:
    return Path(env_value) if env_value else home / ".local" / "share"
