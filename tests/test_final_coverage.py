#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Final coverage improvements for hard-to-reach edge cases.
"""

import io
from unittest import mock

import pytest

from spdx_license_builder.extractors import LicenseExtractor, SpdxExtractor
from spdx_license_builder.license_records import UnifiedLicenseEntry
from spdx_license_builder.utility import extract_copyright_from_license_text


class TestRemainingUtilityGaps:
    """Test remaining gaps in utility.py."""

    def test_copyright_extraction_line_83_break_path(self):
        """Test copyright extraction with pattern match and break."""
        # This should hit line 83 and the break on line 86
        license_text = """
Copyright (c) 2020, First Company
Copyright (c) 2021, Second Company
"""
        copyrights = extract_copyright_from_license_text(license_text)
        assert len(copyrights) == 2

    def test_find_project_license_unicode_decode_error(self, tmp_path):
        """Test find_project_license_file with unicode decode error."""
        from spdx_license_builder.utility import find_project_license_file

        license_file = tmp_path / "LICENSE"
        license_file.write_bytes(b"\xff\xfe")  # Invalid UTF-8

        # Should try to read with errors='ignore' and continue
        result = find_project_license_file(tmp_path)
        # Should return something (might be empty licenses list)
        assert result is not None

    def test_find_project_license_unexpected_exception(self, tmp_path):
        """Test find_project_license_file with unexpected exception."""
        from spdx_license_builder.utility import find_project_license_file

        license_file = tmp_path / "LICENSE"
        license_file.write_text("Apache License")

        # Mock to raise unexpected error
        with (
            mock.patch("builtins.open", side_effect=ValueError("Unexpected")),
            pytest.raises(ValueError),
        ):
            find_project_license_file(tmp_path)

    def test_get_license_text_oserror_during_cache(self, tmp_path):
        """Test get_license_text with OSError during cache write."""
        from spdx_license_builder.utility import get_license_text

        common_licenses = tmp_path / "common_licenses"
        common_licenses.mkdir()
        infrequent = tmp_path / "infrequent_licenses"
        infrequent.mkdir()

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            # Mock successful fetch
            mock_response = mock.MagicMock()
            mock_response.read.return_value = b'{"licenseText": "Test"}'
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            # Make file writing fail (after directory is created)
            original_open = open

            def mock_open_func(file, *args, **kwargs):
                if "infrequent_licenses" in str(file) and "w" in args:
                    raise OSError("Cannot write")
                return original_open(file, *args, **kwargs)

            with mock.patch("builtins.open", side_effect=mock_open_func):
                # Should still return text even if caching fails
                result = get_license_text("TEST", tmp_path)
                assert result == "Test"

    def test_walk_directories_for_files_with_exclusions(self, tmp_path):
        """Test walk_directories_for_files with actual exclusions."""
        from spdx_license_builder.utility import walk_directories_for_files

        # Create structure
        (tmp_path / "LICENSE").write_text("root")
        excluded_dir = tmp_path / "excluded_dir"
        excluded_dir.mkdir()
        (excluded_dir / "LICENSE").write_text("excluded")
        included_dir = tmp_path / "src"
        included_dir.mkdir()
        (included_dir / "LICENSE").write_text("included")

        files = walk_directories_for_files(str(tmp_path), ("excluded_dir",), "LICENSE")

        # Should find 2 files (root and src), not excluded_dir
        assert len(files) == 2
        assert not any("excluded_dir" in f for f in files)


class TestRemainingExtractorGaps:
    """Test remaining gaps in extractors.py."""

    def test_license_extractor_base_extract_not_implemented(self, tmp_path):
        """Test that base LicenseExtractor.extract() raises NotImplementedError."""
        extractor = LicenseExtractor([tmp_path], verbose=False)
        with pytest.raises(NotImplementedError):
            extractor.extract()

    def test_license_extractor_invalid_path(self, tmp_path):
        """Test LicenseExtractor with invalid path."""
        fake_path = tmp_path / "nonexistent"
        with pytest.raises(SystemExit):
            LicenseExtractor([fake_path], verbose=False)

    def test_license_extractor_file_not_directory(self, tmp_path):
        """Test LicenseExtractor with file instead of directory."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")
        with pytest.raises(SystemExit):
            LicenseExtractor([file_path], verbose=False)

    def test_spdx_extractor_copyright_pattern_315(self, tmp_path):
        """Test SPDX extractor with copyright that hits line 315."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        test_file = src_dir / "test.cpp"
        # Copyright with year but fails validation (line 309-310)
        test_file.write_text(
            """
        // SPDX-FileCopyrightText: Copyright January 2024 Company
        // SPDX-License-Identifier: MIT
        """
        )

        extractor = SpdxExtractor([tmp_path], verbose=False)
        file_map = extractor.extract()
        # Should skip invalid copyright
        assert len(file_map) == 0 or (
            len(file_map) == 1 and len(list(file_map.values())[0]["licenses"]) == 0
        )

    def test_spdx_extractor_additional_exclude_dirs(self, tmp_path):
        """Test SpdxExtractor with additional_exclude_dirs."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()

        (src_dir / "test.cpp").write_text(
            """
        // SPDX-FileCopyrightText: Copyright (c) 2023, Test
        // SPDX-License-Identifier: MIT
        """
        )

        (custom_dir / "test.cpp").write_text(
            """
        // SPDX-FileCopyrightText: Copyright (c) 2023, Test
        // SPDX-License-Identifier: MIT
        """
        )

        # Use additional_exclude_dirs
        extractor = SpdxExtractor([tmp_path], additional_exclude_dirs=("custom",), verbose=False)
        file_map = extractor.extract()

        # Should find src but not custom
        assert len(file_map) > 0
        # All paths should be in src, not custom
        for info in file_map.values():
            for path in info["paths"]:
                assert "custom" not in path


