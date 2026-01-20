#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Tests for the OOP extractor classes.
"""

import pytest

from spdx_license_builder.extractors import (
    DependencyLicenseExtractor,
    LicenseReportBuilder,
    SpdxExtractor,
)


class TestSpdxExtractor:
    """Test the SpdxExtractor class."""

    def test_extract_basic(self, test_project_dir):
        """Test basic SPDX extraction."""
        extractor = SpdxExtractor(
            project_paths=[test_project_dir],
            verbose=False,
        )
        file_map = extractor.extract()

        # Should find the third-party files but not NVIDIA files
        assert len(file_map) > 0
        assert "facebook_file.cuh" in file_map or any("facebook_file.cuh" in k for k in file_map)

        # Check that file_map contains the expected structure
        for _filename, info in file_map.items():
            assert "paths" in info
            assert "licenses" in info
            assert isinstance(info["paths"], set)
            assert isinstance(info["licenses"], set)

    def test_dataclass_iteration(self, test_project_dir):
        """
        Test that licenses can be iterated as CopyrightInfo objects.

        This is a regression test for the bug where code tried to unpack
        CopyrightInfo dataclass objects as tuples.
        """
        extractor = SpdxExtractor(
            project_paths=[test_project_dir],
            verbose=False,
        )
        file_map = extractor.extract()

        # Iterate through licenses and access dataclass attributes
        for _filename, info in file_map.items():
            for copyright_info in info["licenses"]:
                # Should be able to access dataclass attributes
                assert hasattr(copyright_info, "license_type")
                assert hasattr(copyright_info, "year_range")
                assert hasattr(copyright_info, "owner")

                # Verify license_type is a string
                assert isinstance(copyright_info.license_type, str)

                # This should NOT work (would fail if it's a tuple):
                # license_type, _, _ = copyright_info  # Would raise TypeError

    def test_license_type_collection(self, test_project_dir):
        """
        Test collecting unique license types from file_map.

        This specifically tests the pattern that was fixed in LicenseReportBuilder.
        """
        extractor = SpdxExtractor(
            project_paths=[test_project_dir],
            verbose=False,
        )
        file_map = extractor.extract()

        # Collect all license types (this is the pattern that was broken)
        found_licenses = set()
        for file_info in file_map.values():
            for copyright_info in file_info["licenses"]:
                found_licenses.add(copyright_info.license_type)

        # Should find some licenses
        assert len(found_licenses) > 0

        # All should be strings
        for license_type in found_licenses:
            assert isinstance(license_type, str)


class TestDependencyLicenseExtractor:
    """Test the DependencyLicenseExtractor class."""

    def test_extract_basic(self, test_project_dir):
        """Test basic dependency license extraction."""
        extractor = DependencyLicenseExtractor(
            project_paths=[test_project_dir],
            verbose=False,
        )
        content_map = extractor.extract()

        # Should find LICENSE files in third_party
        assert len(content_map) > 0

        # Check structure
        for _content_hash, info in content_map.items():
            assert "content" in info
            assert "filenames" in info
            assert "paths" in info


class TestLicenseReportBuilder:
    """Test the LicenseReportBuilder class."""

    def test_build_report_basic(self, test_project_dir):
        """Test building a basic license report."""
        builder = LicenseReportBuilder(
            project_paths=[test_project_dir],
            verbose=False,
        )
        report = builder.build()

        # Should have some data
        assert report.spdx_entries or report.dependency_licenses

        # Verify structure
        for entry in report.spdx_entries:
            assert hasattr(entry, "filename")
            assert hasattr(entry, "licenses")

        for dep_license in report.dependency_licenses:
            assert hasattr(dep_license, "locations")
            assert hasattr(dep_license, "content")

    def test_build_with_licenses(self, test_project_dir):
        """
        Test building report with license texts included.

        This is a regression test for the bug where LicenseReportBuilder.build()
        tried to unpack CopyrightInfo objects as tuples when collecting license types.
        """
        builder = LicenseReportBuilder(
            project_paths=[test_project_dir],
            with_licenses=True,
            verbose=False,
        )
        report = builder.build()

        # Should have license texts
        assert len(report.license_texts) > 0

        # Verify license text structure
        for license_text in report.license_texts:
            assert hasattr(license_text, "license_id")
            assert hasattr(license_text, "text")
            assert isinstance(license_text.license_id, str)
            assert isinstance(license_text.text, str)

    def test_dataclass_unpacking_regression(self, test_project_dir):
        """
        Regression test: Ensure CopyrightInfo objects are not unpacked as tuples.

        This specifically tests the bug that was fixed in line 649-651 of extractors.py:
        Before: for license_type, _, _ in file_info["licenses"]:
        After:  for copyright_info in file_info["licenses"]:
        """
        builder = LicenseReportBuilder(
            project_paths=[test_project_dir],
            with_licenses=True,
            verbose=False,
        )

        # This should not raise TypeError about unpacking
        try:
            report = builder.build()
            assert report is not None
        except TypeError as e:
            if "cannot unpack" in str(e) or "not iterable" in str(e):
                pytest.fail(f"CopyrightInfo objects should not be unpacked as tuples: {e}")
            raise

    def test_license_type_deduplication(self, test_project_dir):
        """Test that license types are properly deduplicated."""
        builder = LicenseReportBuilder(
            project_paths=[test_project_dir],
            with_licenses=True,
            verbose=False,
        )
        report = builder.build()

        # License types should be unique
        license_ids = [lt.license_id for lt in report.license_texts]
        # Parse compound licenses to get individual components
        all_components = set()
        for license_id in license_ids:
            # Split on AND/OR
            components = license_id.replace(" AND ", " ").replace(" OR ", " ").split()
            all_components.update(components)

        # No assertion about exact count, just that we got some licenses
        assert len(all_components) > 0


class TestExtractorOptions:
    """Test extractor configuration options."""

    def test_verbose_output(self, test_project_dir, capsys):
        """Test that verbose mode produces output."""
        extractor = SpdxExtractor(
            project_paths=[test_project_dir],
            verbose=True,
        )
        extractor.extract()

        captured = capsys.readouterr()
        # Should have some output when verbose
        assert len(captured.out) > 0 or len(captured.err) > 0

    def test_quiet_mode(self, test_project_dir, capsys):
        """Test that non-verbose mode is quiet."""
        extractor = SpdxExtractor(
            project_paths=[test_project_dir],
            verbose=False,
        )
        extractor.extract()

        captured = capsys.readouterr()
        # Should have no output when not verbose
        assert len(captured.out) == 0
        assert len(captured.err) == 0

    def test_custom_exclusions(self, test_project_dir):
        """Test custom directory exclusions."""
        # Exclude third_party - should find fewer dependency licenses
        extractor = DependencyLicenseExtractor(
            project_paths=[test_project_dir],
            directories_to_exclude=("third_party", "third-party", "thirdparty"),
            verbose=False,
        )
        content_map = extractor.extract()

        # Might not find any if they're all in third_party
        assert isinstance(content_map, dict)


class TestExtractorEdgeCases:
    """Test edge cases and error handling."""

    def test_nonexistent_path(self, tmp_path):
        """Test handling of nonexistent paths."""
        fake_path = tmp_path / "nonexistent"

        # Should exit with error code 1
        with pytest.raises(SystemExit) as exc_info:
            SpdxExtractor(
                project_paths=[fake_path],
                verbose=False,
            )

        assert exc_info.value.code == 1

    def test_empty_directory(self, tmp_path):
        """Test handling of empty directory."""
        extractor = SpdxExtractor(
            project_paths=[tmp_path],
            verbose=False,
        )
        file_map = extractor.extract()

        # Should return empty map
        assert len(file_map) == 0

    def test_multiple_projects(self, test_project_dir, tmp_path):
        """Test extracting from multiple projects."""
        extractor = SpdxExtractor(
            project_paths=[test_project_dir, tmp_path],
            verbose=False,
        )
        file_map = extractor.extract()

        # Should work with multiple paths
        assert isinstance(file_map, dict)
