# Scrolling Capture UX Flow

Date: 2026-04-24

The mature scrolling capture UX belongs inside Spectacle. Toolbelt provides the
algorithm harness and KDE-standard fallback surfaces until that upstream path
exists.

## Native Manual Flow

1. User starts Spectacle scrolling capture from the capture mode list, desktop action, or global shortcut.
2. Spectacle shows its normal region/window selection overlay.
3. User selects the scrollable area.
4. A compact scrolling capture toolbar appears with:
   - Capture Frame
   - Done
   - Cancel
   - frame count
   - confidence/warning state
5. User scrolls or pans one direction at a time.
6. Spectacle captures frames and shows progress.
7. User clicks Done.
8. Spectacle stitches the frames.
9. On success or partial success, Spectacle opens the result in its existing editor.
10. User annotates, extracts text, scans QR, copies, saves, or shares through Spectacle.

## Native Automatic Flow

1. User starts Spectacle scrolling capture.
2. User selects or hovers a scrollable window/region.
3. If automatic scrolling is supported, Spectacle shows direction affordances:
   - vertical
   - horizontal
   - bidirectional when supported
4. User chooses a direction.
5. Spectacle scrolls, captures, and stitches with progress.
6. Spectacle opens the finished or partial result in the editor.

## Required States

- Ready to select
- Capturing frame
- Waiting for manual scroll
- Automatic scrolling
- Processing/stitching
- Complete
- Partial output available
- Failed with no usable output
- Cancelled

## Error And Partial States

Partial output is acceptable only when clearly labeled. The user should know:

- which join failed or fell below confidence
- whether a usable image was created
- where debug diagnostics were written
- whether the failure was caused by capture limits, scroll behavior, dynamic content, or platform restrictions

## Fallback Toolbelt Flow

Until Spectacle has native UI, Toolbelt now:

1. exposes `Spectacle Toolbelt Scrolling Capture` in the KDE launcher and as a
   user-local Spectacle launcher app action
2. asks for manual, automatic vertical, or automatic horizontal mode
3. asks the user to drag the scrolling viewport once using global desktop
   coordinates, including windows that span monitors when the capture backend
   can represent the selected rectangle
4. captures each frame from that same rectangle while the user scrolls
5. shows Capture Next, Done, Cancel, and frame count between frames
6. writes a debug JSON sidecar
7. opens the result in Spectacle via `spectacle --edit-existing`
8. exposes Dolphin/KIO service menus for existing images

The fallback flow is useful and visible, but the final product UX still belongs
inside Spectacle's own capture overlay.
