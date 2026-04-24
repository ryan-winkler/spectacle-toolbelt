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
SCROLL_LAUNCHER = REPO_ROOT / "desktop" / "io.github.ryanwinkler.spectacle-toolbelt-scroll.desktop"
WEB_FULLPAGE_LAUNCHER = REPO_ROOT / "desktop" / "io.github.ryanwinkler.spectacle-toolbelt-web-fullpage.desktop"


def _run_script(
    name: str,
    xdg_data_home: Path,
    *args: str,
    use_fake_command: bool = True,
    extra_env: dict[str, str] | None = None,
    spectacle_auth_keys: bool = True,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["XDG_DATA_HOME"] = str(xdg_data_home)
    if use_fake_command:
        fake_command = xdg_data_home / "fake-bin" / "spectacle-toolbelt"
        fake_command.parent.mkdir(parents=True, exist_ok=True)
        fake_command.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
        fake_command.chmod(0o755)
        env["SPECTACLE_TOOLBELT_COMMAND"] = str(fake_command)
    fake_spectacle_desktop = xdg_data_home / "fake-system" / "org.kde.spectacle.desktop"
    fake_spectacle_desktop.parent.mkdir(parents=True, exist_ok=True)
    spectacle_lines = [
        "[Desktop Entry]",
        "Name=Spectacle",
        "Exec=/usr/bin/spectacle",
        "Actions=FullScreenScreenShot;OpenWithoutScreenshot",
    ]
    if spectacle_auth_keys:
        spectacle_lines.extend(
            [
                "X-KDE-DBUS-Restricted-Interfaces=org.kde.KWin.ScreenShot2",
                "X-KDE-Wayland-Interfaces=org_kde_plasma_window_management,zkde_screencast_unstable_v1",
            ]
        )
    spectacle_lines.extend(
        [
            "",
            "[Desktop Action FullScreenScreenShot]",
            "Name=Capture Entire Desktop",
            "Exec=/usr/bin/spectacle -f",
            "",
            "[Desktop Action OpenWithoutScreenshot]",
            "Name=Launch without taking a screenshot",
            "Exec=/usr/bin/spectacle -l",
            "",
        ]
    )
    fake_spectacle_desktop.write_text("\n".join(spectacle_lines), encoding="utf-8")
    env["SPECTACLE_DESKTOP_SOURCE"] = str(fake_spectacle_desktop)
    if extra_env:
        env.update(extra_env)
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
        "applications/io.github.ryanwinkler.spectacle-toolbelt-scroll.desktop",
        "applications/io.github.ryanwinkler.spectacle-toolbelt-web-fullpage.desktop",
        "applications/io.github.ryanwinkler.spectacle-toolbelt.desktop",
        "applications/org.kde.spectacle.desktop",
        "fake-system/org.kde.spectacle.desktop",
        "kio/servicemenus/io.github.ryanwinkler.spectacle-toolbelt-open-in-spectacle.desktop",
        "kio/servicemenus/io.github.ryanwinkler.spectacle-toolbelt-stitch.desktop",
        "kservices5/ServiceMenus/io.github.ryanwinkler.spectacle-toolbelt-open-in-spectacle.desktop",
        "kservices5/ServiceMenus/io.github.ryanwinkler.spectacle-toolbelt-stitch.desktop",
    ]

    uninstall = _run_script("uninstall-local.sh", tmp_path)

    assert uninstall.returncode == 0, uninstall.stderr
    assert sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*.desktop")) == [
        "fake-system/org.kde.spectacle.desktop"
    ]


