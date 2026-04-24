# KDE Service Menus

Date: 2026-04-24

Toolbelt installs optional Dolphin/KIO service menus as KDE-standard fallback
surfaces. They do not modify Spectacle files.

## Installed Menus

- `Open in Spectacle Editor`
  - runs `spectacle-toolbelt open-in-spectacle %f`
  - hands the selected image to `spectacle --edit-existing`

- `Stitch with Spectacle Toolbelt`
  - runs `spectacle-toolbelt stitch %F --open-in-spectacle`
  - intended for multiple pre-captured scroll frames

## Install Location

User-local service menus live under:

```text
$XDG_DATA_HOME/kio/servicemenus
```

If `XDG_DATA_HOME` is unset, Toolbelt uses:

```text
~/.local/share/kio/servicemenus
```

## Safety Rule

Install and uninstall scripts only overwrite or remove files that contain:

```text
X-Spectacle-Toolbelt-Owned=true
```
