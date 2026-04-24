# KDE-Native Spectacle Toolbelt Integration Design

Date: 2026-04-24
Status: Approved
Owner: Codex

## Goal

Reframe Spectacle Toolbelt so every serious feature is designed for native KDE/Spectacle integration, not as a parallel screenshot app.

The user experience target is Snagit-grade smoothness:

- scrolling capture appears in Spectacle’s capture UI
- the flow uses Spectacle’s existing selection overlay, shortcuts, notifications, annotation editor, OCR, QR scanning, export paths, and global shortcut patterns
- finished captures open in Spectacle’s editor for preview, annotation, OCR, QR scan, copy, save, and sharing workflows
- Toolbelt remains a companion/proving-ground repo, but the intended mature destination for GUI features is upstream Spectacle

## Non-Negotiable Product Direction

- No fork as the long-term product.
- No separate screenshot app as the primary UX.
- No roadmap language that ignores existing Spectacle features.
- No user-facing deferrals hidden behind vague “later” promises.
- No duplicate annotation/OCR/QR features when Spectacle already owns them.
- No feature is considered complete until its GUI/UX path is specified.
- Known optimizations must be either implemented in the milestone or explicitly moved out of scope by product decision, not forgotten.

## Reality Check

Native Spectacle GUI integration cannot be achieved by Python scripts, `.desktop` files, or Dolphin service menus alone.

Those are useful integration surfaces, but they cannot add a polished button, mode, toolbar state, progress affordance, or editor handoff inside Spectacle’s QML UI.

Therefore, a native GUI requirement means the project must have two tracks:

1. **Toolbelt companion track**
   - prototypes workflows quickly
   - provides stitch/scroll algorithms
   - produces diagnostics and fixtures
   - validates UX assumptions with users

2. **Upstream Spectacle track**
   - adds native UI and integration points to `invent.kde.org/plasma/spectacle`
   - follows KDE contribution process
   - uses Spectacle’s existing architecture instead of bypassing it
   - keeps the final user experience inside Spectacle where possible

The companion track is not the product end state. It is the research and integration vehicle.

## What Spectacle Already Has

Toolbelt must treat these as existing Spectacle-owned capabilities:

- capture modes: full desktop, current monitor, active window, window under cursor/selected window, rectangular region
- recording modes: region, screen, window
- CLI/background capture: `--background`, `--region`, `--output`, `--copy-image`, `--copy-path`, `--delay`, `--onclick`
- edit existing image: `spectacle --edit-existing <file>`
- D-Bus capture and recording methods
- `.desktop` actions for capture/recording/open
- KGlobalAccel shortcut integration
- annotation editor
- annotation tools: crop, select, freehand, highlighter, line, arrow, rectangle, ellipse, pixelate, blur, text, number stamp
- OCR action: `Extract Text`
- QR scanning in the export flow
- notifications with open/annotate actions
- KDE release and contribution process through Invent/GitLab

Toolbelt should not duplicate these. Toolbelt should compose with them.

## Snagit Scrolling Capture UX Lessons

Snagit’s scrolling capture has two important modes:

- manual scrolling capture: user selects an area, clicks scrolling capture, scrolls/pans manually, clicks Done, then the editor opens
- automatic scrolling capture: user selects or hovers a scrollable window, arrows appear when automatic scroll is possible, user chooses vertical/horizontal/bidirectional capture, then the editor opens

The Spectacle-native target should mirror the workflow shape, not the branding:

- select region/window using Spectacle’s overlay
- offer a visible scrolling capture affordance in the capture toolbar
- support manual mode first-class, not as an error fallback
- detect when automatic mode is possible
- show vertical/horizontal/bidirectional choices only when supported
- provide a Done/Cancel capture toolbar
- process/stitch with progress and clear partial/failure states
- open the stitched result in Spectacle’s existing editor

## Product Architecture

### Layer 1: Core Algorithm Library

Owned by Toolbelt initially.

Responsibilities:

- frame capture session model
- vertical and horizontal overlap detection
- fixed-header/footer handling
- partial-result classification
- diagnostic JSON
- synthetic test fixtures
- performance benchmarks

Language can remain Python for prototyping, but upstream Spectacle will likely need a C++/Qt implementation or a clearly acceptable helper-process boundary.

### Layer 2: KDE/Spectacle Integration Adapter

Owned by Toolbelt initially, upstreamable where useful.

Responsibilities:

- invoke Spectacle capture paths correctly
- use `spectacle --edit-existing <stitched.png>` for editor handoff
- generate `.desktop` entries and service menus that respect KDE conventions
- document KGlobalAccel shortcut recipes
- avoid owning annotation/OCR/QR flows

### Layer 3: Native Spectacle UX

Owned by upstream Spectacle MRs.

Required GUI additions:

- new capture mode/action: `Scrolling Capture`
- mode placement consistent with Spectacle’s capture mode UI
- capture overlay toolbar action after region/window selection
- manual capture toolbar: capture frame, done, cancel, frame count, confidence/warning indicator
- automatic capture affordance: scroll direction arrows when supported
- processing state after capture
- final handoff to existing annotation editor
- settings entry for default scrolling behavior and max frames/height
- global shortcut action aligned with existing `.desktop`/KGlobalAccel action naming

## Feature Completeness Definition

A feature is not complete when the CLI works.

For each feature, completion requires:

- native or KDE-standard entrypoint
- GUI/UX behavior documented
- interaction with existing Spectacle features documented
- failure states documented
- Wayland/X11 behavior documented
- tests or fixture coverage where practical
- upstream feasibility assessed
- no duplicate implementation of Spectacle-owned features