def test_real_visible_launchers_are_shipped() -> None:
    desktop_dir = REPO_ROOT / "desktop"

    desktop_files = sorted(path.name for path in desktop_dir.glob("*.desktop"))
    assert desktop_files == [
        "io.github.ryanwinkler.spectacle-toolbelt-scroll.desktop",
        "io.github.ryanwinkler.spectacle-toolbelt-web-fullpage.desktop",
        "io.github.ryanwinkler.spectacle-toolbelt.desktop",
    ]
    guide_content = TOOLBELT_LAUNCHER.read_text(encoding="utf-8")
    scroll_content = SCROLL_LAUNCHER.read_text(encoding="utf-8")
    web_content = WEB_FULLPAGE_LAUNCHER.read_text(encoding="utf-8")
    assert "Exec=spectacle-toolbelt guide" in guide_content
    assert "Exec=spectacle-toolbelt scroll" in scroll_content
    assert "Name=Spectacle Toolbelt Scrolling Capture" in scroll_content
    assert "X-KDE-DBUS-Restricted-Interfaces=org.kde.KWin.ScreenShot2" in scroll_content
    assert "X-KDE-Wayland-Interfaces=org_kde_plasma_window_management,zkde_screencast_unstable_v1" in scroll_content
    assert "Exec=spectacle-toolbelt web-fullpage" in web_content
    assert "X-KDE-Shortcuts=Ctrl+Alt+W" in web_content
    assert "X-Spectacle-Toolbelt-Owned=true" in guide_content
    assert "X-Spectacle-Toolbelt-Owned=true" in scroll_content
    assert "X-Spectacle-Toolbelt-Owned=true" in web_content


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
    installed_scroll = tmp_path / "applications" / "io.github.ryanwinkler.spectacle-toolbelt-scroll.desktop"
    installed_web = tmp_path / "applications" / "io.github.ryanwinkler.spectacle-toolbelt-web-fullpage.desktop"
    assert f"Exec={expected_command} scroll" in installed_scroll.read_text(encoding="utf-8")
    assert f"Exec={expected_command} web-fullpage" in installed_web.read_text(encoding="utf-8")


def test_install_adds_reversible_spectacle_app_actions(tmp_path) -> None:
    install = _run_script("install-local.sh", tmp_path)

    assert install.returncode == 0, install.stderr
    expected_command = tmp_path / "fake-bin" / "spectacle-toolbelt"
    installed_spectacle = tmp_path / "applications" / "org.kde.spectacle.desktop"
    content = installed_spectacle.read_text(encoding="utf-8")
    assert "Actions=FullScreenScreenShot;OpenWithoutScreenshot;ToolbeltScrollCapture;ToolbeltWebFullpage;" in content
    assert "[Desktop Action ToolbeltScrollCapture]" in content
    assert "Name=Scrolling Capture" in content
    assert f"Exec={expected_command} scroll" in content
    assert "[Desktop Action ToolbeltWebFullpage]" in content
    assert "Name=Full-Page Web Capture" in content
    assert f"Exec={expected_command} web-fullpage" in content
    assert "X-KDE-Shortcuts=Ctrl+Alt+W" in content
    assert "X-KDE-DBUS-Restricted-Interfaces=org.kde.KWin.ScreenShot2" in content
    assert "X-KDE-Wayland-Interfaces=org_kde_plasma_window_management,zkde_screencast_unstable_v1" in content
    assert "X-Spectacle-Toolbelt-Owned=true" in content


def test_install_injects_kwin_authorization_when_spectacle_source_lacks_it(tmp_path) -> None:
    install = _run_script("install-local.sh", tmp_path, spectacle_auth_keys=False)

    assert install.returncode == 0, install.stderr
    installed_spectacle = tmp_path / "applications" / "org.kde.spectacle.desktop"
    content = installed_spectacle.read_text(encoding="utf-8")
    desktop_entry = content.split("[Desktop Action FullScreenScreenShot]", 1)[0]
    assert "X-KDE-DBUS-Restricted-Interfaces=org.kde.KWin.ScreenShot2" in desktop_entry
    assert "X-KDE-Wayland-Interfaces=org_kde_plasma_window_management,zkde_screencast_unstable_v1" in desktop_entry


def test_installer_runtime_probe_does_not_require_dbus_on_x11(tmp_path) -> None:
    fake_python = _fake_python_without_dbus(tmp_path)

    install = _run_script(
        "install-local.sh",
        tmp_path,
        use_fake_command=False,
        extra_env={
            "XDG_SESSION_TYPE": "x11",
            "SPECTACLE_TOOLBELT_PYTHON_CANDIDATES": str(fake_python),
        },
    )

    assert install.returncode == 0, install.stderr
    wrapper = tmp_path / "spectacle-toolbelt" / "bin" / "spectacle-toolbelt"
    assert wrapper.exists()
    wrapper_content = wrapper.read_text(encoding="utf-8")
    assert f"exec '{fake_python}' -m spectacle_toolbelt.cli" in wrapper_content
    assert 'if [ "${1:-}" = "scroll" ] && [ "$toolbelt_help_only" != "true" ]; then' in wrapper_content
    assert "requires dbus-python" in wrapper_content
    assert "lacks dbus-python" in install.stderr


