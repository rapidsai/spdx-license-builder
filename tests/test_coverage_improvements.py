#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Additional tests to improve code coverage.

These tests target previously uncovered edge cases and error handling paths.
"""

import io
from unittest import mock

import pytest

from spdx_license_builder.extractors import (
    DependencyLicenseExtractor,
    LicenseReportBuilder,
    SpdxExtractor,
)
from spdx_license_builder.license_records import (
    DependencyLicense,
    LicenseReport,
    LicenseText,
    SpdxEntry,
    UnifiedLicenseEntry,
)
from spdx_license_builder.utility import (
    extract_copyright_from_license_text,
    find_project_license_file,
    get_license_text,
    get_project_relative_path,
    walk_directories_for_files,
)


class TestUtilityEdgeCases:
    """Test edge cases in utility functions."""

    def test_extract_copyright_no_match_after_copyright_keyword(self):
        """Test copyright extraction when line has 'Copyright' but no valid pattern."""
        # This tests the case where we have 'copyright' but none of the patterns match
        license_text = """
Copyright somethingweird
Copyright
"""
        copyrights = extract_copyright_from_license_text(license_text)
        # Should not extract invalid copyright lines
        assert len(copyrights) == 0

    def test_get_project_relative_path_no_markers_no_root(self):
        """Test get_project_relative_path with no markers and no project root."""
        # This should hit line 246 fallback
        result = get_project_relative_path("/some/random/path/file.txt")
        project_name, rel_path = result
        assert project_name is None
        assert rel_path == "file.txt"

    def test_get_license_text_with_network_fetch(self, tmp_path):
        """Test fetching license from SPDX API (network call)."""
        # Create directories but no license files
        common_licenses = tmp_path / "common_licenses"
        common_licenses.mkdir()
        infrequent_licenses = tmp_path / "infrequent_licenses"
        infrequent_licenses.mkdir()

        # Try to fetch a real license (will hit network code)
        # Use ISC as it's small and should be quick
        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            # Mock a successful response
            mock_response = mock.MagicMock()
            mock_response.read.return_value = b'{"licenseText": "ISC License Text"}'
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            result = get_license_text("ISC", tmp_path)
            assert result == "ISC License Text"

            # Verify the license was cached
            cached_file = infrequent_licenses / "ISC.txt"
            assert cached_file.exists()
            assert "ISC License Text" in cached_file.read_text()

    def test_get_license_text_http_error(self, tmp_path):
        """Test handling of HTTP error when fetching license."""
        common_licenses = tmp_path / "common_licenses"
        common_licenses.mkdir()
        infrequent_licenses = tmp_path / "infrequent_licenses"
        infrequent_licenses.mkdir()

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            # Mock HTTP 404 error
            import urllib.error

            mock_urlopen.side_effect = urllib.error.HTTPError(
                "http://test", 404, "Not Found", {}, None
            )

            with pytest.raises(RuntimeError, match="Could not fetch license.*HTTP 404"):
                get_license_text("NONEXISTENT-LICENSE", tmp_path)

    def test_get_license_text_url_error(self, tmp_path):
        """Test handling of URL error when fetching license."""
        common_licenses = tmp_path / "common_licenses"
        common_licenses.mkdir()

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            # Mock network error
            import urllib.error

            mock_urlopen.side_effect = urllib.error.URLError("Network error")

            with pytest.raises(RuntimeError, match="Failed to fetch license.*Network error"):
                get_license_text("TEST-LICENSE", tmp_path)

    def test_get_license_text_json_decode_error(self, tmp_path):
        """Test handling of JSON decode error."""
        common_licenses = tmp_path / "common_licenses"
        common_licenses.mkdir()

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            # Mock response with invalid JSON
            mock_response = mock.MagicMock()
            mock_response.read.return_value = b"invalid json {{"
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            with pytest.raises(RuntimeError, match="Failed to fetch license"):
                get_license_text("TEST-LICENSE", tmp_path)

    def test_get_license_text_no_license_text_field(self, tmp_path):
        """Test handling when SPDX response has no licenseText field."""
        common_licenses = tmp_path / "common_licenses"
        common_licenses.mkdir()

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            # Mock response with no licenseText field
            mock_response = mock.MagicMock()
            mock_response.read.return_value = b'{"licenseId": "TEST", "name": "Test License"}'
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            with pytest.raises(ValueError, match="No licenseText field found"):
                get_license_text("TEST-LICENSE", tmp_path)

    def test_get_license_text_cache_write_error(self, tmp_path):
        """Test handling of error when writing cache file."""
        common_licenses = tmp_path / "common_licenses"
        common_licenses.mkdir()

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            # Mock successful fetch
            mock_response = mock.MagicMock()
            mock_response.read.return_value = b'{"licenseText": "Test License"}'
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            # Mock file write to fail
            with mock.patch("builtins.open", side_effect=OSError("Write error")):
                # Should still return the license text even if caching fails
                result = get_license_text("TEST-LICENSE", tmp_path)
                assert result == "Test License"

    def test_get_license_text_read_error(self, tmp_path):
        """Test handling of error when reading cached license file."""
        common_licenses = tmp_path / "common_licenses"
        common_licenses.mkdir()
        license_file = common_licenses / "TEST.txt"
        license_file.write_text("Test")

        # Mock file read to fail
        with (
            mock.patch("builtins.open", side_effect=OSError("Read error")),
            pytest.raises(RuntimeError, match="Could not read license file"),
        ):
            get_license_text("TEST", tmp_path)

    def test_find_project_license_read_error(self, tmp_path):
        """Test handling of read error in find_project_license_file."""
        license_file = tmp_path / "LICENSE"
        license_file.write_text("Apache License")

        # Mock file read to fail
        with mock.patch("builtins.open", side_effect=OSError("Read error")):
            result = find_project_license_file(tmp_path)
            # Should try next file in priority list, but since there's only LICENSE, returns None
            assert result is None

    def test_walk_directories_for_files_string_pattern(self, tmp_path):
        """Test walk_directories_for_files with single string pattern."""
        # Create test structure
        (tmp_path / "LICENSE").write_text("license")
        (tmp_path / "README").write_text("readme")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "LICENSE.txt").write_text("license")

        # Test with string pattern (not list)
        files = walk_directories_for_files(str(tmp_path), (), "LICENSE")
        assert len(files) == 2  # LICENSE and LICENSE.txt
        assert any("LICENSE" in f and "txt" not in f for f in files)
        assert any("LICENSE.txt" in f for f in files)


class TestExtractorEdgeCases:
    """Test edge cases in extractor classes."""

    def test_spdx_extractor_file_not_readable(self, tmp_path):
        """Test handling of unreadable files."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        test_file = src_dir / "test.cpp"
        test_file.write_text("// SPDX-License-Identifier: MIT\n")

        # Mock file opening to fail
        extractor = SpdxExtractor([tmp_path], verbose=False)
        with mock.patch("builtins.open", side_effect=OSError("Permission denied")):
            # Should handle the error gracefully
            file_map = extractor.extract()
            assert len(file_map) == 0

    def test_spdx_extractor_unicode_decode_error(self, tmp_path):
        """Test handling of unicode decode errors."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        test_file = src_dir / "test.cpp"
        # Write binary data that will cause decode errors
        test_file.write_bytes(b"\xff\xfe\x00\x00")

        extractor = SpdxExtractor([tmp_path], verbose=False)
        # Should handle decode errors gracefully with errors='ignore'
        file_map = extractor.extract()
        # File should be skipped
        assert len(file_map) == 0

    def test_dependency_extractor_read_error(self, tmp_path):
        """Test handling of read error in dependency license extraction."""
        third_party = tmp_path / "third_party"
        third_party.mkdir()
        license_file = third_party / "LICENSE"
        license_file.write_text("MIT License")

        extractor = DependencyLicenseExtractor([tmp_path], verbose=False)

        # Mock file read to fail
        with mock.patch("builtins.open", side_effect=OSError("Read error")):
            content_map = extractor.extract()
            # Should skip the file and continue
            assert len(content_map) == 0

    def test_license_report_builder_verbose_mode(self, tmp_path, capsys):
        """Test verbose output in LicenseReportBuilder."""
        # Create project LICENSE
        license_file = tmp_path / "LICENSE"
        license_file.write_text(
            """
        MIT License
        Permission is hereby granted, free of charge, to deal in the Software without restriction...
        """
        )

        # Create source file with matching license
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        source_file = src_dir / "test.cpp"
        source_file.write_text(
            """
        // SPDX-FileCopyrightText: Copyright (c) 2023, Test
        // SPDX-License-Identifier: MIT
        """
        )

        builder = LicenseReportBuilder([tmp_path], verbose=True)
        builder.build()

        captured = capsys.readouterr()
        # Should have verbose output
        assert len(captured.err) > 0
        assert "Project path" in captured.err


class TestLicenseRecordsEdgeCases:
    """Test edge cases in license record classes."""

    def test_license_text_none_text(self):
        """Test LicenseText with None text."""
        license_text = LicenseText(license_id="TEST", text=None)
        output = io.StringIO()
        license_text.write(output)
        result = output.getvalue()
        assert "TEST" in result
        assert "not available" in result

    def test_dependency_license_empty_content(self):
        """Test DependencyLicense with empty content."""
        dep_license = DependencyLicense(locations={"proj": {"path/LICENSE"}}, content="")
        output = io.StringIO()
        dep_license.write(output)
        result = output.getvalue()
        assert "path/LICENSE" in result
        # Should still show location even with empty content

    def test_unified_license_entry_no_files(self):
        """Test UnifiedLicenseEntry with no files."""
        entry = UnifiedLicenseEntry(
            license_id="TEST",
            spdx_files={},
            license_files={},
            license_text="Test License",
        )
        output = io.StringIO()
        entry.write(output)
        result = output.getvalue()
        assert "No files found" in result

    def test_unified_license_entry_with_warnings(self):
        """Test UnifiedLicenseEntry with validation warnings."""
        entry = UnifiedLicenseEntry(
            license_id="GPL-3.0",
            spdx_files={"test.cpp": {"locations": {"proj": {"src/test.cpp"}}, "copyrights": []}},
            license_text="GPL License",
            in_project_license=False,
            validation_warnings=["License not found in project LICENSE"],
        )
        output = io.StringIO()
        entry.write(output, show_validation=True)
        result = output.getvalue()
        assert "WARNING" in result
        assert "not found" in result

    def test_license_report_empty(self):
        """Test empty LicenseReport."""
        report = LicenseReport()
        output = io.StringIO()
        report.write(output)
        result = output.getvalue()
        assert "No third-party licenses found" in result

    def test_license_report_fallback_format(self):
        """Test LicenseReport fallback to old format when no unified entries."""
        spdx_entry = SpdxEntry(
            filename="test.cpp",
            locations={"proj": {"src/test.cpp"}},
            licenses={"MIT": [("2023", "Test Corp")]},
        )
        report = LicenseReport(spdx_entries=[spdx_entry], unified_entries=[])
        output = io.StringIO()
        report.write(output)
        result = output.getvalue()
        assert "SECTION 1" in result  # Old format
        assert "test.cpp" in result


class TestExtractorErrorPaths:
    """Test error handling paths in extractors."""

    def test_spdx_extractor_unexpected_error(self, tmp_path):
        """Test handling of unexpected errors during file processing."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        test_file = src_dir / "test.cpp"
        test_file.write_text("// SPDX-License-Identifier: MIT\n")

        # Use sequential mode to ensure exception propagates
        extractor = SpdxExtractor([tmp_path], verbose=False, parallel=False)

        # Mock to raise an unexpected error
        original_find = extractor._find_spdx_entries
        call_count = [0]

        def mock_find_spdx_entries(file_path):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("Unexpected error")
            return original_find(file_path)

        with (
            mock.patch.object(extractor, "_find_spdx_entries", side_effect=mock_find_spdx_entries),
            pytest.raises(RuntimeError, match="Unexpected error"),
        ):
            extractor.extract()

    def test_dependency_extractor_unexpected_error(self, tmp_path):
        """Test handling of unexpected errors during LICENSE processing."""
        third_party = tmp_path / "third_party"
        third_party.mkdir()
        license_file = third_party / "LICENSE"
        license_file.write_text("MIT License")

        # Use sequential mode to ensure exception propagates
        extractor = DependencyLicenseExtractor([tmp_path], verbose=False, parallel=False)

        # Mock to raise an unexpected error

        def mock_process(*args):
            raise RuntimeError("Unexpected error")

        with (
            mock.patch.object(extractor, "_process_license_file", side_effect=mock_process),
            pytest.raises(RuntimeError, match="Unexpected error"),
        ):
            extractor.extract()

    def test_get_license_text_unexpected_error(self, tmp_path):
        """Test handling of unexpected errors when fetching license."""
        common_licenses = tmp_path / "common_licenses"
        common_licenses.mkdir()
        license_file = common_licenses / "MIT.txt"
        license_file.write_text("MIT License")

        # Mock to raise an unexpected error
        with (
            mock.patch("builtins.open", side_effect=RuntimeError("Unexpected error")),
            pytest.raises(RuntimeError, match="Unexpected error"),
        ):
            # Should raise the unexpected error
            get_license_text("MIT", tmp_path)


