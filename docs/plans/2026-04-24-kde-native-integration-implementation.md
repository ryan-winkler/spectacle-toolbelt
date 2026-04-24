# KDE-Native Spectacle Toolbelt Integration Implementation Plan

Date: 2026-04-24
Status: Approved design, ready for execution
Owner: Codex
Spec: `docs/specs/2026-04-24-kde-native-integration-design.md`

## Goal

Move Spectacle Toolbelt from “external companion scripts” toward a KDE-native integration path where serious features, starting with scrolling capture, appear in Spectacle’s GUI and reuse Spectacle’s existing capabilities.

This plan covers the full known work, not just the fast external fallback:

- correct Toolbelt’s public positioning so it no longer ignores Spectacle-owned annotation/OCR/QR/editor features
- add KDE-standard Toolbelt fallback surfaces that compose with Spectacle
- make `spectacle --edit-existing` the default post-stitch editor handoff
- add Dolphin/KIO service menus and shortcut documentation
- produce an upstream-ready Spectacle scrolling capture proposal
- prepare a Spectacle implementation worktree and source map
- implement the all-inclusive scrolling capture capability across Toolbelt harness and Spectacle-native UI work

## Architectural Approach

Use a two-repo hybrid track.

### Toolbelt Repo

Path:

`/home/ryan/code/spectacle-toolbelt`

Purpose:

- algorithm harness
- external fallback integration
- docs and proposal artifacts
- deterministic test fixtures and diagnostics
- bridge UX until upstream Spectacle carries native GUI support

### Spectacle Upstream Worktree

Planned path:

`/home/ryan/code/spectacle-native-scroll`

Source:

`https://invent.kde.org/plasma/spectacle`

Purpose:

- native Spectacle GUI changes
- C++/Qt/QML implementation
- KDE Invent MR candidate
- KGlobalAccel/desktop action integration

## Files To Create Or Modify

### Toolbelt

- `README.md`
- `docs/specs/2026-04-24-kde-native-integration-design.md`
- `docs/plans/2026-04-24-kde-native-integration-implementation.md`
- `docs/upstream/spectacle-native-scrolling-capture-proposal.md`
- `docs/integration/spectacle-feature-map.md`
- `docs/integration/kde-shortcuts.md`
- `docs/integration/service-menus.md`
- `docs/integration/ux-flow-scrolling-capture.md`
- `src/spectacle_toolbelt/cli.py`
- `src/spectacle_toolbelt/capture/spectacle_adapter.py`
- `src/spectacle_toolbelt/desktop/service_menu.py`
- `src/spectacle_toolbelt/output/editor_handoff.py`
- `src/spectacle_toolbelt/scroll/stitch_engine.py`
- `src/spectacle_toolbelt/scroll/session.py`
- `desktop/io.github.ryanwinkler.spectacle-toolbelt.desktop`
- `servicemenus/io.github.ryanwinkler.spectacle-toolbelt-stitch.desktop`
- `servicemenus/io.github.ryanwinkler.spectacle-toolbelt-open-in-spectacle.desktop`
- `scripts/install-local.sh`
- `scripts/uninstall-local.sh`
- `tests/test_cli.py`
- `tests/test_editor_handoff.py`
- `tests/test_service_menu_install.py`
- `tests/test_stitch_engine.py`

### Spectacle Upstream Candidate

Exact paths to validate before editing:

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
- new likely files:
  - `src/ScrollingCaptureSession.cpp`
  - `src/ScrollingCaptureSession.h`
  - `src/Gui/ScrollingCaptureToolbar.qml`
  - `tests/ScrollingStitchTest.cpp`

## Execution Phases

### Phase 1: Correct Public Positioning

Goal:

Make the public repo honest about Spectacle’s existing feature ownership and the native GUI destination.

Steps:

1. Update `README.md`.
   - Replace “Toolbelt handles OCR/redaction/documentation capture” language with “Toolbelt orchestrates around Spectacle-owned annotation/OCR/QR/editor surfaces.”
   - Add a `What Spectacle Already Owns` section.
   - Add a `Native GUI Direction` section.
   - State that external desktop/service-menu UX is a bridge, not the final product.

