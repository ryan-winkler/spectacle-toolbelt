# KDE Shortcuts

Date: 2026-04-24

Spectacle already owns native global shortcuts through KGlobalAccel. Toolbelt
must not pretend it can fully replace that integration from the outside.

## Existing Spectacle Shortcut Surface

Spectacle aligns global shortcut action names with actions in its desktop file.
The upstream source currently includes actions for:

- launch Spectacle
- capture entire desktop
- capture current monitor
- capture active window
- capture rectangular region
- capture selected/window under cursor
- start/stop screen recording
- start/stop window recording
- start/stop region recording
- launch Spectacle without capturing

## Toolbelt Bridge Shortcuts

The local Toolbelt installer ships visible desktop entries for bridge workflows
and appends Toolbelt actions to a reversible user-local Spectacle desktop
override. The full-page web capture launcher and Spectacle app action declare
the approved shortcut:

```bash
spectacle-toolbelt web-fullpage
```

Default shortcut:

```text
Ctrl+Alt+W
```

The scrolling capture launcher is also installed and can be bound from KDE
System Settings if desired:

```bash
spectacle-toolbelt scroll
```

Toolbelt does not bind this over Spectacle's normal screenshot shortcuts.

For editing an existing generated image:

```bash
spectacle-toolbelt open-in-spectacle /path/to/image.png
```

## Native Target

When scrolling capture moves upstream, Spectacle should register a native action
such as:

```text
ScrollingCapture
```

That action should be wired the same way as the existing Spectacle desktop
actions and KGlobalAccel entries.
