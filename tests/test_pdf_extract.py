"""Tests for pdf_extract module."""

import pytest

from kv_pet.pdf_extract import (
    extract_part_numbers_from_table,
    find_part_number_column,
    normalize_header,
)


class TestNormalizeHeader:
    def test_lowercase(self):
        assert normalize_header("PART NUMBER") == "partnumber"

    def test_removes_spaces(self):
        assert normalize_header("PART  NUMBER") == "partnumber"

    def test_removes_dashes(self):
        assert normalize_header("PART-NUMBER") == "partnumber"

    def test_removes_underscores(self):
        assert normalize_header("PART_NUMBER") == "partnumber"

    def test_none_input(self):
        assert normalize_header(None) == ""


class TestFindPartNumberColumn:
    def test_finds_column(self):
        headers = ["Name", "PART NUMBER", "Quantity"]
        assert find_part_number_column(headers) == 1

    def test_case_insensitive(self):
        headers = ["Name", "part number", "Quantity"]
        assert find_part_number_column(headers) == 0 or find_part_number_column(headers) == 1
        # Re-check properly
        assert find_part_number_column(["Name", "part number", "Qty"]) == 1

    def test_with_dashes(self):
        headers = ["Name", "PART-NUMBER", "Quantity"]
        assert find_part_number_column(headers) == 1

    def test_not_found(self):
        headers = ["Name", "Description", "Quantity"]
        assert find_part_number_column(headers) is None


class TestExtractPartNumbersFromTable:
    def test_extracts_values(self):
        table = [
            ["Name", "PART NUMBER", "Qty"],
            ["Widget", "ABC123", "10"],
            ["Gadget", "XYZ789", "5"],
        ]
        result = extract_part_numbers_from_table(table)
        assert result == ["ABC123", "XYZ789"]

    def test_skips_empty_values(self):
        table = [
            ["Name", "PART NUMBER", "Qty"],
            ["Widget", "ABC123", "10"],
            ["Gadget", "", "5"],
            ["Thing", None, "3"],
        ]
        result = extract_part_numbers_from_table(table)
        assert result == ["ABC123"]

    def test_strips_whitespace(self):
        table = [
            ["Name", "PART NUMBER"],
            ["Widget", "  ABC123  "],
        ]
        result = extract_part_numbers_from_table(table)
        assert result == ["ABC123"]

    def test_no_part_number_column(self):
        table = [
            ["Name", "Description"],
            ["Widget", "A widget"],
        ]
        result = extract_part_numbers_from_table(table)
        assert result == []

    def test_empty_table(self):
        assert extract_part_numbers_from_table([]) == []

    def test_header_only(self):
        table = [["Name", "PART NUMBER"]]
        result = extract_part_numbers_from_table(table)
        assert result == []
