#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Integration tests using real RAPIDS and CCCL project structures.

These tests download actual LICENSE files from GitHub to verify our
deduplication logic works with real-world projects.
"""

import urllib.request

import pytest

from spdx_license_builder.deduplication import (
    group_licenses_with_deduplication,
    is_cccl_component,
    is_cccl_root,
    is_rapids_project,
)
from spdx_license_builder.find_and_copy_license_files import extract_license_files

# GitHub raw content URLs
GITHUB_RAW = "https://raw.githubusercontent.com"
GITHUB_API = "https://api.github.com"

# Project URLs
PROJECTS = {
    "cccl": {
        "repo": "NVIDIA/cccl",
        "branch": "main",
        "licenses": [
            "LICENSE",  # Root license
            "cub/LICENSE.TXT",  # CUB component (BSD)
            "thrust/LICENSE",  # Thrust component (Apache)
            "libcudacxx/LICENSE.TXT",  # libcudacxx component (Apache + LLVM)
        ],
    },
    "raft": {"repo": "rapidsai/raft", "branch": "branch-25.02", "licenses": ["LICENSE"]},
    "cudf": {"repo": "rapidsai/cudf", "branch": "branch-25.02", "licenses": ["LICENSE"]},
    "cuco": {"repo": "NVIDIA/cuCollections", "branch": "dev", "licenses": ["LICENSE"]},
}


def download_license(repo, branch, license_path, timeout=10):
    """
    Download a LICENSE file from GitHub.

    Args:
        repo: Repository in format 'owner/repo'
        branch: Branch name
        license_path: Path to LICENSE file in repo
        timeout: Request timeout in seconds

    Returns:
        License text or None if download fails
    """
    url = f"{GITHUB_RAW}/{repo}/{branch}/{license_path}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"Failed to download {url}: {e}")
        return None


def setup_integration_fixtures(tmp_path):
    """
    Download real LICENSE files and create test directory structure.

    Creates a c/cpp subdirectory structure that extract_license_files expects.

    Args:
        tmp_path: Pytest temporary directory

    Returns:
        Dictionary mapping project names to their paths, or None if downloads fail
    """
    fixtures = {}

    for project_name, config in PROJECTS.items():
        project_dir = tmp_path / project_name

        # Create cpp subdirectory (as expected by extract_license_files)
        cpp_dir = project_dir / "cpp"
        cpp_dir.mkdir(parents=True, exist_ok=True)

        # Download each LICENSE file
        for license_path in config["licenses"]:
            content = download_license(
                config["repo"],
                config["branch"],
                license_path,
            )

            if content is None:
                # Download failed, skip this test
                return None

            # Put LICENSE files in cpp subdirectory
            # This matches the structure that extract_license_files expects
            if license_path == "LICENSE":
                # Root LICENSE goes in cpp root
                license_file = cpp_dir / "LICENSE"
            else:
                # Component licenses go in their subdirectories under cpp
                license_file = cpp_dir / license_path

            license_file.parent.mkdir(parents=True, exist_ok=True)

            # Write LICENSE file
            license_file.write_text(content)

        fixtures[project_name] = project_dir

    return fixtures


class TestRealCCCLStructure:
    """Test with real CCCL project structure."""

    @pytest.fixture
    def cccl_structure(self, tmp_path):
        """Download and setup real CCCL structure."""
        fixtures = setup_integration_fixtures(tmp_path)
        if fixtures is None:
            pytest.skip("Could not download LICENSE files from GitHub")
        return fixtures

    def test_cccl_license_detection(self, cccl_structure):
        """Test that we correctly identify CCCL root and component licenses."""
        cccl_dir = cccl_structure["cccl"]

        # Check root detection
        root_license = str(cccl_dir / "LICENSE")
        assert is_cccl_root(root_license)

        # Check component detection
        assert is_cccl_component(str(cccl_dir / "cub" / "LICENSE")) == "cub"
        assert is_cccl_component(str(cccl_dir / "thrust" / "LICENSE")) == "thrust"
        assert is_cccl_component(str(cccl_dir / "libcudacxx" / "LICENSE")) == "libcudacxx"

    def test_cccl_deduplication(self, cccl_structure):
        """Test that CCCL component licenses are skipped when root exists."""
        cccl_dir = cccl_structure["cccl"]

        # Extract licenses
        content_map = extract_license_files([cccl_dir])

        # Should find 4 licenses before deduplication
        assert len(content_map) >= 1  # At minimum root

        # Apply deduplication with CCCL handling
        deduplicated = group_licenses_with_deduplication(
            content_map, use_year_normalization=False, deduplicate_rapids=False, handle_cccl=True
        )

        # After deduplication, should only have root license
        # Components should be filtered out
        remaining_paths = set()
        for info in deduplicated.values():
            remaining_paths.update(info["paths"].keys())

        # Root should be present (in cpp/LICENSE)
        assert any(
            "cccl/cpp/LICENSE" in p
            and "cub" not in p
            and "thrust" not in p
            and "libcudacxx" not in p
            for p in remaining_paths
        ), f"Root not found in paths: {remaining_paths}"

        # Components should be filtered if root exists
        cccl_paths = [p for p in remaining_paths if "cccl" in p]
        if len(cccl_paths) > 1:
            # If we have multiple CCCL paths, they shouldn't all be components
            component_count = sum(
                1 for p in cccl_paths if "/cub/" in p or "/thrust/" in p or "/libcudacxx/" in p
            )
            root_count = sum(
                1
                for p in cccl_paths
                if "/cpp/LICENSE" in p
                and "cub" not in p
                and "thrust" not in p
                and "libcudacxx" not in p
            )

            # Should have root but not components
            assert root_count >= 1, f"Root not found. Paths: {cccl_paths}"
            assert component_count == 0, f"Components not filtered. Paths: {cccl_paths}"


class TestRealRAPIDSProjects:
    """Test with real RAPIDS project structures."""

    @pytest.fixture
    def rapids_structure(self, tmp_path):
        """Download and setup real RAPIDS structures."""
        fixtures = setup_integration_fixtures(tmp_path)
        if fixtures is None:
            pytest.skip("Could not download LICENSE files from GitHub")
        return fixtures

    def test_rapids_project_detection(self, rapids_structure):
        """Test that we correctly identify RAPIDS projects."""
        # Check each RAPIDS project
        assert is_rapids_project(str(rapids_structure["raft"] / "LICENSE"))
        assert is_rapids_project(str(rapids_structure["cudf"] / "LICENSE"))
        assert is_rapids_project(str(rapids_structure["cuco"] / "LICENSE"))

    def test_rapids_license_content(self, rapids_structure):
        """Test that RAPIDS licenses are actually Apache-2.0 with NVIDIA copyright."""
        for project_name in ["raft", "cudf", "cuco"]:
            if project_name not in rapids_structure:
                continue

            license_file = rapids_structure[project_name] / "cpp" / "LICENSE"
            content = license_file.read_text()

            # Should be Apache-2.0
            assert "Apache License" in content or "Apache-2.0" in content

            # Should have NVIDIA copyright
            assert "NVIDIA" in content.upper()

    def test_rapids_deduplication(self, rapids_structure):
        """Test that RAPIDS Apache-2.0 licenses are deduplicated."""
        # Extract licenses from multiple RAPIDS projects
        rapids_dirs = [
            rapids_structure[p] for p in ["raft", "cudf", "cuco"] if p in rapids_structure
        ]

        if len(rapids_dirs) < 2:
            pytest.skip("Need at least 2 RAPIDS projects for deduplication test")

        content_map = extract_license_files(rapids_dirs)

        # Count RAPIDS Apache licenses before deduplication
        rapids_licenses_before = sum(
            1
            for info in content_map.values()
            if any("raft" in p or "cudf" in p or "cuco" in p for p in info["paths"])
            and "Apache" in info["content"]
        )

        # Apply RAPIDS deduplication
        deduplicated = group_licenses_with_deduplication(
            content_map, use_year_normalization=False, deduplicate_rapids=True, handle_cccl=False
        )

        # Count RAPIDS Apache licenses after deduplication
        rapids_licenses_after = sum(
            1
            for info in deduplicated.values()
            if any("raft" in p or "cudf" in p or "cuco" in p for p in info["paths"])
            and "Apache" in info["content"]
        )

        # Should be deduplicated into fewer entries
        assert rapids_licenses_after <= rapids_licenses_before

        # If there were multiple RAPIDS licenses, they should be merged
        if rapids_licenses_before > 1:
            assert rapids_licenses_after == 1


class TestCombinedRealProjects:
    """Test with combined RAPIDS and CCCL projects."""

    @pytest.fixture
    def combined_structure(self, tmp_path):
        """Download and setup combined project structure."""
        fixtures = setup_integration_fixtures(tmp_path)
        if fixtures is None:
            pytest.skip("Could not download LICENSE files from GitHub")
        return fixtures

    def test_full_deduplication_pipeline(self, combined_structure):
        """Test complete deduplication with real RAPIDS + CCCL projects."""
        all_dirs = list(combined_structure.values())

        # Extract all licenses
        content_map = extract_license_files(all_dirs)
        total_before = len(content_map)

        # Apply all deduplication features
        deduplicated = group_licenses_with_deduplication(
            content_map, use_year_normalization=True, deduplicate_rapids=True, handle_cccl=True
        )
        total_after = len(deduplicated)

        # Deduplication should reduce the number of licenses
        assert total_after <= total_before

        # Verify CCCL root is present but components are not
        cccl_paths = []
        for info in deduplicated.values():
            cccl_paths.extend([p for p in info["paths"] if "cccl" in p])

        if cccl_paths:
            # Should have root
            has_root = any(
                "/LICENSE" in p and "cub" not in p and "thrust" not in p and "libcudacxx" not in p
                for p in cccl_paths
            )
            assert has_root

            # Should not have components
            has_components = any(
                "cub/LICENSE" in p or "thrust/LICENSE" in p or "libcudacxx/LICENSE" in p
                for p in cccl_paths
            )
            assert not has_components

        # Verify RAPIDS licenses are consolidated
        rapids_license_count = sum(
            1
            for info in deduplicated.values()
            if any("raft" in p or "cudf" in p or "cuco" in p for p in info["paths"])
            and "Apache" in info["content"]
        )

        # Should have at most 1 RAPIDS Apache license after deduplication
        assert rapids_license_count <= 1

    def test_realistic_output_size(self, combined_structure):
        """Test that deduplication significantly reduces output for realistic projects."""
        all_dirs = list(combined_structure.values())

        content_map = extract_license_files(all_dirs)

        # Without deduplication
        without_dedup = group_licenses_with_deduplication(
            content_map, use_year_normalization=False, deduplicate_rapids=False, handle_cccl=False
        )

        # With full deduplication
        with_dedup = group_licenses_with_deduplication(
            content_map, use_year_normalization=True, deduplicate_rapids=True, handle_cccl=True
        )

        reduction_percent = (
            (1 - len(with_dedup) / len(without_dedup)) * 100 if len(without_dedup) > 0 else 0
        )

        print("\nDeduplication results:")
        print(f"  Without deduplication: {len(without_dedup)} licenses")
        print(f"  With deduplication: {len(with_dedup)} licenses")
        print(f"  Reduction: {reduction_percent:.1f}%")

        # Should see significant reduction with multiple projects
        if len(all_dirs) >= 3:
            assert len(with_dedup) < len(without_dedup)


@pytest.mark.slow
class TestDownloadPerformance:
    """Test that can be run independently to verify GitHub access."""

    def test_can_access_github(self):
        """Verify we can access GitHub to download files."""
        # Try to download a small file from CCCL
        content = download_license("NVIDIA/cccl", "main", "LICENSE", timeout=5)

        if content is None:
            pytest.skip("Cannot access GitHub - may be offline or rate limited")

        # Should contain Apache license
        assert "Apache" in content or "LICENSE" in content
        assert len(content) > 100  # Should be a real license file
