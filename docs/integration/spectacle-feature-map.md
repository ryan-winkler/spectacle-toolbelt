# Spectacle Feature Map

Date: 2026-04-24

Spectacle Toolbelt must compose with Spectacle before adding new behavior. This
map keeps feature ownership explicit.

| Area | Spectacle-Owned Capability | Toolbelt Responsibility | Upstream Target |
| --- | --- | --- | --- |
| Capture | Full desktop, current monitor, active window, selected/window under cursor, rectangular region | Invoke and document safe capture paths where useful | Add scrolling capture as a native capture mode/action |
| Recording | Region, screen, window recording | No duplicate recording feature | None for scrolling screenshot milestone |
| CLI | `--background`, `--region`, `--output`, `--copy-image`, `--copy-path`, `--delay`, `--onclick`, `--edit-existing` | Wrap editor handoff and fallback workflows | Keep native CLI in Spectacle if scrolling capture lands upstream |
| D-Bus | Screenshot and recording methods | Use for diagnostics/research where stable | Add scrolling capture D-Bus method only if KDE accepts it |
| Desktop actions | Capture/record/open actions in Spectacle desktop file | Install Toolbelt-owned service menus only until native actions are useful | Add native scrolling action to Spectacle desktop file |
| Shortcuts | KGlobalAccel actions aligned with Spectacle desktop actions | Document bridge shortcut recipes | Register native scrolling shortcut action in Spectacle |
| Annotation | Crop, select, freehand, highlighter, line, arrow, rectangle, ellipse, pixelate, blur, text, number stamp | Open generated images in Spectacle editor | Reuse existing editor for scrolling capture output |
| OCR | Extract Text action | Do not duplicate native OCR UI; future batch sidecars must be explicit | Reuse OCR action after editor handoff |
| QR | QR scanning in export flow | Do not duplicate native QR flow by default | Reuse existing export flow |
| Redaction | Blur and pixelate tools | Add policy/automation only where it does not duplicate manual editor tools | Upstream only if a native smart-redaction UX is accepted |
| Documentation | Visual annotations in editor | Markdown export, asset naming, sidecar metadata, guide sequencing | Native hooks only if Spectacle accepts documentation workflow integration |
| Scrolling capture | Not currently native | Algorithm harness, diagnostics, fallback service menus | Native GUI capture mode/action |

## Rule

If Spectacle already owns the user interaction, Toolbelt should call, document,
or hand off to Spectacle instead of rebuilding that interaction.
