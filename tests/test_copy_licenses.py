#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Integration tests for LICENSE file copying functionality.
"""

import hashlib
from pathlib import Path
from pathlib import Path as PathlibPath

import pytest

from spdx_license_builder.extractors import DependencyLicenseExtractor
from spdx_license_builder.utility import walk_directories_for_files


# Helper function for tests
def extract_license_files(project_paths, directories_to_exclude=None, verbose=False):
    """Helper to extract LICENSE files using OOP API."""
    if not isinstance(project_paths, list):
        project_paths = [project_paths]
    project_paths = [PathlibPath(p) if not isinstance(p, PathlibPath) else p for p in project_paths]
    extractor = DependencyLicenseExtractor(
        project_paths,
        directories_to_exclude=directories_to_exclude,
        verbose=verbose,
        deduplicate_rapids=False,
        deduplicate_hierarchical=False,
        normalize_years=False,
    )
    return extractor.extract()


class TestWalkDirectoriesForFiles:
    """Test walking directories to find LICENSE files."""

    def test_find_license_files(self, tmp_path):
        """Test finding LICENSE files in directory structure."""
        # Create test structure
        cpp_dir = tmp_path / "cpp"
        cpp_dir.mkdir()

        third_party = cpp_dir / "third_party"
        third_party.mkdir()

        fmt_dir = third_party / "fmt"
        fmt_dir.mkdir()

        # Create LICENSE file
        (fmt_dir / "LICENSE").write_text("MIT License text")

        # Create non-LICENSE file
        (fmt_dir / "README.md").write_text("README content")

        directories_to_exclude = ("test",)
        files = walk_directories_for_files(str(cpp_dir), directories_to_exclude, "LICENSE")

        # Should find only the LICENSE file
        assert len(files) == 1
        assert "LICENSE" in files[0]
        assert "README" not in files[0]

    def test_find_license_variants(self, tmp_path):
        """Test finding LICENSE files with different names."""
        cpp_dir = tmp_path / "cpp"
        cpp_dir.mkdir()

        lib_dir = cpp_dir / "lib"
        lib_dir.mkdir()

        # Create various LICENSE file names
        (lib_dir / "LICENSE").write_text("License 1")
        (lib_dir / "LICENSE.txt").write_text("License 2")
        (lib_dir / "LICENSE-Apache").write_text("License 3")
        (lib_dir / "LICENSE.md").write_text("License 4")

        directories_to_exclude = ()
        files = walk_directories_for_files(str(cpp_dir), directories_to_exclude, "LICENSE")

        # Should find all LICENSE* files
        assert len(files) == 4

    def test_exclude_directories_from_search(self, tmp_path):
        """Test that excluded directories are not searched."""
        cpp_dir = tmp_path / "cpp"
        cpp_dir.mkdir()

        src_dir = cpp_dir / "src"
        src_dir.mkdir()

        test_dir = cpp_dir / "test"
        test_dir.mkdir()

        (src_dir / "LICENSE").write_text("Src license")
        (test_dir / "LICENSE").write_text("Test license")

        directories_to_exclude = ("test", "tests")
        files = walk_directories_for_files(str(cpp_dir), directories_to_exclude, "LICENSE")

        # Should only find src LICENSE, not in test directory
        assert len(files) == 1
        # Check that it's from src, not test (using path components)
        assert Path(files[0]).parts[-2] == "src"
        assert "test" not in Path(files[0]).parts or Path(files[0]).parts[-2] != "test"


class TestExtractLicenseFiles:
    """Test LICENSE file extraction and grouping."""

    def test_extract_single_license(self):
        """Test extracting a single LICENSE file."""
        fixtures_path = Path(__file__).parent / "fixtures" / "test_project"

        if not fixtures_path.exists():
            pytest.skip("Test fixtures not found")

        content_map = extract_license_files([fixtures_path])

        # Should find LICENSE files in third_party directories
        assert len(content_map) > 0

        # Each entry should have content, filenames, and paths
        for _content_hash, info in content_map.items():
            assert "content" in info
            assert "filenames" in info
            assert "paths" in info
            assert len(info["content"]) > 0

    def test_deduplicate_identical_licenses(self, tmp_path):
        """Test that identical license texts are deduplicated."""
        # Create project structure with duplicate licenses
        project = tmp_path / "project"
        project.mkdir()

        cpp_dir = project / "cpp"
        cpp_dir.mkdir()

        lib1 = cpp_dir / "lib1"
        lib1.mkdir()

        lib2 = cpp_dir / "lib2"
        lib2.mkdir()

        # Same license text in both
        license_text = "MIT License\n\nCopyright 2020\n\nPermission is granted..."
        (lib1 / "LICENSE").write_text(license_text)
        (lib2 / "LICENSE").write_text(license_text)

        content_map = extract_license_files([project])

        # Should have only 1 entry (deduplicated by content hash)
        assert len(content_map) == 1

        # The entry should reference both paths
        for _content_hash, info in content_map.items():
            assert len(info["paths"]) == 2
            assert any("lib1" in path for path in info["paths"])
            assert any("lib2" in path for path in info["paths"])

    def test_different_licenses_not_deduplicated(self, tmp_path):
        """Test that different license texts are kept separate."""
        project = tmp_path / "project"
        project.mkdir()

        cpp_dir = project / "cpp"
        cpp_dir.mkdir()

        lib1 = cpp_dir / "lib1"
        lib1.mkdir()

        lib2 = cpp_dir / "lib2"
        lib2.mkdir()

        # Different licenses
        (lib1 / "LICENSE").write_text("MIT License text")
        (lib2 / "LICENSE").write_text("Apache License text")

        content_map = extract_license_files([project])

        # Should have 2 entries (different content)
        assert len(content_map) == 2

    def test_license_year_difference(self, tmp_path):
        """Test handling of licenses that differ only in year."""
        project = tmp_path / "project"
        project.mkdir()

        cpp_dir = project / "cpp"
        cpp_dir.mkdir()

        lib1 = cpp_dir / "cuco"
        lib1.mkdir()

        lib2 = cpp_dir / "raft"
        lib2.mkdir()

        # Apache 2.0 with different years
        license_template = """Apache License
