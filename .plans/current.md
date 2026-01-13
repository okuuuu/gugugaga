# Plan: PDF Preview Resizing & Desktop Distribution

## Context
- No git remote is configured, so fetching `master` is not possible in this workspace.
- The current UI includes a preview size slider independent of the preview pane width.
- The request is to remove the slider and scale the preview based on the resizable pane border.
- The PDF preview should never overflow the application window.
- The app should be distributable as a desktop executable that opens via double-click for sharing.

## Files to Create/Modify
- `src/kv_pet/app.py` — remove preview size slider, tie preview scaling to pane width/height, and ensure previews fit within the window.
- `README.md` — document packaging steps for producing a double-clickable desktop executable.
- `pyproject.toml` — add optional packaging dependency metadata (if needed for the chosen build tool).

## Implementation Steps
1. [ ] Remove the preview size slider UI/state and introduce a single sizing pathway driven by the preview pane dimensions (track pane size via `<Configure>` events or PanedWindow sash updates).
2. [ ] Compute preview image size from the preview frame’s available width/height (respecting padding) and update the cache key/thumbnail sizing to prevent overflow in the pane.
3. [ ] Refresh previews when the pane is resized, throttling updates if necessary to avoid excessive rendering.
4. [ ] Add documentation for building a desktop executable (e.g., PyInstaller) and clarify how users can double-click the packaged app.
✅ Verify by running: python -m kv_pet.app

## Technical Constraints
- Keep UI responsive while resizing; avoid blocking the main thread during preview refresh.
- Maintain aspect ratio of PDF previews while fitting within the pane bounds.
- Do not add try/catch blocks around imports.

## Dependencies
- PyInstaller (optional, for building a double-clickable desktop executable).

## Notes / Edge Cases
- If Pillow/pdfplumber is unavailable, ensure preview messaging still renders correctly.
- Handle very small pane sizes gracefully (avoid zero/negative dimensions).
- Confirm that resizing the sash triggers a preview update without flicker.

## Claude Code Handoff
- Save this plan to `.plans/current.md`.
- Claude Code command: `claude "Read .plans/current.md and implement the plan step by step"`
- While implementing:
  1. Read the full plan first
  2. Execute steps in order
  3. Check off completed items
  4. Record deviations/blockers directly in the plan file