class TestRemainingRecordGaps:
    """Test remaining gaps in license_records.py."""

    def test_unified_license_entry_no_copyrights(self):
        """Test UnifiedLicenseEntry with files but no copyrights."""
        entry = UnifiedLicenseEntry(
            license_id="MIT",
            spdx_files={
                "test.cpp": {
                    "locations": {"proj": {"src/test.cpp"}},
                    "copyrights": [],  # Empty copyrights
                }
            },
            license_text="MIT License",
        )
        output = io.StringIO()
        entry.write(output)
        result = output.getvalue()
        assert "test.cpp" in result or "src/test.cpp" in result

    def test_unified_license_entry_license_files_no_copyright(self):
        """Test UnifiedLicenseEntry with license files but no copyright info."""
        entry = UnifiedLicenseEntry(
            license_id="Apache-2.0",
            license_files={"proj": {"LICENSE"}},
            license_file_copyrights={},  # No copyright info
            license_text="Apache License",
        )
        output = io.StringIO()
        entry.write(output)
        result = output.getvalue()
        assert "LICENSE" in result


class TestAliasingAndEdgeCases:
    """Test license aliasing and edge cases."""

    def test_license_alias_bsd_3(self, tmp_path):
        """Test that BSD-3 is aliased to BSD-3-Clause."""
        from spdx_license_builder.utility import get_license_text

        common_licenses = tmp_path / "common_licenses"
        common_licenses.mkdir()
        license_file = common_licenses / "BSD-3-Clause.txt"
        license_file.write_text("BSD 3-Clause License")

        # Request BSD-3 (should map to BSD-3-Clause)
        result = get_license_text("BSD-3", tmp_path)
        assert result == "BSD 3-Clause License"

    def test_spdx_extractor_no_license_after_copyright(self, tmp_path):
        """Test SPDX file with copyright but no license (goes past line 390)."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        test_file = src_dir / "test.cpp"
        test_file.write_text(
            """
        // SPDX-FileCopyrightText: Copyright (c) 2023, Test Corp
        // Some other comment
        // No license identifier
        """
        )

        extractor = SpdxExtractor([tmp_path], verbose=False)
        file_map = extractor.extract()
        # Should not extract anything (no license found)
        assert len(file_map) == 0


class TestBuildReportEdgeCases:
    """Test edge cases in report building."""

    def test_license_report_builder_no_license_texts(self, tmp_path):
        """Test report builder with with_licenses=False."""
        from spdx_license_builder.extractors import LicenseReportBuilder

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "test.cpp").write_text(
            """
        // SPDX-FileCopyrightText: Copyright (c) 2023, Test
        // SPDX-License-Identifier: MIT
        """
        )

        builder = LicenseReportBuilder([tmp_path], with_licenses=False, verbose=False)
        report = builder.build()

        # Should have entries but no license texts
        assert len(report.license_texts) == 0
        assert len(report.unified_entries) > 0

    def test_spdx_extractor_custom_exclusions(self, tmp_path):
        """Test SpdxExtractor with custom directories_to_exclude."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        custom = tmp_path / "custom"
        custom.mkdir()

        (src_dir / "test.cpp").write_text(
            """
        // SPDX-FileCopyrightText: Copyright (c) 2023, Test
        // SPDX-License-Identifier: MIT
        """
        )

        (custom / "test.cpp").write_text(
            """
        // SPDX-FileCopyrightText: Copyright (c) 2023, Test
        // SPDX-License-Identifier: MIT
        """
        )

        # Use custom directories_to_exclude (replaces defaults)
        extractor = SpdxExtractor([tmp_path], directories_to_exclude=("custom",), verbose=False)
        file_map = extractor.extract()

        # Should only exclude 'custom', not default exclusions like 'tests'
        assert len(file_map) > 0