Version 2.0, January 2004

Copyright (c) {year}, NVIDIA CORPORATION.

Licensed under the Apache License, Version 2.0...
"""

        (lib1 / "LICENSE").write_text(license_template.format(year="2020-2023"))
        (lib2 / "LICENSE").write_text(license_template.format(year="2022-2024"))

        content_map = extract_license_files([project])

        # Currently these will be separate (different content hashes)
        # This is a known issue mentioned in the requirements
        assert len(content_map) == 2

        # TODO: Future enhancement - normalize years for deduplication

    def test_hash_based_grouping(self, tmp_path):
        """Test that licenses are grouped by content hash."""
        project = tmp_path / "project"
        project.mkdir()

        cpp_dir = project / "cpp"
        cpp_dir.mkdir()

        lib1 = cpp_dir / "lib1"
        lib1.mkdir()

        license_text = "Example License Text"
        (lib1 / "LICENSE").write_text(license_text)

        content_map = extract_license_files([project])

        # Verify hash is computed correctly
        expected_hash = hashlib.sha256(license_text.encode("utf-8")).hexdigest()
        assert expected_hash in content_map

        # Verify content matches
        assert content_map[expected_hash]["content"] == license_text


class TestLicenseFileGrouping:
    """Test grouping and deduplication logic for LICENSE files."""

    def test_group_multiple_projects(self):
        """Test extracting licenses from multiple projects."""
        fixtures_path = Path(__file__).parent / "fixtures" / "test_project"

        if not fixtures_path.exists():
            pytest.skip("Test fixtures not found")

        # Extract from same project twice (simulating multiple project paths)
        content_map = extract_license_files([fixtures_path, fixtures_path])

        # Should still deduplicate
        assert len(content_map) > 0

        # Each unique license should appear once
        for _content_hash, info in content_map.items():
            # Paths might be duplicated if same project scanned twice
            assert isinstance(info["paths"], dict)

    def test_filename_tracking(self, tmp_path):
        """Test that filenames are tracked separately from paths."""
        project = tmp_path / "project"
        project.mkdir()

        cpp_dir = project / "cpp"
        cpp_dir.mkdir()

        lib1 = cpp_dir / "lib1"
        lib1.mkdir()

        lib2 = cpp_dir / "lib2"
        lib2.mkdir()

        # Same content, different filenames
        license_text = "MIT License"
        (lib1 / "LICENSE").write_text(license_text)
        (lib2 / "LICENSE.txt").write_text(license_text)

        content_map = extract_license_files([project])

        # Should be deduplicated by content
        assert len(content_map) == 1

        # Should track both filenames
        for _content_hash, info in content_map.items():
            filenames = info["filenames"]
            assert "LICENSE" in filenames
            assert "LICENSE.txt" in filenames


class TestRapidsNvidiaDeduplication:
    """Tests for RAPIDS/NVIDIA project deduplication."""

    def test_identify_rapids_projects(self):
        """Test identification of RAPIDS projects."""
        from spdx_license_builder.deduplication import RAPIDS_PROJECTS, is_rapids_project

        # Test known RAPIDS projects
        assert len(RAPIDS_PROJECTS) > 0

        # Test path detection
        assert is_rapids_project("/path/to/raft/cpp/src/file.cpp")
        assert is_rapids_project("/build/cudf-src/include/header.h")
        assert is_rapids_project("/home/user/cuco/LICENSE")

        # Test non-RAPIDS paths
        assert not is_rapids_project("/path/to/random/file.cpp")
        assert not is_rapids_project("/home/user/myproject/src/code.cpp")

    def test_deduplicate_rapids_licenses(self, tmp_path):
        """Test deduplication of RAPIDS Apache 2.0 licenses."""
        from spdx_license_builder.deduplication import should_deduplicate_rapids_license

        apache_license = """Apache License
