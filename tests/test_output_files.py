from __future__ import annotations

from datetime import datetime as real_datetime

from spectacle_toolbelt.output import files


class _FixedDatetime:
    @staticmethod
    def now() -> real_datetime:
        return real_datetime(2026, 4, 24, 13, 35, 17, 123456)


def test_timestamped_output_path_uses_microseconds(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(files, "datetime", _FixedDatetime)
    monkeypatch.setattr(files, "default_screenshot_dir", lambda: tmp_path)

    output = files.timestamped_output_path()

    assert output == tmp_path / "Scrolling Screenshot 2026-04-24 13.35.17.123456.png"


def test_timestamped_output_path_avoids_existing_file(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(files, "datetime", _FixedDatetime)
    monkeypatch.setattr(files, "default_screenshot_dir", lambda: tmp_path)
    existing = tmp_path / "Scrolling Screenshot 2026-04-24 13.35.17.123456.png"
    existing.write_bytes(b"existing")

    output = files.timestamped_output_path()

    assert output == tmp_path / "Scrolling Screenshot 2026-04-24 13.35.17.123456-2.png"


def test_default_screenshot_dir_uses_xdg_pictures_dir(monkeypatch, tmp_path) -> None:
    config_home = tmp_path / "config"
    config_home.mkdir()
    (config_home / "user-dirs.dirs").write_text(
        'XDG_PICTURES_DIR="$HOME/Images"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    assert files.default_screenshot_dir() == tmp_path / "home" / "Images" / "Screenshots"


def test_default_screenshot_dir_uses_spectacle_folder_name(monkeypatch, tmp_path) -> None:
    config_home = tmp_path / "config"
    config_home.mkdir()
    (config_home / "user-dirs.dirs").write_text(
        f'XDG_PICTURES_DIR="{tmp_path / "Pictures"}"\n',
        encoding="utf-8",
    )
    (config_home / "spectaclerc").write_text(
        "[ImageSave]\ntranslatedScreenshotsFolder=Captures\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

    assert files.default_screenshot_dir() == tmp_path / "Pictures" / "Captures"


def test_default_screenshot_dir_prefers_spectacle_image_save_location(monkeypatch, tmp_path) -> None:
    config_home = tmp_path / "config"
    save_location = tmp_path / "Pictures" / "Screenshots" / "2026.04"
    config_home.mkdir()
    (config_home / "user-dirs.dirs").write_text(
        f'XDG_PICTURES_DIR="{tmp_path / "Pictures"}"\n',
        encoding="utf-8",
    )
    (config_home / "spectaclerc").write_text(
        "[ImageSave]\n"
        f"imageSaveLocation=file://{save_location}\n"
        "lastImageSaveLocation=file:///tmp/exported/elsewhere.png\n"
        "translatedScreenshotsFolder=Captures\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

    assert files.default_screenshot_dir() == save_location


def test_default_screenshot_dir_accepts_absolute_spectacle_folder(monkeypatch, tmp_path) -> None:
    config_home = tmp_path / "config"
    custom_dir = tmp_path / "Custom Screenshots"
    config_home.mkdir()
    (config_home / "spectaclerc").write_text(
        f"[ImageSave]\ntranslatedScreenshotsFolder={custom_dir}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

    assert files.default_screenshot_dir() == custom_dir
