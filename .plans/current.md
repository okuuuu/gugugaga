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
1. [ ] Locate UI components that render the preview and the resizable divider between windows.
2. [ ] Identify current sizing constraints for preview pane and divider behavior.
3. [ ] Adjust divider logic and/or CSS so the preview can be increased via border/drag resizing.
4. [ ] Update any state management tied to pane sizes to persist or clamp values appropriately.
5. [ ] Add or update tests/documentation notes for the resizing behavior (if tests exist).
✅ Verify by running: <command(s)>

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

## Claude Code Handoff
- Save this plan to `.plans/current.md`.
- Claude Code command: `claude "Read .plans/current.md and implement the plan step by step"`
- While implementing:
  1. Read the full plan first
  2. Execute steps in order
  3. Check off completed items
  4. Record deviations/blockers directly in the plan file
