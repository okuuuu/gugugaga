"""PDF table parsing and PART NUMBER extraction logic."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pdfplumber


@dataclass
class PartRow:
    """A single row from the parts table with all extracted fields."""

    part_number: str
    title: str = ""
    description: str = ""
    material: str = ""
    mass: str = ""
    qty: str = ""


# Column name variations to match
COLUMN_ALIASES = {
    "partnumber": ["partnumber", "partno", "pn", "part"],
    "title": ["title", "name"],
    "description": ["description", "desc"],
    "material": ["material", "mat"],
    "mass": ["mass", "weight", "wt"],
    "qty": ["qty", "quantity", "count"],
}


def normalize_header(text: Optional[str]) -> str:
    """Normalize header text for comparison (lowercase, strip spaces/special chars)."""
    if text is None:
        return ""
    return "".join(text.lower().split()).replace("-", "").replace("_", "")


def find_column_index(headers: List[Optional[str]], column_name: str) -> Optional[int]:
    """Find the index of a column by checking against known aliases."""
    aliases = COLUMN_ALIASES.get(column_name, [column_name])
    for i, header in enumerate(headers):
        normalized = normalize_header(header)
        if normalized in aliases:
            return i
    return None


def find_part_number_column(headers: List[Optional[str]]) -> Optional[int]:
    """Find the index of the PART NUMBER column in a table header row."""
    return find_column_index(headers, "partnumber")


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


def _is_header_like(value: str) -> bool:
    """Check if a value looks like a header rather than a part number."""
    header_keywords = ['part', 'number', 'pos', 'title', 'description',
                       'material', 'mass', 'qty', 'quantity', 'item']
    normalized = value.lower().strip()
    return normalized in header_keywords or len(normalized) > 50


def _get_cell_value(row: List[Optional[str]], idx: Optional[int]) -> str:
    """Safely get a cell value from a row."""
    if idx is None or idx >= len(row):
        return ""
    value = row[idx]
    return value.strip() if value else ""


def extract_part_rows_from_table(table: List[List[Optional[str]]]) -> List[PartRow]:
    """
    Extract part rows with all fields from a table.

    Handles engineering drawings where header may be at the bottom of the parts list.
    """
    if not table or len(table) < 2:
        return []

    header_row_idx, pn_col_idx = find_header_row(table)
    if header_row_idx is None or pn_col_idx is None:
        return []

    # Get the header row and find all column indices
    header_row = table[header_row_idx]
    col_indices = {
        "part_number": pn_col_idx,
        "title": find_column_index(header_row, "title"),
        "description": find_column_index(header_row, "description"),
        "material": find_column_index(header_row, "material"),
        "mass": find_column_index(header_row, "mass"),
        "qty": find_column_index(header_row, "qty"),
    }

    part_rows = []

    # Determine which rows contain data (above or below header)
    data_rows = table[:header_row_idx]  # Try rows above header first
    if not any(_get_cell_value(row, pn_col_idx) for row in data_rows if not _is_header_like(_get_cell_value(row, pn_col_idx) or "")):
        data_rows = table[header_row_idx + 1:]  # Fall back to rows below

    for row in data_rows:
        pn_value = _get_cell_value(row, col_indices["part_number"])
        if pn_value and not _is_header_like(pn_value):
            part_row = PartRow(
                part_number=pn_value,
                title=_get_cell_value(row, col_indices["title"]),
                description=_get_cell_value(row, col_indices["description"]),
                material=_get_cell_value(row, col_indices["material"]),
                mass=_get_cell_value(row, col_indices["mass"]),
                qty=_get_cell_value(row, col_indices["qty"]),
            )
            part_rows.append(part_row)

    return part_rows


def extract_part_numbers_from_table(table: List[List[Optional[str]]]) -> List[str]:
    """
    Extract part numbers from a table that has a PART NUMBER column.

    Legacy function - returns only part number strings for backwards compatibility.
    """
    rows = extract_part_rows_from_table(table)
    return [row.part_number for row in rows]


def get_table_position(table: pdfplumber.table.Table) -> Tuple[float, float]:
    """Get the bottom-right position of a table (higher x, higher y = more bottom-right)."""
    bbox = table.bbox  # (x0, top, x1, bottom)
    return (bbox[2], bbox[3])  # x1 (right edge), bottom


def extract_part_rows(pdf_path: Union[str, Path]) -> List[PartRow]:
    """
    Extract part rows with all fields from a PDF file.

    Focuses on the bottom-right table if multiple tables exist.
    Returns a list of PartRow objects with all available fields.
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
                weighted_pos = (pos[0], pos[1] + page_num * 10000)
                all_tables_with_pos.append((weighted_pos, page_num, table))

    if not all_tables_with_pos:
        return []

    all_tables_with_pos.sort(key=lambda x: (x[0][1], x[0][0]), reverse=True)

    for _, page_num, table in all_tables_with_pos:
        extracted = table.extract()
        if extracted:
            part_rows = extract_part_rows_from_table(extracted)
            if part_rows:
                return part_rows

    return []


def extract_part_numbers(pdf_path: Union[str, Path]) -> List[str]:
    """
    Extract PART NUMBER values from a PDF file.

    Legacy function - returns only part number strings for backwards compatibility.
    """
    rows = extract_part_rows(pdf_path)
    return [row.part_number for row in rows]


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