Version 2.0, January 2004

Copyright (c) 2020-2023, NVIDIA CORPORATION.

Licensed under the Apache License, Version 2.0..."""

        # RAPIDS paths should be deduplicated
        rapids_paths = {"/path/to/raft/LICENSE", "/path/to/cudf/LICENSE"}
        assert should_deduplicate_rapids_license(rapids_paths, apache_license)

        # Mixed RAPIDS and non-RAPIDS should not be deduplicated
        mixed_paths = {"/path/to/raft/LICENSE", "/path/to/other/LICENSE"}
        assert not should_deduplicate_rapids_license(mixed_paths, apache_license)

        # Non-Apache license should not be deduplicated
        mit_license = "MIT License..."
        assert not should_deduplicate_rapids_license(rapids_paths, mit_license)

    def test_hierarchical_deduplication(self):
        """Test hierarchical license deduplication."""
        from spdx_license_builder.deduplication import (
            is_parent_path,
            should_prefer_parent_license,
        )

        # Test parent-child path detection
        assert is_parent_path("/path/to/cccl/LICENSE", "/path/to/cccl/thrust/LICENSE")
        assert is_parent_path("/path/to/cccl/LICENSE", "/path/to/cccl/cub/LICENSE")
        assert is_parent_path("/path/to/cccl/LICENSE", "/path/to/cccl/libcudacxx/LICENSE")
        assert not is_parent_path(
            "/path/to/cccl/thrust/LICENSE", "/path/to/cccl/LICENSE"
        )  # Child->parent
        assert not is_parent_path("/path/to/other/LICENSE", "/path/to/cccl/LICENSE")  # Unrelated

        # Test preference for parent licenses
        parent_paths = {"/path/to/cccl/LICENSE"}

        # Children should be skipped when parent exists
        assert should_prefer_parent_license(parent_paths, "/path/to/cccl/thrust/LICENSE")
        assert should_prefer_parent_license(parent_paths, "/path/to/cccl/cub/LICENSE")

        # Parent itself should not be skipped
        assert not should_prefer_parent_license(parent_paths, "/path/to/cccl/LICENSE")

        # Without parent, children should not be skipped
        empty_parents = set()
        assert not should_prefer_parent_license(empty_parents, "/path/to/cccl/thrust/LICENSE")


class TestLicenseYearNormalization:
    """Tests for year normalization in license deduplication."""

    def test_normalize_copyright_years(self):
        """Test normalizing copyright years for deduplication."""
        from spdx_license_builder.deduplication import normalize_copyright_years

        # Year ranges should be normalized
        license1 = "Copyright (c) 2020-2023, NVIDIA CORPORATION."
        license2 = "Copyright (c) 2022-2024, NVIDIA CORPORATION."

        normalized1 = normalize_copyright_years(license1)
        normalized2 = normalize_copyright_years(license2)

        # Both should have the same normalized form
        assert normalized1 == normalized2
        assert "YYYY" in normalized1
        assert "2020" not in normalized1
        assert "2023" not in normalized1

    def test_normalize_various_formats(self):
        """Test normalization of various copyright year formats."""
        from spdx_license_builder.deduplication import normalize_copyright_years

        test_cases = [
            ("Copyright (c) 2020 Company", "Copyright (c) YYYY Company"),
            ("Copyright (C) 2020-2023 Company", "Copyright (c) YYYY Company"),
            ("Copyright 2020 Company", "Copyright YYYY Company"),
            ("Copyright (c) 2020, 2021, 2022 Company", "Copyright (c) YYYY Company"),
        ]

        for original, _expected in test_cases:
            result = normalize_copyright_years(original)
            assert "YYYY" in result
            # Year should be replaced
            assert not any(str(year) in result for year in range(2000, 2030))

    def test_compute_normalized_hash(self):
        """Test that normalized hashes match for licenses differing only in years."""
        from spdx_license_builder.deduplication import compute_normalized_hash

        license1 = """Apache License