def test_installer_runtime_probe_requires_imagemagick_import_on_x11(tmp_path) -> None:
    fake_python = _fake_python_without_dbus(tmp_path)

    install = _run_script(
        "install-local.sh",
        tmp_path,
        "--dry-run",
        use_fake_command=False,
        extra_env={
            "XDG_SESSION_TYPE": "x11",
            "SPECTACLE_TOOLBELT_PYTHON_CANDIDATES": str(fake_python),
            "SPECTACLE_TOOLBELT_IMPORT_COMMAND": "definitely-missing-imagemagick-import",
        },
    )

    assert install.returncode == 1
    assert "ImageMagick import is required" in install.stderr


def test_installer_treats_unknown_session_as_x11_backend(tmp_path) -> None:
    fake_python = _fake_python_without_dbus(tmp_path)
    custom_import = tmp_path / "custom-bin" / "magick-import"
    custom_import.parent.mkdir(parents=True)
    custom_import.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
    custom_import.chmod(0o755)

    install = _run_script(
        "install-local.sh",
        tmp_path,
        use_fake_command=False,
        extra_env={
            "XDG_SESSION_TYPE": "",
            "SPECTACLE_TOOLBELT_PYTHON_CANDIDATES": str(fake_python),
            "SPECTACLE_TOOLBELT_IMPORT_COMMAND": str(custom_import),
        },
    )

    assert install.returncode == 0, install.stderr
    wrapper = tmp_path / "spectacle-toolbelt" / "bin" / "spectacle-toolbelt"
    assert wrapper.exists()
    wrapper_content = wrapper.read_text(encoding="utf-8")
    assert f"exec '{fake_python}' -m spectacle_toolbelt.cli" in wrapper_content


def test_installer_wrapper_honors_configured_imagemagick_import_on_x11(tmp_path) -> None:
    fake_python = _fake_python_without_dbus(tmp_path)
    custom_import = tmp_path / "custom-bin" / "magick-import"
    custom_import.parent.mkdir(parents=True)
    custom_import.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
    custom_import.chmod(0o755)

    install = _run_script(
        "install-local.sh",
        tmp_path,
        use_fake_command=False,
        extra_env={
            "XDG_SESSION_TYPE": "x11",
            "SPECTACLE_TOOLBELT_PYTHON_CANDIDATES": str(fake_python),
            "SPECTACLE_TOOLBELT_IMPORT_COMMAND": str(custom_import),
        },
    )

    assert install.returncode == 0, install.stderr
    wrapper = tmp_path / "spectacle-toolbelt" / "bin" / "spectacle-toolbelt"
    wrapper_content = wrapper.read_text(encoding="utf-8")
    assert f"toolbelt_import_command=${{SPECTACLE_TOOLBELT_IMPORT_COMMAND:-'{custom_import}'}}" in wrapper_content
    assert 'export SPECTACLE_TOOLBELT_IMPORT_COMMAND="$toolbelt_import_command"' in wrapper_content


