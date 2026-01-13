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
<<<<<<< HEAD:.plans/archive/table-columns-preview-completed.md
1. [x] Inspect current PDF table parsing to determine where TITLE/DESCRIPTION/MASS/Qty can be extracted from the same table row as part numbers.
2. [x] Update extraction output structures to return a richer row model (part number + title/description/mass/qty) while preserving existing behavior for PDFs that only include part numbers.
3. [x] Thread the new row model through lookup/matching so results map the extra fields per part number.
4. [x] Update the Treeview to include separate columns for TITLE, DESCRIPTION, MASS, and Qty and populate them per row.
5. [x] Add a hover handler on Treeview rows that, when a PDF exists, renders a preview image and shows it in a top-right overlay/widget; hide/clear on hover exit or row change.
6. [x] Ensure preview rendering is performant (cache per-PDF image, limit to first page) and degrades gracefully when PDFs are missing or preview generation fails.
=======
1. [ ] Review the current PDF selection UI and decide where to add controls for preview/print of uploaded PDFs (e.g., listbox + action buttons + preview panel).
2. [ ] Add UI state to track the currently selected uploaded PDF and the requested preview size (slider or input), with sensible defaults.
3. [ ] Implement preview rendering for the selected uploaded PDF’s first page, resizing according to the chosen preview size, and display it in a dedicated panel.
4. [ ] Add “Preview” and “Print” actions tied to the selected uploaded PDF, reusing existing open/print helpers where possible.
5. [ ] Ensure preview updates are non-blocking and cached per PDF/size to keep the UI responsive.
6. [ ] Handle empty selection, missing files, or render failures gracefully (clear preview, show status text).
>>>>>>> 65f9bf81adb756080b196d7cba3baaaaf3f7b194:.plans/current.md
✅ Verify by running: python -m pytest

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

## Claude Code Handoff
- Save this plan to `.plans/current.md`.
- Claude Code command: `claude "Read .plans/current.md and implement the plan step by step"`
- While implementing:
  1. Read the full plan first
  2. Execute steps in order
  3. Check off completed items
  4. Record deviations/blockers directly in the plan file
