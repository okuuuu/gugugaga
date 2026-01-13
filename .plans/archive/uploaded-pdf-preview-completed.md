# Plan: Adjustable PDF Preview & Print for Uploaded PDFs

## Context
- No git remote is configured in this repo, so fetching `master` is not possible before planning updates.
- The current Tkinter UI lets users add PDF files but provides no preview or print actions for the uploaded PDFs themselves.
- The results tree already supports opening and printing matched PDFs via row interactions, which can be reused for uploaded files.
- The request is to add a resizable preview for the uploaded PDF and expose both preview and print actions for that PDF.

## Files to Create/Modify
- `src/kv_pet/app.py` — add uploaded-PDF selection, preview panel, size control, and print/preview actions.
- `pyproject.toml` — add `pillow` if needed for rendering PDF pages to images in Tkinter.

## Implementation Steps
1. [x] Review the current PDF selection UI and decide where to add controls for preview/print of uploaded PDFs (e.g., listbox + action buttons + preview panel).
2. [x] Add UI state to track the currently selected uploaded PDF and the requested preview size (slider or input), with sensible defaults.
3. [x] Implement preview rendering for the selected uploaded PDF's first page, resizing according to the chosen preview size, and display it in a dedicated panel.
4. [x] Add "Preview" and "Print" actions tied to the selected uploaded PDF, reusing existing open/print helpers where possible.
5. [x] Ensure preview updates are non-blocking and cached per PDF/size to keep the UI responsive.
6. [x] Handle empty selection, missing files, or render failures gracefully (clear preview, show status text).
✅ Verify by running: python -m pytest (39 tests passed)

## Technical Constraints
- Keep the UI in Tkinter without introducing new UI frameworks.
- Avoid blocking the main thread during PDF rendering; use caching or background work.
- Preview size controls must be bounded to prevent excessive memory usage.

## Dependencies
- Add `pillow` if required for PDF-to-image rendering and Tkinter image display.

## Notes / Edge Cases
- Multiple uploaded PDFs should be selectable, with preview/print actions scoped to the current selection.
- Some PDFs may fail to render; the UI should surface an error state without crashing.
- Preview size changes should immediately refresh the displayed preview.

## Implementation Notes
- Replaced the simple label counter with a Listbox showing all uploaded PDF filenames
- Added Preview, Print, and Open buttons that enable/disable based on selection
- Added a Scale widget (150-400px) for adjustable preview size with live updates
- Preview source indicator shows "Source:" for uploaded PDFs and "Match:" for result hover
- Reused existing `_print_pdf()` and `os.startfile()` for print/open actions
- LRU cache handles preview caching; size changes trigger immediate re-render
- Graceful error handling clears preview and shows error in status bar

## Claude Code Handoff
- Save this plan to `.plans/current.md`.
- Claude Code command: `claude "Read .plans/current.md and implement the plan step by step"`
- While implementing:
  1. Read the full plan first
  2. Execute steps in order
  3. Check off completed items
  4. Record deviations/blockers directly in the plan file