2. Add `docs/integration/spectacle-feature-map.md`.
   - Map each proposed Toolbelt feature to:
     - Spectacle-owned capability
     - Toolbelt harness responsibility
     - upstream Spectacle target, if any
   - Include annotation tools, OCR, QR, desktop actions, D-Bus, shortcuts, and `--edit-existing`.

3. Add `docs/integration/ux-flow-scrolling-capture.md`.
   - Document manual and automatic flows based on the approved spec.
   - Include Snagit-inspired steps without copying Snagit UI.
   - Include Done, Cancel, progress, frame count, confidence, partial recovery, and Spectacle editor handoff.

Verification:

```bash
rg "Spectacle already|Native GUI|edit-existing|OCR|QR|number stamp" README.md docs/integration
rg "future OCR workflows|Documentation capture: step markers" README.md && exit 1 || true
```

### Phase 2: Spectacle Editor Handoff

Goal:

Make post-stitch flow open in Spectacle’s native editor by default or by explicit flag.

Steps:

1. Add `src/spectacle_toolbelt/output/editor_handoff.py`.
   - Implement `build_edit_existing_command(path: Path) -> tuple[str, ...]`.
   - Implement `open_in_spectacle(path: Path) -> None`.
   - Validate that the file exists before invoking Spectacle.
   - Return structured errors, no raw tracebacks for CLI users.

2. Update `src/spectacle_toolbelt/cli.py`.
   - Add `spectacle-toolbelt stitch --open-in-spectacle`.
   - Add `spectacle-toolbelt open-in-spectacle IMAGE`.
   - On success, print the exact handoff state.

3. Add tests in `tests/test_editor_handoff.py` and `tests/test_cli.py`.
   - Command construction uses `spectacle --new-instance --edit-existing <file>` or the verified equivalent.
   - Missing files produce controlled errors.
   - CLI exposes the command in help output.

Verification:

```bash
.venv/bin/python -m pytest tests/test_editor_handoff.py tests/test_cli.py
.venv/bin/python -m spectacle_toolbelt.cli stitch --help | rg "open-in-spectacle"
.venv/bin/python -m spectacle_toolbelt.cli open-in-spectacle --help
```

### Phase 3: KDE Service Menus And Shortcut Recipes

Goal:

Install KDE-standard context-menu and shortcut surfaces without touching Spectacle files.

Steps:

1. Add `servicemenus/io.github.ryanwinkler.spectacle-toolbelt-stitch.desktop`.
   - Mime types: PNG, JPEG, WebP where supported by Pillow.
   - Action: stitch selected images into a long screenshot.
   - Use Toolbelt-owned marker.

2. Add `servicemenus/io.github.ryanwinkler.spectacle-toolbelt-open-in-spectacle.desktop`.
   - Action: open selected image in Spectacle annotation editor.
   - Use `spectacle-toolbelt open-in-spectacle %f`.

3. Update `scripts/install-local.sh` and `scripts/uninstall-local.sh`.
   - Install desktop files to `$XDG_DATA_HOME/applications`.
   - Install service menus to `$XDG_DATA_HOME/kio/servicemenus`.
   - Refuse to overwrite or remove non-Toolbelt files.
   - Keep `--dry-run`.

4. Add `src/spectacle_toolbelt/desktop/service_menu.py`.
   - Centralize expected install targets for tests.

5. Add `docs/integration/service-menus.md`.
   - Explain Dolphin/KIO service menu usage and limitations.

6. Add `docs/integration/kde-shortcuts.md`.
   - Document Spectacle’s existing global shortcuts.
   - Document how to assign a Toolbelt bridge shortcut.
   - Explicitly state native shortcut registration belongs upstream in Spectacle.

7. Add tests in `tests/test_service_menu_install.py`.
   - Dry-run does not write.
   - Temp `XDG_DATA_HOME` install/uninstall round trip works.
   - Non-Toolbelt target files are not overwritten or removed.

Verification:

