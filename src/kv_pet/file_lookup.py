"""Folder scanning and part-number-to-path matching logic."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Union


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


def find_matching_files(
    part_number: str,
    files: List[Path],
    match_mode: str = "contains",
) -> List[Path]:
    """
    Find files that match a part number.

    Args:
        part_number: The part number to search for.
        files: List of file paths to search.
        match_mode: How to match - "exact" (filename equals part number),
                   "contains" (filename contains part number),
                   "startswith" (filename starts with part number).

    Returns:
        List of matching file paths.
    """
    normalized_pn = normalize_for_match(part_number)
    matches = []

    for file_path in files:
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


def lookup_part_numbers(
    part_numbers: List[str],
    folder_path: Union[str, Path],
    recursive: bool = True,
    match_mode: str = "contains",
) -> Dict[str, List[Path]]:
    """
    Look up part numbers in a folder and return matching file paths.

    Args:
        part_numbers: List of part numbers to search for.
        folder_path: The folder to search in.
        recursive: If True, search subdirectories.
        match_mode: How to match filenames to part numbers.

    Returns:
        Dict mapping each part number to a list of matching file paths.
    """
    files = scan_folder(folder_path, recursive)
    results = {}

    for pn in part_numbers:
        matches = find_matching_files(pn, files, match_mode)
        results[pn] = matches

    return results
