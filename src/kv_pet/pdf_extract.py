"""PDF table parsing and PART NUMBER extraction logic."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pdfplumber


def normalize_header(text: Optional[str]) -> str:
    """Normalize header text for comparison (lowercase, strip spaces/special chars)."""
    if text is None:
        return ""
    return "".join(text.lower().split()).replace("-", "").replace("_", "")


def find_part_number_column(headers: List[Optional[str]]) -> Optional[int]:
    """Find the index of the PART NUMBER column in a table header row."""
    target = "partnumber"
    for i, header in enumerate(headers):
        if normalize_header(header) == target:
            return i
    return None


def find_header_row(table: List[List[Optional[str]]]) -> Tuple[Optional[int], Optional[int]]:
    """
    Find the header row containing PART NUMBER column.

    Returns (header_row_index, part_number_column_index) or (None, None) if not found.
    """
    for row_idx, row in enumerate(table):
        col_idx = find_part_number_column(row)
        if col_idx is not None:
            return row_idx, col_idx
    return None, None


def extract_part_numbers_from_table(table: List[List[Optional[str]]]) -> List[str]:
    """
    Extract part numbers from a table that has a PART NUMBER column.

    Handles engineering drawings where header may be at the bottom of the parts list.
    """
    if not table or len(table) < 2:
        return []

    header_row_idx, col_idx = find_header_row(table)
    if header_row_idx is None or col_idx is None:
        return []

    part_numbers = []

    # Try rows ABOVE the header first (common in engineering drawings)
    for row in table[:header_row_idx]:
        if col_idx < len(row):
            value = row[col_idx]
            if value and value.strip():
                # Skip values that look like headers or non-part-numbers
                clean_val = value.strip()
                if not _is_header_like(clean_val):
                    part_numbers.append(clean_val)

    # If no part numbers found above, try rows BELOW the header
    if not part_numbers:
        for row in table[header_row_idx + 1:]:
            if col_idx < len(row):
                value = row[col_idx]
                if value and value.strip():
                    clean_val = value.strip()
                    if not _is_header_like(clean_val):
                        part_numbers.append(clean_val)

    return part_numbers


def _is_header_like(value: str) -> bool:
    """Check if a value looks like a header rather than a part number."""
    header_keywords = ['part', 'number', 'pos', 'title', 'description',
                       'material', 'mass', 'qty', 'quantity', 'item']
    normalized = value.lower().strip()
    return normalized in header_keywords or len(normalized) > 50


def get_table_position(table: pdfplumber.table.Table) -> Tuple[float, float]:
    """Get the bottom-right position of a table (higher x, higher y = more bottom-right)."""
    bbox = table.bbox  # (x0, top, x1, bottom)
    return (bbox[2], bbox[3])  # x1 (right edge), bottom


def extract_part_numbers(pdf_path: Union[str, Path]) -> List[str]:
    """
    Extract PART NUMBER values from a PDF file.

    Focuses on the bottom-right table if multiple tables exist.
    Returns a list of part number strings.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    all_tables_with_pos: List[Tuple[Tuple[float, float], int, pdfplumber.table.Table]] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            tables = page.find_tables()
            for table in tables:
                pos = get_table_position(table)
                # Weight by page number (later pages = higher priority for "bottom")
                weighted_pos = (pos[0], pos[1] + page_num * 10000)
                all_tables_with_pos.append((weighted_pos, page_num, table))

    if not all_tables_with_pos:
        return []

    # Sort by position: prioritize bottom-right (higher x1, higher y/page)
    # We'll try tables from bottom-right first
    all_tables_with_pos.sort(key=lambda x: (x[0][1], x[0][0]), reverse=True)

    # Try each table starting from bottom-right until we find PART NUMBER column
    for _, page_num, table in all_tables_with_pos:
        extracted = table.extract()
        if extracted:
            part_numbers = extract_part_numbers_from_table(extracted)
            if part_numbers:
                return part_numbers

    return []


def extract_part_numbers_batch(pdf_paths: List[Union[str, Path]]) -> Dict[str, List[str]]:
    """
    Extract part numbers from multiple PDFs.

    Returns a dict mapping PDF filename to list of part numbers.
    """
    results = {}
    for pdf_path in pdf_paths:
        path = Path(pdf_path)
        try:
            part_numbers = extract_part_numbers(path)
            results[path.name] = part_numbers
        except Exception as e:
            results[path.name] = []
    return results
