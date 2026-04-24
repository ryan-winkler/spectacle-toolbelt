# Snagit-Grade Scrolling And Full-Page Capture Design

Date: 2026-04-24
Status: Approved for planning
Owner: Codex

## Goal

Make Spectacle Toolbelt match or exceed the useful parts of Snagit and ShareX
without hijacking normal Spectacle screenshots.

The product must have three separate capture modes:

1. **Normal Spectacle Capture**
   - Existing Spectacle shortcuts and actions stay normal.
   - No scrolling behavior is implied.
   - Toolbelt does not intercept, wrap, or replace standard screenshots.

2. **Full-Page Web Capture**
   - A dedicated shortcut captures the active browser tab end-to-end.
   - The approved default shortcut is `Ctrl+Alt+W`, matching the current local
     full-page web capture convention.
   - If active-tab detection fails, Toolbelt prompts for a URL as a fallback.

3. **Scrolling Capture**
   - A dedicated Snagit/ShareX-style mode captures scrollable app or browser
     content after the user explicitly asks for scrolling capture.
   - It supports automatic scrolling where the desktop, browser, toolkit, and
     permissions make that possible.
   - It supports manual/panoramic scrolling as a first-class fallback, not as a
     degraded error state.

## Product Principle

Every capture should not be forced to scroll.

Scrolling capture is a capture mode, not a replacement for screenshots. The
user should always know whether they are doing a normal screenshot, a full-page
webpage capture, or a scrolling capture session.

## Competitive Baseline

### Snagit

The Snagit workflow separates normal capture from scrolling capture. Its manual
scrolling capture flow lets the user select an area, choose scrolling capture,
scroll or pan, click Done, and then open the result in the editor. Its automatic
flow shows direction arrows when a scrollable target is detected and then opens
the result in the editor.

Toolbelt/Spectacle should match the workflow shape:

- selection first
- explicit scrolling affordance
- manual and automatic modes
- vertical, horizontal, and bidirectional options where supported
- Done and Cancel controls
- editor handoff after processing

### ShareX

ShareX exposes scrolling capture as a dedicated menu/hotkey action. It selects
a region, scrolls and captures until the end, combines images, then shows a
status indicator:

- green for success
- yellow for partial success
- red for failure

Toolbelt/Spectacle should exceed this by keeping the final editing, OCR, QR,
copy, save, and share path inside Spectacle instead of making a parallel editor.

### Existing Local Full-Page Web Capture

The current local desktop shortcut `screenshot-web-fullpage.desktop` already
claims `Ctrl+Alt+W` for full-page web capture. That workflow is valuable, but
it currently prompts for a URL. The approved UX changes the default behavior:

- first try the active browser tab
- prompt for a URL only when active-tab detection fails or is unavailable

## Non-Goals

- Do not replace Spectacle's normal screenshot shortcuts.
- Do not make every capture a scrolling capture.
- Do not duplicate Spectacle's annotation, OCR, QR, copy, save, or share UI.
- Do not require users to pre-capture frames for the primary scrolling UX.
- Do not claim automatic scrolling works everywhere on Wayland.
- Do not expose arbitrary ImageMagick or shell command templates.

## Entry Points

### Normal Capture

Owned by Spectacle.

Examples:

- `Print`
- `Meta+Shift+S`
- Spectacle's built-in desktop actions
- Spectacle's capture mode list

Toolbelt must not install shortcuts that shadow these with scrolling behavior.

### Full-Page Web Capture

Owned by Toolbelt as a companion workflow.

Default behavior:

1. User presses `Ctrl+Alt+W`.
2. Toolbelt identifies the active browser and current tab URL.
3. Toolbelt captures the full page using a browser automation backend.
4. Toolbelt writes a PNG to the Spectacle screenshots folder.
5. Toolbelt copies the PNG to the clipboard when clipboard support exists.
6. Toolbelt shows a notification with Open, Show in Folder, and Open in
   Spectacle Editor actions where the desktop supports them.

Fallback behavior:

1. If active-tab detection fails, Toolbelt opens a URL prompt.
2. User enters or confirms a URL.
3. Toolbelt captures that page using the same full-page backend.

Supported browser target for the first implementation:

