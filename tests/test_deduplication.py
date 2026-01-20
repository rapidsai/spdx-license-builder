#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Tests for advanced license deduplication functionality.
"""

import hashlib

from spdx_license_builder.deduplication import (
    RAPIDS_PROJECTS,
    compute_normalized_hash,
    get_directory_depth,
    group_licenses_with_deduplication,
    is_nvidia_project,
    is_parent_path,
    is_rapids_project,
    normalize_copyright_years,
    should_deduplicate_rapids_license,
    should_prefer_parent_license,
)


class TestProjectDetection:
    """Test project type detection functions."""

    def test_rapids_projects_list(self):
        """Test that RAPIDS projects list is defined."""
        assert len(RAPIDS_PROJECTS) > 0
        assert "raft" in RAPIDS_PROJECTS
        assert "cudf" in RAPIDS_PROJECTS
        assert "cuco" in RAPIDS_PROJECTS

    def test_is_rapids_project(self):
        """Test RAPIDS project detection."""
        # Positive cases
        assert is_rapids_project("/path/to/raft/cpp/src/file.cpp")
        assert is_rapids_project("/build/cudf-src/include/header.h")
        assert is_rapids_project("/home/user/cuco/LICENSE")
        assert is_rapids_project("/opt/cuml-src/python/setup.py")

        # Negative cases
        assert not is_rapids_project("/path/to/myproject/src/file.cpp")
        assert not is_rapids_project("/home/user/random/LICENSE")
        assert not is_rapids_project("/opt/other-src/code.cpp")

    def test_is_nvidia_project(self):
        """Test NVIDIA project detection."""
        assert is_nvidia_project("/path/to/cccl/LICENSE")
        assert is_nvidia_project("/build/cutlass-src/include/header.h")
        assert is_nvidia_project("/path/to/raft/LICENSE")

        assert not is_nvidia_project("/path/to/other/LICENSE")

    def test_directory_depth(self):
        """Test directory depth calculation."""
        # Parent directory parts count (includes root "/")
        assert get_directory_depth("/path/to/file.txt") == 3  # "/", "path", "to"
        assert get_directory_depth("/root/file.txt") == 2  # "/", "root"
        assert get_directory_depth("/file.txt") == 1  # "/"
        assert get_directory_depth("/a/b/c/d/file.txt") == 5  # "/", "a", "b", "c", "d"

    def test_parent_path_detection(self):
        """Test hierarchical path relationship detection."""
        # True parent relationships
        assert is_parent_path("/path/to/cccl/LICENSE", "/path/to/cccl/thrust/LICENSE")
        assert is_parent_path("/path/to/cccl/LICENSE", "/path/to/cccl/cub/lib/LICENSE")

        # Not parent relationships
        assert not is_parent_path("/path/to/cccl/LICENSE", "/path/to/cccl/LICENSE")  # Same path
        assert not is_parent_path(
            "/path/to/cccl/LICENSE", "/path/to/other/LICENSE"
        )  # Different branch
        assert not is_parent_path(
            "/path/to/cccl/thrust/LICENSE", "/path/to/cccl/LICENSE"
        )  # Child->parent


class TestRapidsDeduplication:
    """Test RAPIDS license deduplication logic."""

    def test_should_deduplicate_rapids_apache(self):
        """Test that RAPIDS Apache-2.0 licenses are marked for deduplication."""
        apache_license = """Apache License
Version 2.0, January 2004
http://www.apache.org/licenses/

