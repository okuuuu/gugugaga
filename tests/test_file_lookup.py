"""Tests for file_lookup module."""

import tempfile
from pathlib import Path

import pytest

from kv_pet.file_lookup import (
    find_matching_files,
    normalize_for_match,
    scan_folder,
)


class TestNormalizeForMatch:
    def test_lowercase(self):
        assert normalize_for_match("ABC123") == "abc123"

    def test_removes_spaces(self):
        assert normalize_for_match("ABC 123") == "abc123"

    def test_removes_dashes(self):
        assert normalize_for_match("ABC-123") == "abc123"

    def test_removes_underscores(self):
        assert normalize_for_match("ABC_123") == "abc123"

    def test_combined(self):
        assert normalize_for_match("ABC - 123_XYZ") == "abc123xyz"


class TestScanFolder:
    def test_scan_empty_folder(self, tmp_path):
        files = scan_folder(tmp_path)
        assert files == []

    def test_scan_folder_with_files(self, tmp_path):
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.pdf").touch()
        files = scan_folder(tmp_path)
        assert len(files) == 2

    def test_scan_folder_recursive(self, tmp_path):
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "file1.txt").touch()
        (subdir / "file2.txt").touch()
        files = scan_folder(tmp_path, recursive=True)
        assert len(files) == 2

    def test_scan_folder_non_recursive(self, tmp_path):
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "file1.txt").touch()
        (subdir / "file2.txt").touch()
        files = scan_folder(tmp_path, recursive=False)
        assert len(files) == 1

    def test_scan_nonexistent_folder(self):
        with pytest.raises(FileNotFoundError):
            scan_folder("/nonexistent/path")


class TestFindMatchingFiles:
    def test_contains_match(self, tmp_path):
        files = [
            tmp_path / "ABC123_drawing.pdf",
            tmp_path / "other_file.pdf",
        ]
        for f in files:
            f.touch()

        matches = find_matching_files("ABC123", files, match_mode="contains")
        assert len(matches) == 1
        assert matches[0].stem == "ABC123_drawing"

    def test_exact_match(self, tmp_path):
        files = [
            tmp_path / "ABC123.pdf",
            tmp_path / "ABC123_extra.pdf",
        ]
        for f in files:
            f.touch()

        matches = find_matching_files("ABC123", files, match_mode="exact")
        assert len(matches) == 1
        assert matches[0].stem == "ABC123"

    def test_startswith_match(self, tmp_path):
        files = [
            tmp_path / "ABC123_rev1.pdf",
            tmp_path / "XYZ_ABC123.pdf",
        ]
        for f in files:
            f.touch()

        matches = find_matching_files("ABC123", files, match_mode="startswith")
        assert len(matches) == 1
        assert matches[0].stem == "ABC123_rev1"

    def test_case_insensitive(self, tmp_path):
        files = [tmp_path / "abc123.pdf"]
        files[0].touch()

        matches = find_matching_files("ABC123", files, match_mode="contains")
        assert len(matches) == 1

    def test_ignores_dashes(self, tmp_path):
        files = [tmp_path / "ABC-123.pdf"]
        files[0].touch()

        matches = find_matching_files("ABC123", files, match_mode="contains")
        assert len(matches) == 1