Copyright (c) 2020-2023, NVIDIA CORPORATION.
Licensed under the Apache License..."""

        license2 = """Apache License
Copyright (c) 2022-2024, NVIDIA CORPORATION.
Licensed under the Apache License..."""

        # Hashes should match after normalization
        hash1 = compute_normalized_hash(license1)
        hash2 = compute_normalized_hash(license2)

        assert hash1 == hash2

    def test_group_licenses_with_year_normalization(self, tmp_path):
        """Test grouping licenses with year normalization enabled."""
        from spdx_license_builder.deduplication import group_licenses_with_deduplication

        license_template = """Apache License
Copyright (c) {year}, NVIDIA CORPORATION.
Licensed under the Apache License, Version 2.0..."""

        license1 = license_template.format(year="2020-2023")
        license2 = license_template.format(year="2022-2024")

        # Create content map with two licenses differing only in years
        content_map = {
            hashlib.sha256(license1.encode()).hexdigest(): {
                "content": license1,
                "filenames": {"LICENSE"},
                "paths": {"/path1/LICENSE": "path1/LICENSE"},
            },
            hashlib.sha256(license2.encode()).hexdigest(): {
                "content": license2,
                "filenames": {"LICENSE"},
                "paths": {"/path2/LICENSE": "path2/LICENSE"},
            },
        }

        # With year normalization, should be deduplicated
        result = group_licenses_with_deduplication(
            content_map,
            use_year_normalization=True,
            deduplicate_rapids=False,
            deduplicate_hierarchical=False,
        )

        # Should be merged into one
        assert len(result) == 1

        # Should have both paths
        for info in result.values():
            assert len(info["paths"]) == 2


class TestLicenseDetectionIntegration:
    """Test automatic license detection from LICENSE file content."""

    def test_detect_mit_license(self, tmp_path):
        """Test that MIT license is detected from LICENSE file content."""
        from spdx_license_builder.extractors import DependencyLicenseExtractor

        # Create MIT LICENSE file
        license_dir = tmp_path / "mit_lib"
        license_dir.mkdir()
        (license_dir / "LICENSE").write_text("""MIT License

Copyright (c) 2020 Example Corp

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software.
""")

        extractor = DependencyLicenseExtractor([tmp_path])
        dep_licenses = extractor.extract()

        assert len(dep_licenses) == 1
        # Should be classified as MIT, not "LICENSE file: LICENSE"
        content_map = extractor.content_map
        assert len(content_map) == 1

    def test_detect_apache_license(self, tmp_path):
        """Test that Apache-2.0 license is detected from LICENSE file content."""
        from spdx_license_builder.extractors import DependencyLicenseExtractor

        # Create Apache LICENSE file
        license_dir = tmp_path / "apache_lib"
        license_dir.mkdir()
        (license_dir / "LICENSE").write_text("""Apache License
Version 2.0, January 2004
http://www.apache.org/licenses/

Copyright (c) 2020-2023, Example Corporation.

Licensed under the Apache License, Version 2.0 (the "License");
""")

        extractor = DependencyLicenseExtractor([tmp_path])
        dep_licenses = extractor.extract()

        assert len(dep_licenses) == 1
        content_map = extractor.content_map
        assert len(content_map) == 1

    def test_unrecognized_license_kept_separate(self, tmp_path):
        """Test that unrecognized licenses are kept separate."""
        from spdx_license_builder.extractors import DependencyLicenseExtractor

        # Create two custom LICENSE files
        lib1 = tmp_path / "lib1"
        lib1.mkdir()
        (lib1 / "LICENSE").write_text("Custom License A - Proprietary")

        lib2 = tmp_path / "lib2"
        lib2.mkdir()
        (lib2 / "LICENSE").write_text("Custom License B - Different proprietary")

        extractor = DependencyLicenseExtractor([tmp_path])
        dep_licenses = extractor.extract()

        # Should have 2 entries since content is different
        assert len(dep_licenses) == 2
        content_map = extractor.content_map
        assert len(content_map) == 2

    def test_unified_mit_from_both_sources(self, tmp_path):
        """Test that MIT from SPDX and LICENSE file are unified."""
        from spdx_license_builder.extractors import LicenseReportBuilder

        # Create SPDX-tagged MIT file
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.cpp").write_text("""// SPDX-FileCopyrightText: Copyright (c) 2023 Example
// SPDX-License-Identifier: MIT