Copyright (c) 2020-2023, NVIDIA CORPORATION."""

        rapids_paths = {"/path/to/raft/LICENSE", "/path/to/cudf/LICENSE", "/path/to/cuco/LICENSE"}

        assert should_deduplicate_rapids_license(rapids_paths, apache_license)

    def test_should_not_deduplicate_mixed_paths(self):
        """Test that mixed RAPIDS/non-RAPIDS paths are not deduplicated."""
        apache_license = "Apache License\nVersion 2.0"

        mixed_paths = {"/path/to/raft/LICENSE", "/path/to/other/LICENSE"}

        assert not should_deduplicate_rapids_license(mixed_paths, apache_license)

    def test_should_not_deduplicate_non_apache(self):
        """Test that non-Apache licenses are not deduplicated."""
        mit_license = "MIT License\n\nPermission is hereby granted..."

        rapids_paths = {"/path/to/raft/LICENSE", "/path/to/cudf/LICENSE"}

        assert not should_deduplicate_rapids_license(rapids_paths, mit_license)


class TestHierarchicalDeduplication:
    """Test hierarchical license deduplication (prefer parent over child)."""

    def test_prefer_parent_with_root(self):
        """Test that child licenses are skipped when parent exists."""
        parent_paths = {"/path/to/cccl/LICENSE"}

        # Children should be skipped in favor of parent
        assert should_prefer_parent_license(parent_paths, "/path/to/cccl/thrust/LICENSE")
        assert should_prefer_parent_license(parent_paths, "/path/to/cccl/cub/LICENSE")
        assert should_prefer_parent_license(parent_paths, "/path/to/cccl/libcudacxx/LICENSE")

        # Parent itself should not be skipped
        assert not should_prefer_parent_license(parent_paths, "/path/to/cccl/LICENSE")

    def test_no_preference_without_parent(self):
        """Test that child licenses are not skipped when no parent exists."""
        parent_paths = set()  # No parents

        # Without parent, nothing should be skipped
        assert not should_prefer_parent_license(parent_paths, "/path/to/cccl/thrust/LICENSE")
        assert not should_prefer_parent_license(parent_paths, "/path/to/cccl/cub/LICENSE")

    def test_unrelated_paths_not_affected(self):
        """Test that unrelated paths are not affected by hierarchical deduplication."""
        parent_paths = {"/path/to/cccl/LICENSE"}

        # Unrelated paths should not be affected
        assert not should_prefer_parent_license(parent_paths, "/path/to/other/LICENSE")
        assert not should_prefer_parent_license(parent_paths, "/different/path/LICENSE")


class TestYearNormalization:
    """Test copyright year normalization."""

    def test_normalize_year_range(self):
        """Test normalization of year ranges."""
        text = "Copyright (c) 2020-2023, NVIDIA CORPORATION."
        normalized = normalize_copyright_years(text)

        assert "YYYY" in normalized
        assert "2020" not in normalized
        assert "2023" not in normalized

    def test_normalize_multiple_years(self):
        """Test normalization of multiple years."""
        text = "Copyright (c) 2020, 2021, 2022 Company"
        normalized = normalize_copyright_years(text)

        assert "YYYY" in normalized
        assert "2020" not in normalized

    def test_normalize_various_formats(self):
        """Test normalization of various copyright formats."""
        test_cases = [
            "Copyright (c) 2020 Company",
            "Copyright (C) 2020-2023 Company",
            "Copyright 2020 Company",
            "Copyright (2020) Company",
        ]

        for text in test_cases:
            normalized = normalize_copyright_years(text)
            assert "YYYY" in normalized
            assert not any(str(year) in normalized for year in range(2000, 2030))

    def test_compute_normalized_hash_same(self):
        """Test that licenses differing only in years have same hash."""
        license1 = "Copyright (c) 2020-2023, NVIDIA CORPORATION.\nApache License"
        license2 = "Copyright (c) 2022-2024, NVIDIA CORPORATION.\nApache License"

        hash1 = compute_normalized_hash(license1)
        hash2 = compute_normalized_hash(license2)

        assert hash1 == hash2

    def test_compute_normalized_hash_different(self):
        """Test that different licenses have different hashes."""
        license1 = "Copyright (c) 2020, Company A.\nMIT License"
        license2 = "Copyright (c) 2020, Company B.\nApache License"

        hash1 = compute_normalized_hash(license1)
        hash2 = compute_normalized_hash(license2)

        assert hash1 != hash2


class TestGroupLicensesWithDeduplication:
    """Test the main deduplication grouping function."""

    def test_year_normalization_deduplication(self):
        """Test that year normalization groups similar licenses."""
        license1 = "Apache License\nCopyright (c) 2020-2023, NVIDIA."
        license2 = "Apache License\nCopyright (c) 2022-2024, NVIDIA."

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

    def test_rapids_deduplication(self):
        """Test that RAPIDS Apache licenses are deduplicated."""
        apache_license = "Apache License\nVersion 2.0"

        content_map = {
            "hash1": {
                "content": apache_license,
                "filenames": {"LICENSE"},
                "paths": {"/path/to/raft/LICENSE": "raft/LICENSE"},
            },
            "hash2": {
                "content": apache_license,
                "filenames": {"LICENSE"},
                "paths": {"/path/to/cudf/LICENSE": "cudf/LICENSE"},
            },
        }

        result = group_licenses_with_deduplication(
            content_map,
            use_year_normalization=False,
            deduplicate_rapids=True,
            deduplicate_hierarchical=False,
        )

        # Should be merged into one
        assert len(result) == 1

        # Should have both paths
        for info in result.values():
            assert len(info["paths"]) == 2

    def test_hierarchical_handling(self):
        """Test hierarchical license deduplication."""
        license_text = "Apache License\nVersion 2.0"
        # In reality, identical content would have the same hash
        content_hash = "samehash"

        content_map = {
            content_hash: {
                "content": license_text,
                "filenames": {"LICENSE"},
                "paths": {
                    "/path/to/cccl/LICENSE": "cccl/LICENSE",
                    "/path/to/cccl/thrust/LICENSE": "cccl/thrust/LICENSE",
                    "/path/to/cccl/cub/LICENSE": "cccl/cub/LICENSE",
                },
            },
        }

        # Safe default: keeps all paths
        safe_result = group_licenses_with_deduplication(
            content_map,
            use_year_normalization=False,
            deduplicate_rapids=False,
            deduplicate_hierarchical=False,
        )
        assert len(safe_result) == 1
        assert len(safe_result[content_hash]["paths"]) == 3

        # Risky opt-in: filters child paths
        risky_result = group_licenses_with_deduplication(
            content_map,
            use_year_normalization=False,
            deduplicate_rapids=False,
            deduplicate_hierarchical=True,
        )
        assert len(risky_result) == 1
        # Should only keep parent, not children
        assert "/path/to/cccl/LICENSE" in risky_result[content_hash]["paths"]
        assert "/path/to/cccl/thrust/LICENSE" not in risky_result[content_hash]["paths"]

    def test_no_deduplication(self):
        """Test that no deduplication preserves all licenses."""
        license1 = "License 1"
        license2 = "License 2"

        content_map = {
            "hash1": {
                "content": license1,
                "filenames": {"LICENSE"},
                "paths": {"/path1/LICENSE": "path1/LICENSE"},
            },
            "hash2": {
                "content": license2,
                "filenames": {"LICENSE"},
                "paths": {"/path2/LICENSE": "path2/LICENSE"},
            },
        }

        result = group_licenses_with_deduplication(
            content_map,
            use_year_normalization=False,
            deduplicate_rapids=False,
            deduplicate_hierarchical=False,
        )

        # Should preserve both
        assert len(result) == 2

    def test_combined_deduplication(self):
        """Test that all deduplication methods work together."""
        apache_license = "Apache License\nCopyright (c) 2020-2023, NVIDIA."

        content_map = {
            "hash1": {
                "content": apache_license.replace("2020-2023", "2022-2024"),
                "filenames": {"LICENSE"},
                "paths": {"/path/to/raft/LICENSE": "raft/LICENSE"},
            },
            "hash2": {
                "content": apache_license,
                "filenames": {"LICENSE"},
                "paths": {"/path/to/cudf/LICENSE": "cudf/LICENSE"},
            },
            "cccl_comp": {
                "content": apache_license,
                "filenames": {"LICENSE"},
                "paths": {"/path/to/cccl/thrust/LICENSE": "cccl/thrust/LICENSE"},
            },
            "cccl_root": {
                "content": apache_license,
                "filenames": {"LICENSE"},
                "paths": {"/path/to/cccl/LICENSE": "cccl/LICENSE"},
            },
        }

        result = group_licenses_with_deduplication(
            content_map,
            use_year_normalization=True,
            deduplicate_rapids=True,
            deduplicate_hierarchical=True,
        )

        # Should have 2: one for RAPIDS (merged), one for CCCL root
        assert len(result) <= 2