def test_installer_preserves_owned_wrapper_import_command_on_reinstall(tmp_path) -> None:
    fake_python = _fake_python_without_dbus(tmp_path)
    custom_import = tmp_path / "custom-bin" / "magick-import"
    custom_import.parent.mkdir(parents=True)
    custom_import.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
    custom_import.chmod(0o755)
    wrapper = tmp_path / "spectacle-toolbelt" / "bin" / "spectacle-toolbelt"
    wrapper.parent.mkdir(parents=True)
    wrapper.write_text(
        "#!/usr/bin/env sh\n"
        "# X-Spectacle-Toolbelt-Owned=true\n"
        f"toolbelt_import_command=${{SPECTACLE_TOOLBELT_IMPORT_COMMAND:-'{custom_import}'}}\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)

    install = _run_script(
        "install-local.sh",
        tmp_path,
        use_fake_command=False,
        extra_env={
            "XDG_SESSION_TYPE": "x11",
            "SPECTACLE_TOOLBELT_PYTHON_CANDIDATES": str(fake_python),
        },
    )

    assert install.returncode == 0, install.stderr
    wrapper_content = wrapper.read_text(encoding="utf-8")
    assert f"toolbelt_import_command=${{SPECTACLE_TOOLBELT_IMPORT_COMMAND:-'{custom_import}'}}" in wrapper_content


def test_installer_regenerates_owned_runtime_wrapper_on_reinstall(tmp_path) -> None:
    fake_python = _fake_python_without_dbus(tmp_path)
    custom_import = tmp_path / "custom-bin" / "magick-import"
    custom_import.parent.mkdir(parents=True)
    custom_import.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
    custom_import.chmod(0o755)
    wrapper = tmp_path / "spectacle-toolbelt" / "bin" / "spectacle-toolbelt"
    wrapper.parent.mkdir(parents=True)
    wrapper.write_text(
        "#!/usr/bin/env sh\n"
        "# X-Spectacle-Toolbelt-Owned=true\n"
        "export PYTHONPATH='/old/checkout/src'${PYTHONPATH:+:$PYTHONPATH}\n"
        f"toolbelt_import_command=${{SPECTACLE_TOOLBELT_IMPORT_COMMAND:-'{custom_import}'}}\n"
        f"exec '{fake_python}' -m spectacle_toolbelt.cli \"$@\"\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)

    install = _run_script(
        "install-local.sh",
        tmp_path,
        use_fake_command=False,
        extra_env={
            "XDG_SESSION_TYPE": "x11",
            "SPECTACLE_TOOLBELT_PYTHON_CANDIDATES": str(tmp_path / "missing-python"),
        },
    )

    assert install.returncode == 0, install.stderr
    assert "Could not find a Python runtime" not in install.stderr
    wrapper_content = wrapper.read_text(encoding="utf-8")
    assert "/old/checkout/src" not in wrapper_content
    assert f"export PYTHONPATH='{REPO_ROOT / 'src'}'" in wrapper_content
    assert f"exec '{fake_python}' -m spectacle_toolbelt.cli" in wrapper_content
    assert f"toolbelt_import_command=${{SPECTACLE_TOOLBELT_IMPORT_COMMAND:-'{custom_import}'}}" in wrapper_content
    installed_scroll = tmp_path / "applications" / "io.github.ryanwinkler.spectacle-toolbelt-scroll.desktop"
    assert f"Exec={wrapper} scroll" in installed_scroll.read_text(encoding="utf-8")


def test_installer_rechecks_dependencies_before_regenerating_owned_wrapper(tmp_path) -> None:
    fake_python = _fake_python_without_dbus(tmp_path)
    wrapper = tmp_path / "spectacle-toolbelt" / "bin" / "spectacle-toolbelt"
    wrapper.parent.mkdir(parents=True)
    wrapper.write_text(
        "#!/usr/bin/env sh\n"
        "# X-Spectacle-Toolbelt-Owned=true\n"
        f"exec '{fake_python}' -m spectacle_toolbelt.cli \"$@\"\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)

    install = _run_script(
        "install-local.sh",
        tmp_path,
        use_fake_command=False,
        extra_env={
            "XDG_SESSION_TYPE": "x11",
            "SPECTACLE_TOOLBELT_PYTHON_CANDIDATES": str(tmp_path / "missing-python"),
            "SPECTACLE_TOOLBELT_IMPORT_COMMAND": "definitely-missing-imagemagick-import",
        },
    )

    assert install.returncode == 1
    assert "ImageMagick import is required" in install.stderr


def test_wrapper_skips_scroll_preflight_for_help_only_invocations(tmp_path) -> None:
    fake_python = _fake_python_without_dbus(tmp_path)
    custom_import = tmp_path / "custom-bin" / "magick-import"
    custom_import.parent.mkdir(parents=True)
    custom_import.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
    custom_import.chmod(0o755)

    install = _run_script(
        "install-local.sh",
        tmp_path,
        use_fake_command=False,
        extra_env={
            "XDG_SESSION_TYPE": "x11",
            "SPECTACLE_TOOLBELT_PYTHON_CANDIDATES": str(fake_python),
            "SPECTACLE_TOOLBELT_IMPORT_COMMAND": str(custom_import),
        },
    )

    assert install.returncode == 0, install.stderr
    custom_import.unlink()
    wrapper = tmp_path / "spectacle-toolbelt" / "bin" / "spectacle-toolbelt"
    help_run = subprocess.run(
        [str(wrapper), "scroll", "--help"],
        check=False,
        env={**os.environ, "XDG_SESSION_TYPE": "x11"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    capture_run = subprocess.run(
        [str(wrapper), "scroll", "--manual"],
        check=False,
        env={**os.environ, "XDG_SESSION_TYPE": "x11"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert help_run.returncode == 0, help_run.stderr
    assert capture_run.returncode == 1
    assert "requires ImageMagick import" in capture_run.stderr


def test_wrapper_requires_imagemagick_import_for_unknown_session(tmp_path) -> None:
    fake_python = _fake_python_without_dbus(tmp_path)
    custom_import = tmp_path / "custom-bin" / "magick-import"
    custom_import.parent.mkdir(parents=True)
    custom_import.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
    custom_import.chmod(0o755)

    install = _run_script(
        "install-local.sh",
        tmp_path,
        use_fake_command=False,
        extra_env={
            "XDG_SESSION_TYPE": "",
            "SPECTACLE_TOOLBELT_PYTHON_CANDIDATES": str(fake_python),
            "SPECTACLE_TOOLBELT_IMPORT_COMMAND": str(custom_import),
        },
    )

    assert install.returncode == 0, install.stderr
    custom_import.unlink()
    wrapper = tmp_path / "spectacle-toolbelt" / "bin" / "spectacle-toolbelt"
    capture_run = subprocess.run(
        [str(wrapper), "scroll", "--manual"],
        check=False,
        env={**os.environ, "XDG_SESSION_TYPE": ""},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert capture_run.returncode == 1
    assert "requires ImageMagick import" in capture_run.stderr


def test_installer_runtime_probe_requires_dbus_on_wayland(tmp_path) -> None:
    fake_python = _fake_python_without_dbus(tmp_path)

    install = _run_script(
        "install-local.sh",
        tmp_path,
        "--dry-run",
        use_fake_command=False,
        extra_env={
            "XDG_SESSION_TYPE": "wayland",
            "SPECTACLE_TOOLBELT_PYTHON_CANDIDATES": str(fake_python),
        },
    )

    assert install.returncode == 1
    assert "dbus-python for Wayland fixed-region capture" in install.stderr


def test_install_preserves_existing_usable_path_command(tmp_path) -> None:
    fake_command = tmp_path / "path-bin" / "spectacle-toolbelt"
    fake_command.parent.mkdir(parents=True)
    fake_command.write_text(
        "#!/usr/bin/env sh\n"
        "if [ \"${1:-}\" = \"doctor\" ]; then\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    fake_command.chmod(0o755)

    install = _run_script(
        "install-local.sh",
        tmp_path,
        use_fake_command=False,
        extra_env={
            "PATH": f"{fake_command.parent}{os.pathsep}{os.environ['PATH']}",
            "XDG_SESSION_TYPE": "wayland",
            "SPECTACLE_TOOLBELT_PYTHON_CANDIDATES": str(tmp_path / "missing-python"),
        },
    )

    assert install.returncode == 0, install.stderr
    installed_scroll = tmp_path / "applications" / "io.github.ryanwinkler.spectacle-toolbelt-scroll.desktop"
    assert f"Exec={fake_command} scroll" in installed_scroll.read_text(encoding="utf-8")
    assert not (tmp_path / "spectacle-toolbelt" / "bin" / "spectacle-toolbelt").exists()


def test_install_validates_existing_path_command_against_active_wayland_backend(tmp_path) -> None:
    fake_command = tmp_path / "path-bin" / "spectacle-toolbelt"
    fake_command.parent.mkdir(parents=True)
    fake_command.write_text(
        "#!/usr/bin/env sh\n"
        "if [ \"${1:-}\" = \"doctor\" ]; then\n"
        "  if [ \"${XDG_SESSION_TYPE:-}\" = \"x11\" ]; then\n"
        "    exit 1\n"
        "  fi\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    fake_command.chmod(0o755)

    install = _run_script(
        "install-local.sh",
        tmp_path,
        use_fake_command=False,
        extra_env={
            "PATH": f"{fake_command.parent}{os.pathsep}{os.environ['PATH']}",
            "XDG_SESSION_TYPE": "wayland",
            "SPECTACLE_TOOLBELT_PYTHON_CANDIDATES": str(tmp_path / "missing-python"),
        },
    )

    assert install.returncode == 0, install.stderr
    installed_scroll = tmp_path / "applications" / "io.github.ryanwinkler.spectacle-toolbelt-scroll.desktop"
    assert f"Exec={fake_command} scroll" in installed_scroll.read_text(encoding="utf-8")
    assert not (tmp_path / "spectacle-toolbelt" / "bin" / "spectacle-toolbelt").exists()


def test_install_validates_existing_path_command_against_active_x11_backend(tmp_path) -> None:
    fake_command = tmp_path / "path-bin" / "spectacle-toolbelt"
    fake_command.parent.mkdir(parents=True)
    fake_command.write_text(
        "#!/usr/bin/env sh\n"
        "if [ \"${1:-}\" = \"doctor\" ]; then\n"
        "  if [ \"${XDG_SESSION_TYPE:-}\" = \"x11\" ]; then\n"
        "    exit 1\n"
        "  fi\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    fake_command.chmod(0o755)

    install = _run_script(
        "install-local.sh",
        tmp_path,
        use_fake_command=False,
        extra_env={
            "PATH": f"{fake_command.parent}{os.pathsep}{os.environ['PATH']}",
            "XDG_SESSION_TYPE": "x11",
            "SPECTACLE_TOOLBELT_PYTHON_CANDIDATES": str(tmp_path / "missing-python"),
        },
    )

    assert install.returncode == 1
    assert "Ignoring PATH Toolbelt command without required local capture dependencies" in install.stderr


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


def test_install_refuses_to_overwrite_symlinked_toolbelt_file(tmp_path) -> None:
    dotfiles_dir = tmp_path / "dotfiles"
    dotfiles_dir.mkdir()
    managed_file = dotfiles_dir / "toolbelt-stitch.desktop"
    managed_content = "[Desktop Entry]\nName=Dotfiles Managed\nX-Spectacle-Toolbelt-Owned=true\n"
    managed_file.write_text(managed_content, encoding="utf-8")
    target_dir = tmp_path / "kio" / "servicemenus"
    target_dir.mkdir(parents=True)
    target = target_dir / "io.github.ryanwinkler.spectacle-toolbelt-stitch.desktop"
    target.symlink_to(managed_file)

    install = _run_script("install-local.sh", tmp_path)

    assert install.returncode == 1
    assert "Refusing to overwrite non-Toolbelt file" in install.stderr
    assert target.is_symlink()
    assert managed_file.read_text(encoding="utf-8") == managed_content


def test_install_refuses_to_overwrite_non_toolbelt_wrapper(tmp_path) -> None:
    fake_python = _fake_python_without_dbus(tmp_path)
    custom_import = tmp_path / "custom-bin" / "magick-import"
    custom_import.parent.mkdir(parents=True)
    custom_import.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
    custom_import.chmod(0o755)
    wrapper = tmp_path / "spectacle-toolbelt" / "bin" / "spectacle-toolbelt"
    wrapper.parent.mkdir(parents=True)
    wrapper.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
    wrapper.chmod(0o755)

    install = _run_script(
        "install-local.sh",
        tmp_path,
        use_fake_command=False,
        extra_env={
            "XDG_SESSION_TYPE": "x11",
            "SPECTACLE_TOOLBELT_PYTHON_CANDIDATES": str(fake_python),
            "SPECTACLE_TOOLBELT_IMPORT_COMMAND": str(custom_import),
        },
    )

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


def test_uninstall_requires_exact_toolbelt_marker_line(tmp_path) -> None:
    target_dir = tmp_path / "applications"
    target_dir.mkdir(parents=True)
    target = target_dir / "io.github.ryanwinkler.spectacle-toolbelt.desktop"
    target.write_text(
        "[Desktop Entry]\nComment=mentions X-Spectacle-Toolbelt-Owned=true only\n",
        encoding="utf-8",
    )

    uninstall = _run_script("uninstall-local.sh", tmp_path)

    assert uninstall.returncode == 1
    assert "Refusing to remove non-Toolbelt file" in uninstall.stderr


def test_stitch_service_menu_requires_multiple_files() -> None:
    content = STITCH_SERVICE_MENU.read_text(encoding="utf-8")

    assert "X-KDE-MinNumberOfUrls=2" in content
    assert "X-KDE-MaxNumberOfUrls=24" in content
    assert "Actions=StitchVertical;StitchHorizontal;" in content
    assert "stitch --direction vertical --natural-sort --max-frames 24 --open-in-spectacle %F" in content
    assert "stitch --direction horizontal --natural-sort --max-frames 24 --open-in-spectacle %F" in content


def test_open_in_spectacle_service_menu_requires_one_file() -> None:
    content = OPEN_IN_SPECTACLE_SERVICE_MENU.read_text(encoding="utf-8")

    assert "X-KDE-MaxNumberOfUrls=1" in content


def _fake_python_without_dbus(tmp_path: Path) -> Path:
    fake_python = tmp_path / "fake-bin" / "python3"
    fake_python.parent.mkdir(parents=True, exist_ok=True)
    fake_python.write_text(
        "#!/usr/bin/env bash\n"
        "code=${2:-}\n"
        "if [[ \"$code\" == *\"import dbus\"* ]]; then\n"
        "  exit 1\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    return fake_python
