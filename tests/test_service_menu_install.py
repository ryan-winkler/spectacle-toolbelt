from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STITCH_SERVICE_MENU = REPO_ROOT / "servicemenus" / "io.github.ryanwinkler.spectacle-toolbelt-stitch.desktop"
OPEN_IN_SPECTACLE_SERVICE_MENU = (
    REPO_ROOT / "servicemenus" / "io.github.ryanwinkler.spectacle-toolbelt-open-in-spectacle.desktop"
)
TOOLBELT_LAUNCHER = REPO_ROOT / "desktop" / "io.github.ryanwinkler.spectacle-toolbelt.desktop"


def _run_script(name: str, xdg_data_home: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["XDG_DATA_HOME"] = str(xdg_data_home)
    fake_command = xdg_data_home / "fake-bin" / "spectacle-toolbelt"
    fake_command.parent.mkdir(parents=True, exist_ok=True)
    fake_command.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
    fake_command.chmod(0o755)
    env["SPECTACLE_TOOLBELT_COMMAND"] = str(fake_command)
    return subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / name), *args],
        check=False,
        cwd=REPO_ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def test_install_and_uninstall_round_trip_in_temp_xdg_home(tmp_path) -> None:
    install = _run_script("install-local.sh", tmp_path)

    assert install.returncode == 0, install.stderr
    installed = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*.desktop"))
    assert installed == [
        "applications/io.github.ryanwinkler.spectacle-toolbelt.desktop",
        "kio/servicemenus/io.github.ryanwinkler.spectacle-toolbelt-open-in-spectacle.desktop",
        "kio/servicemenus/io.github.ryanwinkler.spectacle-toolbelt-stitch.desktop",
        "kservices5/ServiceMenus/io.github.ryanwinkler.spectacle-toolbelt-open-in-spectacle.desktop",
        "kservices5/ServiceMenus/io.github.ryanwinkler.spectacle-toolbelt-stitch.desktop",
    ]

    uninstall = _run_script("uninstall-local.sh", tmp_path)

    assert uninstall.returncode == 0, uninstall.stderr
    assert list(tmp_path.rglob("*.desktop")) == []


def test_only_real_guide_launcher_is_shipped() -> None:
    desktop_dir = REPO_ROOT / "desktop"

    desktop_files = sorted(path.name for path in desktop_dir.glob("*.desktop"))
    assert desktop_files == ["io.github.ryanwinkler.spectacle-toolbelt.desktop"]
    content = TOOLBELT_LAUNCHER.read_text(encoding="utf-8")
    assert "Exec=spectacle-toolbelt guide" in content
    assert "X-Spectacle-Toolbelt-Owned=true" in content


def test_install_rewrites_exec_to_resolved_command(tmp_path) -> None:
    install = _run_script("install-local.sh", tmp_path)

    assert install.returncode == 0, install.stderr
    installed_menu = (
        tmp_path / "kio" / "servicemenus" / "io.github.ryanwinkler.spectacle-toolbelt-open-in-spectacle.desktop"
    )
    expected_command = tmp_path / "fake-bin" / "spectacle-toolbelt"
    assert f"Exec={expected_command} open-in-spectacle %f" in installed_menu.read_text(encoding="utf-8")
    assert "Exec=spectacle-toolbelt" not in installed_menu.read_text(encoding="utf-8")

    installed_launcher = tmp_path / "applications" / "io.github.ryanwinkler.spectacle-toolbelt.desktop"
    assert f"Exec={expected_command} guide" in installed_launcher.read_text(encoding="utf-8")


def test_install_refuses_to_overwrite_non_toolbelt_file(tmp_path) -> None:
    target_dir = tmp_path / "kio" / "servicemenus"
    target_dir.mkdir(parents=True)
    target = target_dir / "io.github.ryanwinkler.spectacle-toolbelt-stitch.desktop"
    target.write_text("[Desktop Entry]\nName=Someone Else\n", encoding="utf-8")

    install = _run_script("install-local.sh", tmp_path)

    assert install.returncode == 1
    assert "Refusing to overwrite non-Toolbelt file" in install.stderr


def test_install_refuses_to_overwrite_non_toolbelt_kf5_service_menu(tmp_path) -> None:
    target_dir = tmp_path / "kservices5" / "ServiceMenus"
    target_dir.mkdir(parents=True)
    target = target_dir / "io.github.ryanwinkler.spectacle-toolbelt-stitch.desktop"
    target.write_text("[Desktop Entry]\nName=Someone Else\n", encoding="utf-8")

    install = _run_script("install-local.sh", tmp_path)

    assert install.returncode == 1
    assert "Refusing to overwrite non-Toolbelt file" in install.stderr


def test_uninstall_refuses_to_remove_non_toolbelt_file(tmp_path) -> None:
    target_dir = tmp_path / "applications"
    target_dir.mkdir(parents=True)
    target = target_dir / "io.github.ryanwinkler.spectacle-toolbelt.desktop"
    target.write_text("[Desktop Entry]\nName=Someone Else\n", encoding="utf-8")

    uninstall = _run_script("uninstall-local.sh", tmp_path)

    assert uninstall.returncode == 1
    assert "Refusing to remove non-Toolbelt file" in uninstall.stderr


def test_stitch_service_menu_requires_multiple_files() -> None:
    content = STITCH_SERVICE_MENU.read_text(encoding="utf-8")

    assert "X-KDE-MinNumberOfUrls=2" in content
    assert "X-KDE-MaxNumberOfUrls=24" in content
    assert "stitch --natural-sort --max-frames 24 --open-in-spectacle %F" in content


def test_open_in_spectacle_service_menu_requires_one_file() -> None:
    content = OPEN_IN_SPECTACLE_SERVICE_MENU.read_text(encoding="utf-8")

    assert "X-KDE-MaxNumberOfUrls=1" in content