- Chromium/Chrome on KDE Plasma Wayland.

Compatibility requirements for this milestone:

- Firefox full-page capture through the URL prompt fallback.
- A documented browser extension/native messaging bridge contract for Firefox
  and Chromium-family active-tab handoff when desktop-owned tab discovery is not
  reliable.

### Scrolling Capture

Owned by Toolbelt as a harness and upstream Spectacle as the final native GUI
destination.

Primary native target:

1. User chooses `Scrolling Capture` from Spectacle's capture UI, desktop action,
   or dedicated shortcut.
2. Spectacle shows its normal selection overlay.
3. User selects a scrollable region or window.
4. A compact scrolling toolbar appears.
5. User chooses automatic direction if available, or manual mode.
6. The toolbar shows frame count, progress, confidence, Done, and Cancel.
7. Toolbelt/Spectacle stitches frames.
8. Result opens in Spectacle's editor.

External Toolbelt bridge until native Spectacle support exists:

1. User launches `Spectacle Toolbelt Scrolling Capture`.
2. Toolbelt asks for scrolling mode:
   - Auto vertical
   - Auto horizontal
   - Auto bidirectional
   - Manual/panoramic
3. Toolbelt uses Spectacle-compatible capture paths to collect frames.
4. Toolbelt uses the stitch engine to produce the result.
5. Toolbelt opens the result in Spectacle's editor.

## Scrolling Toolbar UX

The scrolling capture toolbar must be compact and visible but excluded from the
final output where technically possible.

Required controls:

- direction selector: vertical, horizontal, bidirectional
- mode selector: automatic, manual
- Capture Frame, visible in manual mode
- Done
- Cancel
- frame count
- live status indicator
- optional warning details

Status colors:

- green: complete, all joins above confidence threshold
- yellow: partial, output exists but one or more joins used best-effort matching
- red: failed, no usable stitched output

## Data Flow

### Full-Page Web Capture

```text
shortcut
  -> active browser/tab resolver
  -> URL fallback prompt when active-tab resolution fails
  -> browser full-page capture backend
  -> output writer
  -> clipboard copy
  -> notification / editor handoff
```

### Scrolling Capture

```text
explicit scrolling capture entrypoint
  -> region/window selection
  -> capture session
  -> scroll controller or manual frame trigger
  -> frame store
  -> stitch engine
  -> result classifier
  -> Spectacle editor handoff
```

## Component Boundaries

### Capture Mode Router

Purpose:

- keep normal capture, full-page web capture, and scrolling capture separate
- prevent shortcut or launcher drift
- make doctor output explain what owns each capture path

Public contract:

- `normal`: Spectacle-owned, no Toolbelt handling
- `web-fullpage`: active-tab first, URL prompt fallback
- `scrolling`: explicit scrolling workflow only

### Active Browser Resolver

Purpose:

- identify the current browser window and tab URL when possible
- avoid prompting when the URL can be discovered safely

Initial implementation options:

- query Chrome/Chromium remote debugging when available
- inspect KDE/xdotool-style active window metadata on X11
- keep a browser extension/native messaging bridge boundary in the resolver so
  browser-owned active-tab handoff can be added without redesigning the capture
  contract

Wayland constraint:

- global window inspection may be limited; fallback to URL prompt is mandatory.

### Browser Full-Page Backend

Purpose:

- load or connect to a browser page and capture full-page PNG output
- support the existing `Ctrl+Alt+W` workflow

Initial backend:

- Chromium/Chrome automation through an existing local script or Playwright-like
  browser automation, wrapped behind a stable Toolbelt command.

Safety:

- URL must be `http`, `https`, or explicitly allowed `file`.
- No remote upload.
- No telemetry.
- Output path must not overwrite existing files unless explicitly forced.

### Scrolling Session Controller

Purpose:

- own frame ordering, max frames, max output dimensions, cancellation, and state
- separate automatic scroll from manual capture

Session states:

- ready to select
- selected
- capturing frame
- waiting for scroll
- automatic scrolling
- processing
- complete
- partial
- failed
- cancelled

### Stitch Engine

Purpose:

- combine ordered frames into one image
- classify result quality
- emit diagnostics without requiring private screenshot upload

