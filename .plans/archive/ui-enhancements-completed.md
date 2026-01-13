# Plan: Part number match enhancements & UI actions

## Context
- No git remote is configured, so fetching `master` is not possible in this repo state.
- The UI is a Tkinter app with a drag-and-drop PDF selection label and a Treeview for results.
- Matching logic currently returns any file types and does not handle revision selection or special part-number suffixes.
- The requested updates add click behaviors (drop-zone browse, print buttons, model links) and stricter matching rules.

## Files to Create/Modify
- `src/kv_pet/app.py` — update UI behavior (clickable drop zone, model column, print actions, Treeview interactions).
- `src/kv_pet/file_lookup.py` — refine matching logic for PDF-only results, revision handling, and part-number suffix rules.
- `src/kv_pet/pdf_extract.py` — adjust if needed to preserve/flag part number suffixes such as `*`.

## Implementation Steps
1. [x] Review current extraction and matching data flow to confirm where part numbers and matches are assembled for display.
2. [x] Update matching logic to:
   - filter matches to `.pdf` by default,
   - collapse `_rev` files to the latest numeric revision when multiple exist,
   - mark part numbers ending in `*` as "no PDF required" in the matching output.
3. [x] Extend UI columns to add a rightmost "Model" column and render a clickable square indicator for `.ipt`/`.iam` matches.
4. [x] Make the drag-and-drop label clickable to open the PDF browse dialog (regardless of DnD availability).
5. [x] Add a "Print" action adjacent to each matched PDF (e.g., in the matching files column text or via a dedicated action column) and wire it to system print for PDFs.
6. [x] Ensure Treeview click handlers distinguish between open-file, print, and model-link actions without breaking double-click open.
✅ Verify by running: python -m pytest

## Technical Constraints
- Avoid adding new UI dependencies; use Tkinter only.
- Keep PDF matching case-insensitive and consistent with existing normalization.
- Preserve existing drag-and-drop behavior when tkinterdnd2 is available.

## Dependencies
- No new dependencies.

## Notes / Edge Cases
- If no prior plan existed, the archive entry is empty; document this in commit history as needed.
- Handle `_rev` matching when filenames include additional suffixes beyond the revision number.
- If a part number ends with `*`, do not require a PDF and display a clear message instead of a file list.
- When both `.ipt` and `.iam` exist, decide whether to show one or multiple model indicators.

## Claude Code Handoff
- Save this plan to `.plans/current.md`.
- Claude Code command: `claude "Read .plans/current.md and implement the plan step by step"`
- While implementing:
  1. Read the full plan first
  2. Execute steps in order
  3. Check off completed items
  4. Record deviations/blockers directly in the plan file