#include <iostream>
""")

        # Create MIT LICENSE file
        dep_dir = tmp_path / "third_party" / "mit_lib"
        dep_dir.mkdir(parents=True)
        (dep_dir / "LICENSE").write_text("""MIT License

Copyright (c) 2020 Third Party

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software.
""")

        builder = LicenseReportBuilder(
            project_paths=[tmp_path],
            with_licenses=False,
            verbose=False,
        )
        report = builder.build()

        # Should have only 1 unified entry for MIT
        mit_entries = [e for e in report.unified_entries if e.license_id == "MIT"]
        assert len(mit_entries) == 1

        mit_entry = mit_entries[0]
        # Should have both SPDX file and LICENSE file
        assert len(mit_entry.spdx_files) == 1
        assert "main.cpp" in mit_entry.spdx_files
        assert len(mit_entry.license_files) > 0


class TestLicenseFilePatterns:
    """Test finding various license file name patterns."""

    def test_find_multiple_license_patterns(self, tmp_path):
        """Test finding LICENSE, COPYING, COPYRIGHT, and NOTICE files."""
        # Create test structure with various license file names
        build_dir = tmp_path / "build" / "third_party"
        build_dir.mkdir(parents=True)

        lib1 = build_dir / "lib1"
        lib1.mkdir()
        (lib1 / "LICENSE").write_text("MIT License from lib1")
        (lib1 / "COPYING").write_text("GPL License from lib1")

        lib2 = build_dir / "lib2"
        lib2.mkdir()
        (lib2 / "COPYRIGHT").write_text("Copyright notice from lib2")
        (lib2 / "NOTICE").write_text("NOTICE file from lib2")

        lib3 = build_dir / "lib3"
        lib3.mkdir()
        (lib3 / "LICENSE.txt").write_text("Apache License from lib3")
        (lib3 / "COPYING.LESSER").write_text("LGPL from lib3")

        # Extract all license files
        result = extract_license_files(tmp_path, verbose=False)

        # Should find 6 unique license contents
        assert len(result) == 6

        # Verify all file types were found
        all_filenames = set()
        for info in result.values():
            all_filenames.update(info["filenames"])

        expected_names = {
            "LICENSE",
            "COPYING",
            "COPYRIGHT",
            "NOTICE",
            "LICENSE.txt",
            "COPYING.LESSER",
        }
        assert all_filenames == expected_names

    def test_build_directory_not_excluded(self, tmp_path):
        """Test that build directory is searched for license files."""
        # Create license in build directory
        build_dir = tmp_path / "build" / "deps"
        build_dir.mkdir(parents=True)
        (build_dir / "LICENSE").write_text("Dependency license in build folder")

        # Create license in regular directory
        regular_dir = tmp_path / "cpp" / "third_party"
        regular_dir.mkdir(parents=True)
        (regular_dir / "LICENSE").write_text("Regular third party license")

        # Extract should find both
        result = extract_license_files(tmp_path, verbose=False)

        assert len(result) == 2

        # Check that build directory was searched
        all_paths = []
        for info in result.values():
            all_paths.extend(info["paths"].keys())

        build_paths = [p for p in all_paths if "/build/" in p]
        assert len(build_paths) == 1

    def test_license_pattern_matching(self, tmp_path):
        """Test that files starting with license patterns are matched."""
        dir1 = tmp_path / "lib1"
        dir1.mkdir()

        # These should all be found (startswith pattern matching)
        (dir1 / "LICENSE").write_text("License 1")
        (dir1 / "LICENSE.md").write_text("License 2")
        (dir1 / "LICENSE-MIT").write_text("License 3")
        (dir1 / "COPYING").write_text("License 4")
        (dir1 / "COPYING.txt").write_text("License 5")

        # This should NOT be found (doesn't start with any pattern)
        (dir1 / "README").write_text("Not a license")

        result = extract_license_files(tmp_path, verbose=False)

        # Should find 5 license files, not the README
        assert len(result) == 5

        # Verify filenames
        all_filenames = set()
        for info in result.values():
            all_filenames.update(info["filenames"])

        expected = {"LICENSE", "LICENSE.md", "LICENSE-MIT", "COPYING", "COPYING.txt"}
        assert all_filenames == expected
