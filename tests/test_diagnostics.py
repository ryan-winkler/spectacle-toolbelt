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
