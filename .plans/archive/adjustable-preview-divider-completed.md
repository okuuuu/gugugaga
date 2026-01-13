# Plan: Adjustable Preview Divider Expansion

## Context
- Git remote is not configured; fetch of master could not be attempted.
- Previous .plans/current.md was missing; archived an empty placeholder per instructions.
- Request: increase preview size by adjusting borders/divider between windows.
- Need to identify where split panes or resizable borders are implemented in the UI.
- Update layout logic so resizing divider expands the preview area appropriately.

## Files to Create/Modify
- `src/` relevant UI layout files — locate split-pane/border resizing logic for preview area.
- `tests/` (if applicable) — update or add coverage for resize behavior.

## Implementation Steps
1. [x] Locate UI components that render the preview and the resizable divider between windows.
2. [x] Identify current sizing constraints for preview pane and divider behavior.
3. [x] Adjust divider logic and/or CSS so the preview can be increased via border/drag resizing.
4. [x] Update any state management tied to pane sizes to persist or clamp values appropriately.
5. [x] Add or update tests/documentation notes for the resizing behavior (if tests exist).
✅ Verify by running: python -m pytest (39 tests passed)

## Technical Constraints
- Do not add try/catch blocks around imports.
- Follow existing UI layout patterns and sizing conventions.
- Keep divider interaction accessible and consistent with current UX.

## Dependencies
- No new dependencies

## Notes / Edge Cases
- Ensure minimum/maximum widths prevent the preview from collapsing or exceeding container bounds.
- Verify behavior across responsive breakpoints if the layout changes with screen size.
- Confirm drag handles remain usable after sizing changes.

## Implementation Notes
- Replaced pack-based left/right layout with `ttk.PanedWindow(orient=tk.HORIZONTAL)`
- Left pane (controls/results) has `weight=1` for expansion, preview pane has `weight=0`
- PanedWindow provides a draggable sash between panes automatically
- Removed fixed width/height constraints from preview panel
- Added `_schedule_initial_sash_position()` to set initial preview width after window realized
- Increased size slider range from 150-400px to 150-600px for larger previews
- Preview panel resizes when dragging the sash; image size still controlled by slider

## Claude Code Handoff
- Save this plan to `.plans/current.md`.
- Claude Code command: `claude "Read .plans/current.md and implement the plan step by step"`
- While implementing:
  1. Read the full plan first
  2. Execute steps in order
  3. Check off completed items
  4. Record deviations/blockers directly in the plan file