Required behavior:

- exact row-match fast path
- tolerant pixel-difference matching
- fixed header/footer mitigation
- vertical and horizontal stitching
- max frame, input pixel, and output pixel caps
- no overwrite without explicit force
- debug JSON with confidence and join metadata

## Error Handling

### Normal Capture Errors

Handled by Spectacle.

Toolbelt should not add failure paths to normal screenshots.

### Full-Page Web Capture Errors

Required messages:

- active tab unavailable: prompt for URL
- browser backend unavailable: explain missing dependency
- page capture failed: keep error concise and include URL host only, not full
  sensitive URLs by default
- output already exists: refuse unless force is used
- clipboard unavailable: save succeeds and notification says clipboard copy was
  skipped

### Scrolling Capture Errors

Required messages:

- automatic scrolling unavailable: offer manual mode
- no movement detected: stop and offer partial result if frames exist
- overlap confidence low: mark yellow partial and open output if usable
- first join failed: mark red failure and keep diagnostics
- dynamic/animated content detected: suggest tighter region or manual mode
- Wayland input restriction: explain why automatic scroll is unavailable

## Testing Strategy

### Unit Tests

- capture mode router maps shortcuts to the correct owner
- active-tab resolver falls back to URL prompt when unsupported
- output writer refuses overwrite without force
- stitch engine handles exact overlap, partial joins, first-join failure, fixed
  headers, max frame caps, and max pixel caps

### Integration Tests

- `Ctrl+Alt+W` command captures a supplied test URL into a PNG
- URL prompt fallback captures the same test URL
- service menu stitch opens result in Spectacle editor when available
- doctor reports capture ownership and missing dependencies clearly

### Manual KDE Tests

- Print and Spectacle's normal shortcuts still behave as normal screenshots
- `Ctrl+Alt+W` captures active browser tab without prompting
- URL prompt appears when no browser tab can be resolved
- scrolling capture manual mode supports Done and Cancel
- automatic scrolling stops at page/document end
- partial output is yellow and opens in Spectacle editor
- failed output is red and preserves diagnostics

## Acceptance Criteria

The milestone is complete only when:

- Normal Spectacle screenshots are unchanged.
- Full-page web capture is reachable through `Ctrl+Alt+W`.
- `Ctrl+Alt+W` uses the active browser tab by default.
- URL prompt is fallback, not the primary path.
- Scrolling capture is explicit and never triggered by normal capture.
- Manual scrolling capture has Done and Cancel.
- Automatic scrolling capture has vertical and horizontal direction handling
  where platform support exists.
- Results open in Spectacle's editor.
- Success, partial, and failure states are visually and textually clear.
- Doctor can explain capture ownership and platform blockers.
- README no longer implies that service-menu stitching is the primary UX.

## Implementation Sequencing

1. **Capture Ownership Cleanup**
   - audit current local shortcuts
   - document which shortcuts belong to Spectacle, Toolbelt full-page capture,
     and Toolbelt scrolling capture
   - ensure normal capture is not forced through scrolling code

2. **Full-Page Web Capture**
   - create a stable Toolbelt command for full-page web capture
   - default to active tab
   - keep URL prompt fallback
   - wire `Ctrl+Alt+W` to the Toolbelt command

3. **Scrolling Capture Prototype**
   - create explicit scrolling capture launcher/shortcut
   - provide manual mode with frame count, Done, Cancel
   - integrate stitch result states

4. **Automatic Scrolling**
   - add automatic scroll controller where session support allows it
   - fall back to manual mode with clear messaging

5. **Spectacle Native Proposal**
   - convert the proven UX into an upstream Spectacle proposal/MR plan
   - keep Toolbelt as harness until upstream support exists

## Sources

- Snagit scrolling capture tutorial:
  `https://www.techsmith.com/learn/tutorials/snagit/scrolling-capture/`
- ShareX scrolling screenshot documentation:
  `https://getsharex.com/docs/scrolling-screenshot`
- Wondershare DemoCreator Snagit scrolling capture overview:
  `https://democreator.wondershare.com/screen-recorder/snagit-scrolling-capture.html`
- ShareX repository:
  `https://github.com/ShareX/ShareX`
