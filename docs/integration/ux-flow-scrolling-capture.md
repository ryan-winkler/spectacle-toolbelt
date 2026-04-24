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

Until Spectacle has native UI, Toolbelt should:

1. stitch pre-captured frames
2. write a debug JSON sidecar when requested
3. open the result in Spectacle via `spectacle --edit-existing`
4. expose Dolphin/KIO service menus for existing images

The fallback flow is useful, but it is not the final product UX.
