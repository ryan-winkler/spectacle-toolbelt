"""Filesystem output helpers."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse


def default_screenshot_dir() -> Path:
    save_dir = _spectacle_image_save_location()
    if save_dir is not None:
        return save_dir
    screenshot_folder = _spectacle_screenshot_folder()
    if screenshot_folder is not None and screenshot_folder.is_absolute():
        return screenshot_folder
    return _xdg_pictures_dir() / (screenshot_folder or Path("Screenshots"))


def timestamped_output_path(prefix: str = "Scrolling Screenshot") -> Path:
    stamp = datetime.now().strftime("%Y-%m-%d %H.%M.%S.%f")
    directory = default_screenshot_dir()
    candidate = directory / f"{prefix} {stamp}.png"
    if not candidate.exists():
        return candidate

    for suffix in range(2, 1000):
        candidate = directory / f"{prefix} {stamp}-{suffix}.png"
        if not candidate.exists():
            return candidate

    raise FileExistsError(f"could not allocate a unique output path in {directory}")


def _spectacle_screenshot_folder() -> Path | None:
    config_path = _xdg_config_home() / "spectaclerc"
    value = _read_kconfig_value(config_path, "ImageSave", "translatedScreenshotsFolder")
    if not value:
        return None
    return _path_from_config_value(value)


def _spectacle_image_save_location() -> Path | None:
    config_path = _xdg_config_home() / "spectaclerc"
    value = _read_kconfig_value(config_path, "ImageSave", "imageSaveLocation")
    if not value:
        return None
    return _path_from_config_value(value)


def _xdg_pictures_dir() -> Path:
    value = _read_xdg_user_dir("XDG_PICTURES_DIR")
    if value:
        return _path_from_config_value(value)
    return Path.home() / "Pictures"


def _xdg_config_home() -> Path:
    value = os.environ.get("XDG_CONFIG_HOME")
    return Path(value).expanduser() if value else Path.home() / ".config"


def _read_xdg_user_dir(key: str) -> str | None:
    config_path = _xdg_config_home() / "user-dirs.dirs"
    if not config_path.exists():
        return None
    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        line_key, raw_value = line.split("=", 1)
        if line_key != key:
            continue
        return raw_value.strip().strip('"')
    return None


def _read_kconfig_value(config_path: Path, group: str, key: str) -> str | None:
    if not config_path.exists():
        return None

    in_group = False
    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            in_group = line[1:-1] == group
            continue
        if not in_group or "=" not in line:
            continue
        line_key, raw_value = line.split("=", 1)
        if line_key == key:
            return raw_value.strip()
    return None


def _path_from_config_value(value: str) -> Path:
    if value.startswith("file://"):
        parsed = urlparse(value)
        value = unquote(parsed.path)
    elif value.startswith("$HOME/"):
        value = str(Path.home() / value.removeprefix("$HOME/"))
    elif value == "$HOME":
        value = str(Path.home())
    return Path(value).expanduser()