class TestCopyrightExtractionEdgeCases:
    """Test edge cases in copyright extraction."""

    def test_copyright_with_comma_after_year(self):
        """Test copyright with comma after year in parens."""
        license_text = "Copyright (2024), Test Company Inc."
        copyrights = extract_copyright_from_license_text(license_text)
        assert len(copyrights) == 1
        year, owner = copyrights[0]
        assert year == "2024"
        assert "Test Company" in owner

    def test_copyright_year_range_with_comma(self):
        """Test copyright with year range and comma."""
        license_text = "Copyright (c) 2020-2024, Example Corp."
        copyrights = extract_copyright_from_license_text(license_text)
        assert len(copyrights) == 1
        year, owner = copyrights[0]
        assert year == "2020-2024"
        assert "Example Corp" in owner


class TestValidationEdgeCases:
    """Test edge cases in license validation."""

    def test_validation_with_compound_license_all_present(self, tmp_path):
        """Test compound license where all components are in project LICENSE."""
        # Create project LICENSE with Apache and MIT
        license_file = tmp_path / "LICENSE"
        license_file.write_text(
            """
        Apache License
        Version 2.0, January 2004

        MIT License
        Permission is hereby granted, free of charge, to deal in the Software without restriction...
        """
        )

        # Create source file with compound license
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        source_file = src_dir / "test.cpp"
        source_file.write_text(
            """
        // SPDX-FileCopyrightText: Copyright (c) 2023, Test
        // SPDX-License-Identifier: Apache-2.0 OR MIT
        """
        )

        builder = LicenseReportBuilder([tmp_path], verbose=False)
        report = builder.build()

        # Both components should validate successfully
        for entry in report.unified_entries:
            if "OR" in entry.license_id and entry.spdx_files:
                assert entry.in_project_license is True
                assert len(entry.validation_warnings) == 0