## Scrolling Capture Complete Scope

Scrolling capture is the first all-inclusive feature and must include:

- manual scrolling capture
- automatic scrolling capture where platform/app support exists
- vertical capture
- horizontal capture
- bidirectional capture if automatic mode supports it
- selected region capture
- selected/window capture where Spectacle can provide the bounds
- progress display
- frame count display
- cancel
- done
- partial output recovery
- fixed-header/footer mitigation
- smooth scroll guidance
- debug diagnostics
- editor handoff through Spectacle
- service menu and CLI fallback
- global shortcut recipe
- upstream Spectacle proposal/MR plan

Known optimizations for the scrolling milestone:

- overlap scoring with confidence thresholds
- exact row matching fast path
- tolerant/pixel-difference matching
- fixed chrome/header detection
- max frame and max height safety caps
- temp-file cleanup
- opt-in debug artifact retention
- large image memory guardrails
- deterministic output names
- clear error messages for Wayland/input limitations

## Documentation Capture Reframe

Current README language says:

> Documentation capture: step markers, click trails, numbered callouts, and markdown export for runbooks and support notes.

This must be corrected.

Spectacle already has number stamps, text, arrows, blur, pixelate, and other annotation tools. Toolbelt should not claim those as missing.

Correct framing:

- Spectacle owns visual annotation.
- Toolbelt adds documentation workflow glue:
  - open generated/stitched images in Spectacle’s editor
  - export Markdown after save/copy
  - generate sidecar metadata for runbooks
  - create consistent file naming and asset paths
  - optionally sequence multiple Spectacle-edited screenshots into a guide

## Integration Surfaces

### Immediate KDE-Standard Surfaces

These can ship in Toolbelt without changing Spectacle:

- CLI commands
- Dolphin/KIO service menus
- KRunner/global shortcut recipes
- `spectacle --edit-existing` handoff
- README integration matrix

### Upstream Spectacle Surfaces

These require Spectacle changes:

- native scrolling capture action in capture UI
- toolbar controls during capture
- automatic scroll arrows
- in-app progress and result state
- global shortcut registration inside Spectacle
- settings UI
- reusable post-capture action hooks if KDE accepts that direction

## Iteration Plan Options

### Option A: External Toolbelt Polishing

Keep Toolbelt external and improve service-menu integration.

Pros:

- fast
- no dependency on KDE review
- useful immediately

Cons:

- does not meet native GUI requirement
- risks becoming parallel UX
- cannot deliver Snagit-grade smoothness inside Spectacle

### Option B: Upstream-First Native Scrolling Capture

Use Toolbelt only as a research harness and focus the next milestone on a Spectacle MR design.

Pros:

- meets native GUI requirement
- respects Spectacle’s existing UX
- avoids duplicated annotation/OCR/QR
- creates the cleanest long-term product

Cons:

- slower
- requires C++/Qt/QML/KDE review
- upstream acceptance is not fully under our control

### Option C: Hybrid Track

Proceed with both:

- Toolbelt adds KDE-standard fallback surfaces now
- parallel upstream Spectacle design/MR work begins immediately
- Toolbelt README clearly states the external UX is a bridge, not the goal

Pros:

- useful now
- honest about native GUI path
- creates test fixtures and evidence for upstream
- keeps momentum while respecting KDE architecture

Cons:

- more coordination
- must avoid overbuilding external UX that should live upstream

## Recommendation

Use Option C.

The next milestone should be:

**Native Scrolling Capture Design + KDE Integration Correction**

Deliverables:

- correct Toolbelt README to acknowledge Spectacle-owned annotation/OCR/QR features
- add `spectacle --edit-existing` as the default post-stitch handoff
- add Dolphin/KIO service menus
- add KGlobalAccel/global shortcut documentation
- add an upstream Spectacle design proposal for native scrolling capture
- map exact Spectacle source files likely affected
- keep Toolbelt’s stitch engine as the algorithm harness
- do not add new duplicate annotation/OCR/QR implementations

## Likely Upstream Spectacle Touch Points

Based on the current Spectacle source layout:

- `src/CaptureModeModel.*`
- `src/ShortcutActions.*`
- `desktop/org.kde.spectacle.desktop.cmake`
- `dbus/org.kde.Spectacle.xml`
- `src/SpectacleDBusAdapter.*`
- `src/SpectacleCore.*`
- `src/Gui/CaptureModeButtonsColumn.qml`
- `src/Gui/CaptureOverlay.qml`
- `src/Gui/SelectionEditor.*`
- `src/Gui/ViewerPage.qml`
- `src/Gui/AnnotationEditor.qml`
- `src/Gui/ExportMenu.*`
- settings files under `src/Gui/SettingsDialog/`

This list must be validated through a dedicated upstream code-reading pass before implementation.

## Review Questions

1. Do we accept that “native GUI” means upstream Spectacle changes, not just Toolbelt scripts?
2. Should Toolbelt’s next pushed change be a README/service-menu correction, or should we first open a dedicated upstream design issue/proposal?
3. Should the scrolling implementation target manual mode and automatic mode in one upstream proposal, or split them into separate MRs while keeping the same product milestone?

## Sources

- KDE Spectacle upstream: `https://invent.kde.org/plasma/spectacle`
- Local upstream snapshot inspected: `75386fdfbcbe7184ec66fff0f140e76662a53779`
- Snagit scrolling capture tutorial: `https://www.techsmith.com/learn/tutorials/snagit/scrolling-capture/`
