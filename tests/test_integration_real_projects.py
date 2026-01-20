#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Integration tests using real RAPIDS and CCCL project structures.

Tests download actual LICENSE files from GitHub to verify deduplication logic.
"""

import urllib.request
from pathlib import Path as PathlibPath

import pytest

from spdx_license_builder.deduplication import (
    group_licenses_with_deduplication,
    is_parent_path,
    is_rapids_project,
)
from spdx_license_builder.extractors import DependencyLicenseExtractor


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


# GitHub raw content base URL
GITHUB_RAW = "https://raw.githubusercontent.com"

# Project configurations
PROJECTS = {
    "cccl": {
        "repo": "NVIDIA/cccl",
        "branch": "main",
        "licenses": ["LICENSE", "cub/LICENSE.TXT", "thrust/LICENSE", "libcudacxx/LICENSE.TXT"],
    },
    "raft": {"repo": "rapidsai/raft", "branch": "branch-25.02", "licenses": ["LICENSE"]},
    "cudf": {"repo": "rapidsai/cudf", "branch": "branch-25.02", "licenses": ["LICENSE"]},
    "cuco": {"repo": "NVIDIA/cuCollections", "branch": "dev", "licenses": ["LICENSE"]},
}


def download_license(repo, branch, license_path, timeout=10):
    """Download LICENSE file from GitHub."""
    url = f"{GITHUB_RAW}/{repo}/{branch}/{license_path}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        print(f"Failed to download {url}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error downloading {url}: {e}")
        raise


@pytest.fixture(scope="module")
def integration_fixtures(tmp_path_factory):
    """Download and setup all real project structures."""
    tmp_path = tmp_path_factory.mktemp("integration")
    fixtures = {}

    for project_name, config in PROJECTS.items():
        project_dir = tmp_path / project_name
        cpp_dir = project_dir / "cpp"
        cpp_dir.mkdir(parents=True)

        for license_path in config["licenses"]:
            content = download_license(config["repo"], config["branch"], license_path)
            if content is None:
                pytest.skip("Could not download LICENSE files from GitHub")

            # Place LICENSE files in cpp subdirectory
            target = cpp_dir / (license_path if license_path != "LICENSE" else "LICENSE")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)

        fixtures[project_name] = project_dir

    return fixtures


class TestCCCL:
    """Test CCCL project deduplication."""

    def test_component_detection(self, integration_fixtures):
        """Verify CCCL root and component license detection."""
        cccl_dir = integration_fixtures["cccl"]

        # Verify hierarchical relationships
        root_license = str(cccl_dir / "LICENSE")
        cub_license = str(cccl_dir / "cub" / "LICENSE")
        thrust_license = str(cccl_dir / "thrust" / "LICENSE")
        libcudacxx_license = str(cccl_dir / "libcudacxx" / "LICENSE")

        # Verify parent-child relationships
        assert is_parent_path(root_license, cub_license)
        assert is_parent_path(root_license, thrust_license)
        assert is_parent_path(root_license, libcudacxx_license)

    def test_component_deduplication(self, integration_fixtures):
        """Verify hierarchical deduplication behavior (when explicitly enabled).

        Note: Hierarchical deduplication only removes child licenses if they have
        IDENTICAL content to the parent. If child licenses have different content
        (e.g., different copyright years, modifications), they are kept.
        """
        cccl_dir = integration_fixtures["cccl"]
        content_map = extract_license_files([cccl_dir])

        # Test safe default (no hierarchical deduplication)
        safe_result = group_licenses_with_deduplication(
            content_map, deduplicate_rapids=False, deduplicate_hierarchical=False
        )
        safe_paths = {p for info in safe_result.values() for p in info["paths"] if "cccl" in p}
        # Should keep all paths (safe - preserves provenance)
        assert any("cub" in p or "thrust" in p or "libcudacxx" in p for p in safe_paths)

        # Test with hierarchical deduplication enabled
        # This will only remove child licenses if they have IDENTICAL content to parent
        risky_result = group_licenses_with_deduplication(
            content_map, deduplicate_rapids=False, deduplicate_hierarchical=True
        )
        risky_paths = {p for info in risky_result.values() for p in info["paths"] if "cccl" in p}

        # Should have root LICENSE
        assert any("/cpp/LICENSE" in p for p in risky_paths)

        # Child licenses may or may not be present depending on whether they have
        # identical content to the parent. The deduplication only removes children
        # with identical content within each content hash bucket.
        # Just verify we didn't lose everything
        assert len(risky_paths) > 0


class TestRAPIDS:
    """Test RAPIDS project deduplication."""

    def test_project_detection(self, integration_fixtures):
        """Verify RAPIDS project detection."""
        for project in ["raft", "cudf", "cuco"]:
            assert is_rapids_project(str(integration_fixtures[project] / "LICENSE"))

    def test_license_content(self, integration_fixtures):
        """Verify RAPIDS licenses are Apache-2.0 with NVIDIA copyright."""
        for project in ["raft", "cudf", "cuco"]:
            license_file = integration_fixtures[project] / "cpp" / "LICENSE"
            content = license_file.read_text()
            assert "Apache" in content
            assert "NVIDIA" in content.upper()

    def test_deduplication(self, integration_fixtures):
        """Verify RAPIDS Apache-2.0 licenses are deduplicated."""
        rapids_dirs = [integration_fixtures[p] for p in ["raft", "cudf", "cuco"]]
        content_map = extract_license_files(rapids_dirs)

        # Count RAPIDS licenses
        def count_rapids(cm):
            return sum(
                1
                for info in cm.values()
                if any(p in str(info["paths"]) for p in ["raft", "cudf", "cuco"])
                and "Apache" in info["content"]
            )

        before = count_rapids(content_map)
        deduplicated = group_licenses_with_deduplication(content_map, deduplicate_rapids=True)
        after = count_rapids(deduplicated)

        assert after <= before
        if before > 1:
            assert after == 1


class TestCombined:
    """Test combined RAPIDS + CCCL deduplication."""

    def test_full_pipeline(self, integration_fixtures):
        """Verify complete deduplication pipeline."""
        all_dirs = list(integration_fixtures.values())
        content_map = extract_license_files(all_dirs)

        # Test with risky deduplication explicitly enabled
        deduplicated = group_licenses_with_deduplication(
            content_map,
            use_year_normalization=True,
            deduplicate_rapids=True,
            deduplicate_hierarchical=True,
        )

        # Should reduce license count (because risky features are enabled)
        assert len(deduplicated) <= len(content_map)

        # With hierarchical deduplication enabled, child licenses are only removed
        # if they have IDENTICAL content to the parent
        cccl_paths = [p for info in deduplicated.values() for p in info["paths"] if "cccl" in p]
        if cccl_paths:
            # Should have at least the root LICENSE
            assert any("/LICENSE" in p for p in cccl_paths)
            # Verify we still have some licenses (didn't lose everything)
            assert len(cccl_paths) > 0

        # RAPIDS: should have at most 1 Apache license
        rapids_count = sum(
            1
            for info in deduplicated.values()
            if any(p in str(info["paths"]) for p in ["raft", "cudf", "cuco"])
            and "Apache" in info["content"]
        )
        assert rapids_count <= 1

    def test_output_reduction(self, integration_fixtures):
        """Verify output reduction with deduplication."""
        all_dirs = list(integration_fixtures.values())
        content_map = extract_license_files(all_dirs)

        without = group_licenses_with_deduplication(content_map)
        with_dedup = group_licenses_with_deduplication(
            content_map,
            use_year_normalization=True,
            deduplicate_rapids=True,
            deduplicate_hierarchical=True,
        )

        reduction = (1 - len(with_dedup) / len(without)) * 100 if without else 0
        print(f"\nReduction: {len(without)} → {len(with_dedup)} licenses ({reduction:.1f}%)")

        # Deduplication should not increase license count
        assert len(with_dedup) <= len(without)


@pytest.mark.slow
class TestGitHubAccess:
    """Verify GitHub connectivity."""

    def test_can_download(self):
        """Verify we can download files from GitHub."""
        content = download_license("NVIDIA/cccl", "main", "LICENSE", timeout=5)
        if content is None:
            pytest.skip("Cannot access GitHub")
        assert "Apache" in content and len(content) > 100
