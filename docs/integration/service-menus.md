# KDE Service Menus

Date: 2026-04-24

Toolbelt installs a visible KDE launcher plus optional Dolphin/KIO service
menus as KDE-standard fallback surfaces. They do not modify Spectacle files.

## Installed Launcher

- `Spectacle Toolbelt`
  - runs `spectacle-toolbelt guide`
  - opens a KDE dialog explaining the Dolphin actions and CLI equivalents
  - exists so KRunner/application-launcher users have an obvious entry point

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
