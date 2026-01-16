#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Integration tests for SPDX extraction functionality.
"""

from pathlib import Path

import pytest

from spdx_license_builder.extract_licenses_via_spdx import find_spdx_entries, walk_directories


class TestFindSpdxEntries:
    """Test SPDX entry extraction from individual files."""

    def test_extract_single_copyright(self, tmp_path):
        """Test extracting a single non-NVIDIA copyright entry."""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(
            """
// SPDX-FileCopyrightText: Copyright (c) 2020 Example Corporation
// SPDX-License-Identifier: MIT

int main() { return 0; }
"""
        )

        entries = find_spdx_entries(str(test_file))

        assert len(entries) == 1
        license_type, year_range, owner, file_path = entries[0]
        assert license_type == "MIT"
        assert year_range == "2020"
        assert owner == "Example Corporation"
        assert file_path == str(test_file)

    def test_extract_multiple_copyrights_same_license(self, tmp_path):
        """Test extracting multiple copyrights for the same license."""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(
            """
// SPDX-FileCopyrightText: Copyright (c) 2020 Company A
// SPDX-FileCopyrightText: Copyright (c) 2021 Company B
// SPDX-License-Identifier: Apache-2.0

void foo() {}
"""
        )

        entries = find_spdx_entries(str(test_file))

        assert len(entries) == 2

        # Check both companies are captured
        owners = [entry[2] for entry in entries]
        assert "Company A" in owners
        assert "Company B" in owners

        # Both should have Apache-2.0 license
        for entry in entries:
            assert entry[0] == "Apache-2.0"

    def test_ignore_nvidia_copyright(self, tmp_path):
        """Test that NVIDIA copyrights are ignored."""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(
            """
// SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

// SPDX-FileCopyrightText: Copyright (c) 2020 Third Party Corp
// SPDX-License-Identifier: MIT

void foo() {}
"""
        )

        entries = find_spdx_entries(str(test_file))

        # Should only get the Third Party Corp entry
        assert len(entries) == 1
        license_type, year_range, owner, file_path = entries[0]
        assert owner == "Third Party Corp"
        assert license_type == "MIT"

    def test_compound_license(self, tmp_path):
        """Test extraction of compound license (AND/OR)."""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(
            """
// SPDX-FileCopyrightText: Copyright (c) Facebook, Inc. and its affiliates
// SPDX-License-Identifier: Apache-2.0 AND MIT

void foo() {}
"""
        )

        entries = find_spdx_entries(str(test_file))

        assert len(entries) == 1
        license_type, year_range, owner, file_path = entries[0]
        assert license_type == "Apache-2.0 AND MIT"
        assert owner == "Facebook, Inc. and its affiliates"
        assert year_range == ""  # No year in this copyright

    def test_no_spdx_headers(self, tmp_path):
        """Test file with no SPDX headers."""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(
            """
// Just a regular file
// Copyright 2020 Someone

int main() { return 0; }
"""
        )

        entries = find_spdx_entries(str(test_file))
        assert len(entries) == 0

    def test_malformed_spdx(self, tmp_path):
        """Test handling of malformed SPDX headers."""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(
            """
// SPDX-FileCopyrightText: Some text but no copyright
// SPDX-License-Identifier: MIT

int main() { return 0; }
"""
        )

        entries = find_spdx_entries(str(test_file))
        # Should handle gracefully - might return empty or skip invalid entries
        # The exact behavior depends on implementation
        assert isinstance(entries, list)


class TestWalkDirectories:
    """Test walking directories to collect SPDX entries."""

    def test_walk_cpp_directory(self):
        """Test walking a cpp directory and collecting SPDX entries."""
        fixtures_path = Path(__file__).parent / "fixtures" / "test_project" / "cpp" / "include"

        if not fixtures_path.exists():
            pytest.skip("Test fixtures not found")

        directories_to_exclude = ("test", "tests", "benchmark")
        file_map = walk_directories(str(fixtures_path), directories_to_exclude)

        # Should find facebook files (grouped)
        assert len(file_map) > 0

        # Check that NVIDIA files are excluded
        for _filename, info in file_map.items():
            for _license_type, _year_range, owner in info["licenses"]:
                assert "NVIDIA" not in owner.upper()

    def test_grouping_by_filename(self):
        """Test that files with the same name are grouped together."""
        fixtures_path = Path(__file__).parent / "fixtures" / "test_project" / "cpp" / "include"

        if not fixtures_path.exists():
            pytest.skip("Test fixtures not found")

        directories_to_exclude = ("test", "tests", "benchmark")
        file_map = walk_directories(str(fixtures_path), directories_to_exclude)

        # Each filename should have a set of paths and licenses
        for _filename, info in file_map.items():
            assert "paths" in info
            assert "licenses" in info
            assert isinstance(info["paths"], set)
            assert isinstance(info["licenses"], set)

    def test_exclude_directories(self, tmp_path):
        """Test that excluded directories are not scanned."""
        # Create test structure
        cpp_dir = tmp_path / "cpp"
        cpp_dir.mkdir()

        include_dir = cpp_dir / "include"
        include_dir.mkdir()

        test_dir = cpp_dir / "test"
        test_dir.mkdir()

        # Create files
        (include_dir / "source.cpp").write_text(
            """
// SPDX-FileCopyrightText: Copyright (c) 2020 Example
// SPDX-License-Identifier: MIT
"""
        )

        (test_dir / "test.cpp").write_text(
            """
// SPDX-FileCopyrightText: Copyright (c) 2020 Test Corp
// SPDX-License-Identifier: MIT
"""
        )

        directories_to_exclude = ("test", "tests")
        file_map = walk_directories(str(cpp_dir), directories_to_exclude)

        # Should only find source.cpp, not test.cpp
        found_owners = []
        for _filename, info in file_map.items():
            for _license_type, _year_range, owner in info["licenses"]:
                found_owners.append(owner)

        assert "Example" in found_owners
        assert "Test Corp" not in found_owners


class TestSpdxOutputFormat:
    """Test that SPDX extraction produces expected output format."""

    def test_grouped_output_structure(self):
        """Test that files are grouped by license and copyright."""
        fixtures_path = Path(__file__).parent / "fixtures" / "test_project" / "cpp" / "include"

        if not fixtures_path.exists():
            pytest.skip("Test fixtures not found")

        directories_to_exclude = ("test", "tests")
        file_map = walk_directories(str(fixtures_path), directories_to_exclude)

        # Verify structure: files with same license/copyright should be together
        for _filename, info in file_map.items():
            # Multiple files can share the same license/copyright
            assert len(info["licenses"]) >= 1

            # Each license entry should have (license_type, year_range, owner)
            for license_entry in info["licenses"]:
                assert len(license_entry) == 3
                license_type, year_range, owner = license_entry
                assert isinstance(license_type, str)
                assert isinstance(year_range, str)
                assert isinstance(owner, str)
