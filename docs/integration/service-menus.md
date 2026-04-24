# KDE Service Menus

Date: 2026-04-24

Toolbelt installs optional Dolphin/KIO service menus as KDE-standard fallback
surfaces. They do not modify Spectacle files.

## Installed Menus

- `Open in Spectacle Editor`
  - runs `spectacle-toolbelt open-in-spectacle %f`
  - hands the selected image to `spectacle --edit-existing`
  - only appears when exactly one image file is selected

- `Stitch with Spectacle Toolbelt`
  - runs `spectacle-toolbelt stitch %F --open-in-spectacle`
  - intended for multiple pre-captured scroll frames
  - only appears when at least two image files are selected

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