```bash
bash -n scripts/install-local.sh scripts/uninstall-local.sh
desktop-file-validate desktop/*.desktop
rg "Type=Service|ServiceTypes=KonqPopupMenu/Plugin|X-Spectacle-Toolbelt-Owned=true" servicemenus/*.desktop
tmpdir=$(mktemp -d); XDG_DATA_HOME="$tmpdir" bash scripts/install-local.sh; find "$tmpdir" -type f | sort; XDG_DATA_HOME="$tmpdir" bash scripts/uninstall-local.sh; find "$tmpdir" -type f | sort; rm -rf "$tmpdir"
.venv/bin/python -m pytest tests/test_service_menu_install.py
```

### Phase 4: Scrolling Engine Completeness

Goal:

Bring Toolbelt’s stitch harness up to the approved complete scrolling-capture scope so it can inform upstream Spectacle implementation.

Steps:

1. Add `src/spectacle_toolbelt/scroll/session.py`.
   - Model frame order, direction, viewport size, max frame count, max output height, status, diagnostics, and temp file ownership.

2. Extend `src/spectacle_toolbelt/scroll/stitch_engine.py`.
   - vertical and horizontal stitching
   - bidirectional session representation
   - tolerant pixel-difference scoring
   - fixed-header/footer crop hints
   - large image guardrails
   - deterministic diagnostic output
   - partial-result recovery states

3. Expand `tests/test_stitch_engine.py`.
   - vertical exact overlap
   - horizontal exact overlap
   - bidirectional session metadata
   - fixed-header mitigation fixture
   - low-confidence partial recovery
   - max output height guard
   - large image guard
   - debug JSON stability

4. Update CLI.
   - Expose `--direction vertical|horizontal|both`.
   - Expose `--fixed-header-rows`.
   - Expose `--max-height` and `--max-frames`.

Verification:

```bash
.venv/bin/python -m pytest tests/test_stitch_engine.py tests/test_cli.py
.venv/bin/python -m spectacle_toolbelt.cli stitch --help | rg "direction|fixed-header|max-height|max-frames"
```

### Phase 5: Upstream Spectacle Proposal

Goal:

Create a KDE Invent-ready proposal that is grounded in Spectacle’s source tree and contribution style.

Steps:

1. Add `docs/upstream/spectacle-native-scrolling-capture-proposal.md`.
   - Problem statement
   - User flows
   - Existing Spectacle capabilities reused
   - Proposed UI changes
   - Proposed C++/QML architecture
   - Wayland/X11 behavior
   - Accessibility/i18n notes
   - Test plan
   - Open upstream questions

2. Add exact source map.
   - Use the current upstream commit hash.
   - Map each proposed change to a file and class/QML component.
   - Identify the smallest MR split that still preserves the complete product milestone.

3. Validate with source reads.
   - Confirm capture mode model shape.
   - Confirm shortcut action naming.
   - Confirm annotation editor handoff path.
   - Confirm D-Bus extension feasibility.

Verification:

```bash
rg "CaptureModeModel|ShortcutActions|SelectionEditor|SpectacleCore|KGlobalAccel|D-Bus|Wayland|i18n" docs/upstream/spectacle-native-scrolling-capture-proposal.md
rg "75386fdfbcbe7184ec66fff0f140e76662a53779" docs/upstream/spectacle-native-scrolling-capture-proposal.md
```

### Phase 6: Prepare Spectacle Native Worktree

Goal:

Create a dedicated worktree/clone for upstream implementation without contaminating Toolbelt.

Steps:

1. Create `/home/ryan/code/spectacle-native-scroll`.
   - Clone from `https://invent.kde.org/plasma/spectacle`.
   - Create branch `feature/native-scrolling-capture`.

2. Verify build prerequisites and baseline tests.
   - Read upstream `README.md` and `CONTRIBUTING.md`.
   - Identify build command using KDE tooling available locally.
   - If full build is unavailable, record exact blocker in Toolbelt proposal docs.

3. Create upstream implementation plan inside Toolbelt or Spectacle branch.
   - File: `docs/upstream/native-scrolling-capture-implementation-plan.md` in Toolbelt, unless KDE repo has a better local-only planning convention.

Verification:

