# Native Scrolling Capture Proposal For KDE Spectacle

Date: 2026-04-24
Status: Draft proposal
Upstream: `https://invent.kde.org/plasma/spectacle`
Source snapshot inspected: `75386fdfbcbe7184ec66fff0f140e76662a53779`

## Problem

Spectacle is the KDE-native screenshot tool and already owns capture, editing,
annotation, OCR, QR scanning, desktop actions, D-Bus, notifications, and global
shortcuts. The missing workflow is native scrolling capture for content that
extends beyond the visible viewport.

Users currently need external tools or manual stitching to capture:

- long web pages
- documents
- settings panes
- terminal/log output
- file lists
- wide spreadsheets or tables

## Product Requirement

Scrolling capture should feel native to Spectacle, not like a separate utility.

The complete feature includes:

- manual scrolling capture
- automatic scrolling capture where platform/app support exists
- vertical capture
- horizontal capture
- bidirectional capture where supported
- selected region capture
- selected/window capture where bounds are available
- progress state
- frame count
- Done
- Cancel
- partial output recovery
- fixed-header/footer mitigation
- confidence/warning state
- debug diagnostics where appropriate
- handoff to Spectacle’s existing editor
- KGlobalAccel and desktop action integration

## Existing Spectacle Capabilities To Reuse

- capture modes through `CaptureModeModel`
- global shortcut naming through `ShortcutActions`
- desktop actions in `desktop/org.kde.spectacle.desktop.cmake`
- D-Bus interface in `dbus/org.kde.Spectacle.xml`
- capture orchestration in `SpectacleCore`
- region/window selection through existing GUI components
- existing annotation document/editor
- OCR action
- QR scan/export flow
- notifications and open/annotate behavior

## Proposed UX

### Manual Mode

1. User chooses `Scrolling Capture`.
2. Spectacle shows the normal region/window selection overlay.
3. User selects the scrollable area.
4. A capture toolbar appears with:
   - Capture Frame
   - Done
   - Cancel
   - frame count
   - confidence/warning indicator
5. User scrolls or pans one direction at a time.
6. Spectacle captures frames.
7. User clicks Done.
8. Spectacle stitches frames.
9. Spectacle opens the stitched result in the existing editor.

### Automatic Mode

1. User chooses `Scrolling Capture`.
2. User selects or hovers a scrollable target.
3. If automatic scrolling is available, Spectacle shows direction controls:
   - vertical
   - horizontal
   - both
4. User picks a direction.
5. Spectacle scrolls, captures, stitches, and shows progress.
6. Spectacle opens the complete or partial result in the editor.

## Proposed Source Touch Points

Initial source map to validate during implementation:

- `src/CaptureModeModel.cpp`
- `src/CaptureModeModel.h`
- `src/ShortcutActions.cpp`
- `src/ShortcutActions.h`
- `desktop/org.kde.spectacle.desktop.cmake`
- `dbus/org.kde.Spectacle.xml`
- `src/SpectacleDBusAdapter.cpp`
- `src/SpectacleDBusAdapter.h`
- `src/SpectacleCore.cpp`
- `src/SpectacleCore.h`
- `src/Gui/CaptureModeButtonsColumn.qml`
- `src/Gui/CaptureOverlay.qml`
- `src/Gui/SelectionEditor.cpp`
- `src/Gui/SelectionEditor.h`
- `src/Gui/ViewerPage.qml`
- `src/Gui/ExportMenu.cpp`
- `src/Gui/ExportMenu.h`
- `src/Gui/SettingsDialog/GeneralOptions.ui`
- `src/Gui/SettingsDialog/GeneralOptionsPage.cpp`
- `src/Gui/SettingsDialog/spectacle.kcfg`

Likely new files:

- `src/ScrollingCaptureSession.cpp`
- `src/ScrollingCaptureSession.h`
- `src/Gui/ScrollingCaptureToolbar.qml`
- `tests/ScrollingStitchTest.cpp`

## Algorithm Requirements

- exact row/column overlap fast path
- tolerant pixel-difference scoring
- vertical and horizontal joins
- bidirectional session model
- fixed-header/footer crop hints
- maximum frame count
- maximum output dimensions
- partial-result classification
- deterministic diagnostics
- cleanup of temporary frames by default

## Wayland And X11 Policy

Manual mode should be first-class everywhere.

Automatic mode must be capability-driven. On Wayland, arbitrary input injection
may be blocked by compositor and portal rules. Spectacle should not claim
automatic scrolling when the platform, app, or toolkit does not support it.

## Accessibility And I18n

- All new visible strings must use KDE i18n conventions.
- Toolbar actions need keyboard-accessible controls.
- Progress and failure state must be visible without relying only on color.
- Direction controls must have text labels/tooltips, not only arrows.

## Test Plan

- stitch unit tests for vertical overlap
- stitch unit tests for horizontal overlap
- duplicate/end-of-scroll detection
- no-overlap partial result
- width/height mismatch failure
- fixed-header mitigation fixture
- max frame/output cap
- manual mode smoke test
- automatic mode capability detection test where feasible

## Proposed MR Split

The product milestone is complete scrolling capture, but KDE review may require
small merge requests:

1. Add action/model/shortcut/desktop plumbing.
2. Add scrolling session backend and algorithm tests.
3. Add QML capture toolbar and UX states.
4. Add settings and documentation.

Each MR should avoid duplicating Spectacle’s existing annotation, OCR, or QR
features.

## Open Questions For KDE

- Should the stitch algorithm live fully inside Spectacle or call a helper?
- What automatic scrolling mechanisms are acceptable on Plasma Wayland?
- Should scrolling capture expose a D-Bus method immediately or only after GUI maturity?
- How should debug diagnostics be surfaced to users and bug reports?
- Should bidirectional capture be part of the first MR series or guarded behind capability detection?
