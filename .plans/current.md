# Plan: PDF Part Number Extractor with File Path Lookup

## Context
- No git remote is configured, so `git fetch` cannot be run for `master`.
- Build an app that accepts a PDF drawing via drag-and-drop or folder selection.
- The PDF contains a bottom-right table with a `PART NUMBER` column to extract.
- Extracted part numbers must be returned to the user with a link/path to matching files in the selected folder.
- Repository is a fresh Python project with no existing app structure.

## Files to Create/Modify
- `pyproject.toml` — define project metadata and Python dependencies for the app.
- `src/kv_pet/__init__.py` — package initializer.
- `src/kv_pet/app.py` — application entry point (web server or desktop UI wiring).
- `src/kv_pet/pdf_extract.py` — PDF table parsing and `PART NUMBER` extraction logic.
- `src/kv_pet/file_lookup.py` — folder scanning and part-number-to-path matching logic.
- `src/kv_pet/ui/` — front-end assets/templates for drag-and-drop and folder selection UI.
- `README.md` — usage instructions and setup notes.

## Implementation Steps
1. [ ] Establish the app approach (web UI vs. desktop UI) and align folder-selection + drag-and-drop behavior to that UI choice.
2. [ ] Add project scaffolding and dependency declarations required for PDF table extraction.
3. [ ] Implement PDF parsing to locate the bottom-right table and extract `PART NUMBER` values reliably.
4. [ ] Implement folder scanning and file-path resolution for each extracted part number (exact/normalized match rules defined).
5. [ ] Build the UI to accept drag-and-drop or folder selection, run the extraction, and render results with file paths.
6. [ ] Add basic validation, error handling, and user feedback for missing tables, empty columns, or no matching files.
7. [ ] Document setup, usage, and limitations in `README.md`.
✅ Verify by running: python -m pytest

## Technical Constraints
- Keep parsing deterministic and avoid heavy system dependencies unless required.
- Handle PDFs that contain multiple tables and ensure `PART NUMBER` is picked from the correct table.
- Support both drag-and-drop input and folder browsing within the chosen UI framework.

## Dependencies
- Add `pdfplumber` (or equivalent) to extract tables from PDFs.
- Add a lightweight web or UI framework if required by the chosen interface.

## Notes / Edge Cases
- `PART NUMBER` column header casing or spacing may vary.
- Multiple PDFs may be dropped; ensure batch processing does not block the UI.
- File matching may require normalization (case-insensitive, strip spaces/dashes).

## Claude Code Handoff
- Save this plan to `.plans/current.md`.
- Claude Code command: `claude "Read .plans/current.md and implement the plan step by step"`
- While implementing:
  1. Read the full plan first
  2. Execute steps in order
  3. Check off completed items
  4. Record deviations/blockers directly in the plan file
