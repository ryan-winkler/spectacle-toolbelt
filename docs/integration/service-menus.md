# KDE Service Menus

Date: 2026-04-24

Toolbelt installs visible KDE launchers, Spectacle launcher app actions, and
optional Dolphin/KIO service menus as KDE-standard fallback surfaces. It does
not modify Spectacle's system files.

## Installed Launchers

- `Spectacle Toolbelt`
  - runs `spectacle-toolbelt guide`
  - opens a KDE dialog explaining the launchers, Dolphin actions, and CLI
    equivalents
  - exists so KRunner/application-launcher users have an obvious entry point

- `Spectacle Toolbelt Scrolling Capture`
  - runs `spectacle-toolbelt scroll`
  - starts the visible scrolling capture workflow
  - presents mode selection, Capture Next, Done, Cancel, frame count, and
    Spectacle editor handoff

- `Spectacle Toolbelt Full-Page Web Capture`
  - runs `spectacle-toolbelt web-fullpage`
  - tries active Chromium-family tab metadata, then prompts for a URL
  - declares `X-KDE-Shortcuts=Ctrl+Alt+W`

## Spectacle App Actions

The installer creates a user-local `org.kde.spectacle.desktop` override by
copying Spectacle's system desktop file, preserving its KWin authorization
metadata, and appending Toolbelt actions:

- `Scrolling Capture`
  - runs `spectacle-toolbelt scroll`
  - appears from Spectacle's launcher/task-manager context menu

- `Full-Page Web Capture`
  - runs `spectacle-toolbelt web-fullpage`
  - appears from Spectacle's launcher/task-manager context menu
  - declares `X-KDE-Shortcuts=Ctrl+Alt+W`

Uninstalling removes only this Toolbelt-owned local override. KDE then falls
back to the system Spectacle desktop file.

## Installed Menus

- `Open in Spectacle Editor`
  - runs `spectacle-toolbelt open-in-spectacle %f`
  - hands the selected image to `spectacle --edit-existing`
  - only appears when exactly one image file is selected

- `Stitch with Spectacle Toolbelt`
  - runs `spectacle-toolbelt stitch --natural-sort --max-frames 24 --open-in-spectacle %F`
  - intended for multiple pre-captured scroll frames
  - only appears when 2-24 image files are selected
  - sorts selected image filenames naturally before stitching

## Install Location

User-local service menus live under:

```text
$XDG_DATA_HOME/kio/servicemenus
```

For Plasma 5/KF5, Toolbelt also installs them under:

```text
$XDG_DATA_HOME/kservices5/ServiceMenus
```

If `XDG_DATA_HOME` is unset, Toolbelt uses:

```text
~/.local/share/kio/servicemenus
~/.local/share/kservices5/ServiceMenus
```

## Safety Rule

Install and uninstall scripts only overwrite or remove files that contain:

```text
X-Spectacle-Toolbelt-Owned=true
```

Installed entries use the resolved Toolbelt executable path instead of relying
on Dolphin or KIO inheriting a shell virtualenv. The installer refreshes KDE's
service cache automatically when `kbuildsycoca6` or `kbuildsycoca5` is
available.