```bash
git -C /home/ryan/code/spectacle-native-scroll status --short
git -C /home/ryan/code/spectacle-native-scroll branch --show-current
```

### Phase 7: Native Spectacle Implementation

Goal:

Implement scrolling capture inside Spectacle’s GUI with no known UX optimizations omitted from the approved feature scope.

Steps:

1. Add native capture mode/action.
   - Update `src/CaptureModeModel.*`.
   - Update `src/ShortcutActions.*`.
   - Update `desktop/org.kde.spectacle.desktop.cmake`.

2. Add session/backend implementation.
   - Add `src/ScrollingCaptureSession.*`.
   - Implement frame accumulation, overlap scoring, max caps, partial states, and diagnostics.
   - Port the Toolbelt algorithm or justify a Qt-native equivalent.

3. Add QML capture UX.
   - Add `src/Gui/ScrollingCaptureToolbar.qml`.
   - Update `src/Gui/CaptureOverlay.qml` and related selection UI.
   - Include Done, Cancel, progress, frame count, confidence warning.

4. Add editor handoff.
   - Reuse existing annotation document/editor path.
   - Do not create a parallel editor.

5. Add settings.
   - Update settings UI and config for defaults: mode, max frames, max height, debug retention if accepted.

6. Add tests.
   - Add algorithm/unit tests for stitching.
   - Add any available QML/UI smoke tests consistent with Spectacle’s test setup.

Verification:

Use the exact build/test commands discovered in Phase 6. Minimum target:

```bash
cmake --build <build-dir>
ctest --test-dir <build-dir> --output-on-failure
```

If local full build is blocked by KDE environment constraints, the blocker must be documented with exact missing package/tool output before any upstream MR claim.

## Commit Boundaries

### Toolbelt

1. `docs: align roadmap with native spectacle integration`
   - spec, plan, README correction, feature map, UX docs

2. `feat: add spectacle editor handoff`
   - CLI handoff, editor helper, tests

3. `feat: add kde service menu integration`
   - service menus, installer updates, docs, tests

4. `feat: complete scrolling stitch harness`
   - session model, stitch engine enhancements, tests

5. `docs: draft upstream spectacle scrolling proposal`
   - upstream proposal and source map

### Spectacle Upstream Candidate

Split MRs should be small enough for KDE review, but the product milestone remains complete:

1. native action/model/shortcut plumbing
2. scrolling session backend and tests
3. QML capture toolbar and UX states
4. settings and documentation

## Required Verification Before Claiming Completion

Toolbelt:

```bash
cd /home/ryan/code/spectacle-toolbelt
.venv/bin/python -m compileall src tests
.venv/bin/python -m pytest
.venv/bin/python -m spectacle_toolbelt.cli --help
.venv/bin/python -m spectacle_toolbelt.cli doctor
desktop-file-validate desktop/*.desktop
rg "Type=Service|ServiceTypes=KonqPopupMenu/Plugin|X-Spectacle-Toolbelt-Owned=true" servicemenus/*.desktop
bash scripts/install-local.sh --dry-run
bash scripts/uninstall-local.sh --dry-run
```

Spectacle:

```bash
cd /home/ryan/code/spectacle-native-scroll
git status --short
cmake --build <build-dir>
ctest --test-dir <build-dir> --output-on-failure
```

GitHub/GitLab:

```bash
gh repo view ryan-winkler/spectacle-toolbelt --json url,pushedAt
```

For KDE Invent, use KDE’s documented GitLab workflow after authentication and remote setup are confirmed.

## Stop Conditions

Stop and report clearly if:

- Spectacle upstream build cannot be configured locally.
- KDE Invent authentication is unavailable.
- Wayland capture/input restrictions block an automatic-scrolling claim.
- a proposed feature duplicates Spectacle annotation/OCR/QR instead of integrating with it.
- a GUI feature cannot be represented natively without an upstream architectural decision.

## First Execution Recommendation

Start with Phases 1-3 in Toolbelt.

Reason:

- they immediately correct the public repo
- they do not conflict with future upstream work
- they make current Toolbelt outputs flow back into Spectacle’s editor
- they establish KDE-native integration surfaces before deeper algorithm and upstream implementation work
