# Plan: Table Columns and PDF Hover Preview

## Context
- No git remote is configured, so fetching `master` is not possible in this repo state.
- The UI is a Tkinter desktop app with a results Treeview listing extracted part numbers.
- The request is to split out distinct columns for TITLE, DESCRIPTION, MASS, and Qty.
- When a row has an associated PDF, hovering that row should show a PDF preview near the top-right of the UI.
- PDF parsing currently focuses on part numbers; additional table fields are not extracted today.

## Files to Create/Modify
- `src/kv_pet/pdf_extract.py` — extend table extraction to capture TITLE, DESCRIPTION, MASS, Qty alongside part numbers.
- `src/kv_pet/file_lookup.py` — adjust data structures to carry the additional fields through lookup results.
- `src/kv_pet/app.py` — update Treeview columns, row hover handling, and PDF preview widget.
- `pyproject.toml` — add any required dependency for rendering PDF previews (e.g., Pillow), if needed.

## Implementation Steps
1. [ ] Inspect current PDF table parsing to determine where TITLE/DESCRIPTION/MASS/Qty can be extracted from the same table row as part numbers.
2. [ ] Update extraction output structures to return a richer row model (part number + title/description/mass/qty) while preserving existing behavior for PDFs that only include part numbers.
3. [ ] Thread the new row model through lookup/matching so results map the extra fields per part number.
4. [ ] Update the Treeview to include separate columns for TITLE, DESCRIPTION, MASS, and Qty and populate them per row.
5. [ ] Add a hover handler on Treeview rows that, when a PDF exists, renders a preview image and shows it in a top-right overlay/widget; hide/clear on hover exit or row change.
6. [ ] Ensure preview rendering is performant (cache per-PDF image, limit to first page) and degrades gracefully when PDFs are missing or preview generation fails.
✅ Verify by running: python -m pytest

## Technical Constraints
- Keep the UI in Tkinter; avoid introducing new UI frameworks.
- Preview should not block the UI thread; use caching or background rendering if needed.
- Maintain compatibility with PDF files lacking the extra columns by leaving those fields blank.

## Dependencies
- Add `pillow` if required for PDF-to-image rendering via pdfplumber.

## Notes / Edge Cases
- Some PDFs may not include TITLE/DESCRIPTION/MASS/Qty columns or may use alternate headers; handle missing fields gracefully.
- Hover preview should not obscure critical controls; place it in a predictable top-right container.
- Large PDFs may be slow to render; consider downscaling or thumbnailing.

## Claude Code Handoff
- Save this plan to `.plans/current.md`.
- Claude Code command: `claude "Read .plans/current.md and implement the plan step by step"`
- While implementing:
  1. Read the full plan first
  2. Execute steps in order
  3. Check off completed items
  4. Record deviations/blockers directly in the plan file
