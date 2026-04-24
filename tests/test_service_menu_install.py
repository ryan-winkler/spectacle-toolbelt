from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_script(name: str, xdg_data_home: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["XDG_DATA_HOME"] = str(xdg_data_home)
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
        "applications/io.github.ryanwinkler.spectacle-toolbelt-copy-markdown.desktop",
        "applications/io.github.ryanwinkler.spectacle-toolbelt-redact.desktop",
        "applications/io.github.ryanwinkler.spectacle-toolbelt-scroll.desktop",
        "applications/io.github.ryanwinkler.spectacle-toolbelt-transform.desktop",
        "applications/io.github.ryanwinkler.spectacle-toolbelt.desktop",
        "kio/servicemenus/io.github.ryanwinkler.spectacle-toolbelt-open-in-spectacle.desktop",
        "kio/servicemenus/io.github.ryanwinkler.spectacle-toolbelt-stitch.desktop",
    ]

    uninstall = _run_script("uninstall-local.sh", tmp_path)

    assert uninstall.returncode == 0, uninstall.stderr
    assert list(tmp_path.rglob("*.desktop")) == []


def test_install_refuses_to_overwrite_non_toolbelt_file(tmp_path) -> None:
    target_dir = tmp_path / "kio" / "servicemenus"
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
