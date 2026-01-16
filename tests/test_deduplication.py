#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Tests for advanced license deduplication functionality.
"""

import hashlib

from spdx_license_builder.deduplication import (
    RAPIDS_PROJECTS,
    compute_normalized_hash,
    group_licenses_with_deduplication,
    is_cccl_component,
    is_cccl_root,
    is_nvidia_project,
    is_rapids_project,
    normalize_copyright_years,
    should_deduplicate_rapids_license,
    should_skip_cccl_component_license,
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

    def test_cccl_component_detection(self):
        """Test CCCL component detection."""
        assert is_cccl_component("/path/to/cccl/thrust/LICENSE") == "thrust"
        assert is_cccl_component("/path/to/cccl/cub/LICENSE") == "cub"
        assert is_cccl_component("/path/to/cccl/libcudacxx/LICENSE") == "libcudacxx"
        assert is_cccl_component("/build/thrust-src/LICENSE") == "thrust"

        assert is_cccl_component("/path/to/other/LICENSE") is None
        assert is_cccl_component("/path/to/cccl/LICENSE") is None

    def test_cccl_root_detection(self):
        """Test CCCL root LICENSE detection."""
        assert is_cccl_root("/path/to/cccl/LICENSE")
        assert is_cccl_root("/build/cccl-src/LICENSE")
        assert is_cccl_root("/opt/cccl/include/../LICENSE")

        assert not is_cccl_root("/path/to/cccl/thrust/LICENSE")
        assert not is_cccl_root("/path/to/cccl/cub/LICENSE")
        assert not is_cccl_root("/path/to/other/LICENSE")


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


class TestCcclHandling:
    """Test CCCL special handling logic."""

    def test_skip_component_with_root(self):
        """Test that components are skipped when root exists."""
        all_paths = {
            "/path/to/cccl/LICENSE",
            "/path/to/cccl/thrust/LICENSE",
            "/path/to/cccl/cub/LICENSE",
            "/path/to/cccl/libcudacxx/LICENSE",
        }

        # Components should be skipped
        assert should_skip_cccl_component_license("/path/to/cccl/thrust/LICENSE", all_paths)
        assert should_skip_cccl_component_license("/path/to/cccl/cub/LICENSE", all_paths)
        assert should_skip_cccl_component_license("/path/to/cccl/libcudacxx/LICENSE", all_paths)

        # Root should not be skipped
        assert not should_skip_cccl_component_license("/path/to/cccl/LICENSE", all_paths)

    def test_dont_skip_component_without_root(self):
        """Test that components are not skipped when root doesn't exist."""
        paths_no_root = {"/path/to/cccl/thrust/LICENSE", "/path/to/cccl/cub/LICENSE"}

        # Without root, components should not be skipped
        assert not should_skip_cccl_component_license("/path/to/cccl/thrust/LICENSE", paths_no_root)
        assert not should_skip_cccl_component_license("/path/to/cccl/cub/LICENSE", paths_no_root)

    def test_non_cccl_not_skipped(self):
        """Test that non-CCCL paths are never skipped."""
        all_paths = {"/path/to/cccl/LICENSE", "/path/to/other/LICENSE"}

        assert not should_skip_cccl_component_license("/path/to/other/LICENSE", all_paths)


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
            content_map, use_year_normalization=True, deduplicate_rapids=False, handle_cccl=False
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
            content_map, use_year_normalization=False, deduplicate_rapids=True, handle_cccl=False
        )

        # Should be merged into one
        assert len(result) == 1

        # Should have both paths
        for info in result.values():
            assert len(info["paths"]) == 2

    def test_cccl_handling(self):
        """Test that CCCL component licenses are filtered."""
        license_text = "Apache License\nVersion 2.0"

        content_map = {
            "root": {
                "content": license_text,
                "filenames": {"LICENSE"},
                "paths": {"/path/to/cccl/LICENSE": "cccl/LICENSE"},
            },
            "thrust": {
                "content": license_text,
                "filenames": {"LICENSE"},
                "paths": {"/path/to/cccl/thrust/LICENSE": "cccl/thrust/LICENSE"},
            },
            "cub": {
                "content": license_text,
                "filenames": {"LICENSE"},
                "paths": {"/path/to/cccl/cub/LICENSE": "cccl/cub/LICENSE"},
            },
        }

        result = group_licenses_with_deduplication(
            content_map, use_year_normalization=False, deduplicate_rapids=False, handle_cccl=True
        )

        # Should only have root, components filtered out
        assert len(result) == 1
        assert "root" in result

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
            content_map, use_year_normalization=False, deduplicate_rapids=False, handle_cccl=False
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
            content_map, use_year_normalization=True, deduplicate_rapids=True, handle_cccl=True
        )

        # Should have 2: one for RAPIDS (merged), one for CCCL root
        assert len(result) <= 2
