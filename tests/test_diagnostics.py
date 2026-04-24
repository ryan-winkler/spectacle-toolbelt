from __future__ import annotations

from spectacle_toolbelt.diagnostics import run_doctor


def test_doctor_reports_local_spectacle_launcher_missing_kwin_authorization(monkeypatch, tmp_path) -> None:
    applications = tmp_path / "applications"
    applications.mkdir()
    launcher = applications / "spectacle-launch.desktop"
    launcher.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Spectacle\n"
        "Exec=/usr/bin/spectacle -l\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    report = run_doctor()

    check = next(check for check in report.checks if check.name == "spectacle-launch.desktop KWin authorization")
    assert not check.available
    assert "X-KDE-DBUS-Restricted-Interfaces" in str(check.note)


def test_doctor_accepts_local_spectacle_launcher_with_kwin_authorization(monkeypatch, tmp_path) -> None:
    applications = tmp_path / "applications"
    applications.mkdir()
    launcher = applications / "spectacle-launch.desktop"
    launcher.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Spectacle\n"
        "Exec=/usr/bin/spectacle -l\n"
        "X-KDE-DBUS-Restricted-Interfaces=org.kde.KWin.ScreenShot2\n"
        "X-KDE-Wayland-Interfaces=org_kde_plasma_window_management,zkde_screencast_unstable_v1\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    report = run_doctor()

    check = next(check for check in report.checks if check.name == "spectacle-launch.desktop KWin authorization")
    assert check.available


def test_doctor_checks_user_local_spectacle_desktop_override(monkeypatch, tmp_path) -> None:
    applications = tmp_path / "applications"
    applications.mkdir()
    launcher = applications / "org.kde.spectacle.desktop"
    launcher.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Spectacle\n"
        "Exec=/usr/bin/spectacle\n"
        "X-KDE-DBUS-Restricted-Interfaces=org.kde.KWin.ScreenShot2\n"
        "X-KDE-Wayland-Interfaces=org_kde_plasma_window_management,zkde_screencast_unstable_v1\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    report = run_doctor()

    check = next(check for check in report.checks if check.name == "org.kde.spectacle.desktop KWin authorization")
    assert check.available


def test_doctor_checks_toolbelt_scroll_launcher_authorization(monkeypatch, tmp_path) -> None:
    applications = tmp_path / "applications"
    applications.mkdir()
    launcher = applications / "io.github.ryanwinkler.spectacle-toolbelt-scroll.desktop"
    launcher.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Spectacle Toolbelt Scrolling Capture\n"
        "Exec=spectacle-toolbelt scroll\n"
        "X-KDE-DBUS-Restricted-Interfaces=org.kde.KWin.ScreenShot2\n"
        "X-KDE-Wayland-Interfaces=org_kde_plasma_window_management,zkde_screencast_unstable_v1\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    report = run_doctor()

    check = next(
        check
        for check in report.checks
        if check.name == "io.github.ryanwinkler.spectacle-toolbelt-scroll.desktop KWin authorization"
    )
    assert check.available


def test_doctor_marks_exact_fixed_region_dependencies_required(monkeypatch, tmp_path) -> None:
    applications = tmp_path / "applications"
    applications.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")

    report = run_doctor()

    gtk = next(check for check in report.checks if check.name == "GTK 4/PyGObject")
    import_tool = next(check for check in report.checks if check.name == "import")
    dbus = next(check for check in report.checks if check.name == "dbus-python")
    assert gtk.required
    assert import_tool.required
    assert not dbus.required


def test_doctor_treats_unknown_session_as_x11_fixed_region_backend(monkeypatch, tmp_path) -> None:
    applications = tmp_path / "applications"
    applications.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.delenv("XDG_SESSION_TYPE", raising=False)

    report = run_doctor()

    import_tool = next(check for check in report.checks if check.name == "import")
    dbus = next(check for check in report.checks if check.name == "dbus-python")
    assert import_tool.required
    assert not dbus.required


def test_doctor_honors_configured_imagemagick_import(monkeypatch, tmp_path) -> None:
    custom_import = tmp_path / "custom-bin" / "magick-import"
    custom_import.parent.mkdir(parents=True)
    custom_import.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
    custom_import.chmod(0o755)
    monkeypatch.setenv("SPECTACLE_TOOLBELT_IMPORT_COMMAND", str(custom_import))
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")

    report = run_doctor()

    import_tool = next(check for check in report.checks if check.name == "import")
    assert import_tool.available
    assert import_tool.path == str(custom_import)
