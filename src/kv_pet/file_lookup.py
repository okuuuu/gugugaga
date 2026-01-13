"""Folder scanning and part-number-to-path matching logic."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union


@dataclass
class MatchResult:
    """Result of matching a part number to files."""

    pdf_files: List[Path] = field(default_factory=list)
    model_files: List[Path] = field(default_factory=list)
    no_pdf_required: bool = False
    status: str = ""


def normalize_for_match(text: str) -> str:
    """Normalize text for matching: lowercase, remove spaces/dashes/underscores."""
    return re.sub(r"[\s\-_]", "", text.lower())


def scan_folder(folder_path: Union[str, Path], recursive: bool = True) -> List[Path]:
    """
    Scan a folder and return all file paths.

    Args:
        folder_path: The folder to scan.
        recursive: If True, scan subdirectories as well.

    Returns:
        List of Path objects for all files found.
    """
    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"Folder not found: {folder}")
    if not folder.is_dir():
        raise NotADirectoryError(f"Not a directory: {folder}")

    if recursive:
        return [p for p in folder.rglob("*") if p.is_file()]
    else:
        return [p for p in folder.iterdir() if p.is_file()]


def extract_revision_number(filename: str) -> Optional[int]:
    """
    Extract revision number from filename.

    Looks for patterns like _rev1, _rev2, _r1, _r2, etc.
    Returns None if no revision found.
    """
    # Match _rev followed by digits, or _r followed by digits
    match = re.search(r"_r(?:ev)?(\d+)", filename.lower())
    if match:
        return int(match.group(1))
    return None


def get_base_name_without_revision(filename: str) -> str:
    """Remove revision suffix from filename for grouping."""
    # Remove _rev# or _r# patterns
    return re.sub(r"_r(?:ev)?\d+", "", filename.lower())


def collapse_to_latest_revision(files: List[Path]) -> List[Path]:
    """
    Given a list of files, collapse those with revision suffixes to only the latest.

    Files without revision numbers are kept as-is.
    """
    if not files:
        return []

    # Group files by base name (without revision)
    groups: Dict[str, List[tuple]] = {}  # base_name -> [(rev_num, path), ...]

    for file_path in files:
        stem = file_path.stem
        base = get_base_name_without_revision(stem)
        rev = extract_revision_number(stem)

        if base not in groups:
            groups[base] = []
        groups[base].append((rev, file_path))

    # For each group, keep only the highest revision (or all if no revisions)
    result = []
    for base, items in groups.items():
        # Separate items with and without revision numbers
        with_rev = [(r, p) for r, p in items if r is not None]
        without_rev = [p for r, p in items if r is None]

        if with_rev:
            # Keep only the highest revision
            with_rev.sort(key=lambda x: x[0], reverse=True)
            result.append(with_rev[0][1])
        else:
            # No revisions, keep all
            result.extend(without_rev)

    return result


def find_matching_files(
    part_number: str,
    files: List[Path],
    match_mode: str = "contains",
    file_extensions: Optional[List[str]] = None,
) -> List[Path]:
    """
    Find files that match a part number.

    Args:
        part_number: The part number to search for.
        files: List of file paths to search.
        match_mode: How to match - "exact" (filename equals part number),
                   "contains" (filename contains part number),
                   "startswith" (filename starts with part number).
        file_extensions: If provided, only match files with these extensions.

    Returns:
        List of matching file paths.
    """
    # Remove trailing * for matching purposes
    clean_pn = part_number.rstrip("*").strip()
    normalized_pn = normalize_for_match(clean_pn)
    matches = []

    for file_path in files:
        # Filter by extension if specified
        if file_extensions:
            if file_path.suffix.lower() not in [e.lower() for e in file_extensions]:
                continue

        # Match against the stem (filename without extension)
        normalized_stem = normalize_for_match(file_path.stem)

        if match_mode == "exact":
            if normalized_stem == normalized_pn:
                matches.append(file_path)
        elif match_mode == "startswith":
            if normalized_stem.startswith(normalized_pn):
                matches.append(file_path)
        else:  # contains
            if normalized_pn in normalized_stem:
                matches.append(file_path)

    return matches


def lookup_part_number(
    part_number: str,
    files: List[Path],
    match_mode: str = "contains",
) -> MatchResult:
    """
    Look up a single part number and return structured match result.

    Args:
        part_number: The part number to search for.
        files: List of all files to search.
        match_mode: How to match filenames to part numbers.

    Returns:
        MatchResult with PDFs, models, and status.
    """
    result = MatchResult()

    # Check if part number ends with * (no PDF required)
    if part_number.rstrip().endswith("*"):
        result.no_pdf_required = True
        result.status = "No PDF required"
        # Still look for model files
        model_matches = find_matching_files(
            part_number, files, match_mode, file_extensions=[".ipt", ".iam"]
        )
        result.model_files = model_matches
        return result

    # Find PDF matches
    pdf_matches = find_matching_files(
        part_number, files, match_mode, file_extensions=[".pdf"]
    )
    # Collapse to latest revision
    result.pdf_files = collapse_to_latest_revision(pdf_matches)

    # Find model files (.ipt, .iam)
    model_matches = find_matching_files(
        part_number, files, match_mode, file_extensions=[".ipt", ".iam"]
    )
    result.model_files = model_matches

    # Set status
    if result.pdf_files:
        result.status = f"{len(result.pdf_files)} PDF(s)"
    else:
        result.status = "No PDF match"

    return result


def lookup_part_numbers(
    part_numbers: List[str],
    folder_path: Union[str, Path],
    recursive: bool = True,
    match_mode: str = "contains",
) -> Dict[str, MatchResult]:
    """
    Look up part numbers in a folder and return matching file paths.

    Args:
        part_numbers: List of part numbers to search for.
        folder_path: The folder to search in.
        recursive: If True, search subdirectories.
        match_mode: How to match filenames to part numbers.

    Returns:
        Dict mapping each part number to a MatchResult.
    """
    files = scan_folder(folder_path, recursive)
    results = {}

    for pn in part_numbers:
        results[pn] = lookup_part_number(pn, files, match_mode)

    return results


# Legacy function for backwards compatibility
def lookup_part_numbers_legacy(
    part_numbers: List[str],
    folder_path: Union[str, Path],
    recursive: bool = True,
    match_mode: str = "contains",
) -> Dict[str, List[Path]]:
    """
    Legacy lookup function returning simple path lists.

    Kept for backwards compatibility with existing code.
    """
    files = scan_folder(folder_path, recursive)
    results = {}

    for pn in part_numbers:
        matches = find_matching_files(pn, files, match_mode)
        results[pn] = matches

    return results
