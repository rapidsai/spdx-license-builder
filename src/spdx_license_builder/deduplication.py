#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
License deduplication utilities.

Provides advanced deduplication logic for:
- RAPIDS/NVIDIA project detection
- CCCL special handling
- Copyright year normalization
"""

import hashlib
import re
from pathlib import Path
from typing import Any, Dict, Set

# Known RAPIDS projects (all use Apache-2.0)
RAPIDS_PROJECTS = {
    "cudf",
    "cuml",
    "cugraph",
    "cuspatial",
    "cuxfilter",
    "cucim",
    "raft",
    "cuco",
    "cupy",
    "rmm",
    "kvikio",
    "ucx-py",
}

# Known NVIDIA projects that use Apache-2.0
NVIDIA_PROJECTS = {
    "cccl",
    "cutlass",
    "thrust",
    "cub",
    "libcudacxx",
    "cudf",
    "cuml",
    "cugraph",
    "cuspatial",
    "cuxfilter",
    "cucim",
    "raft",
    "cuco",
}


def is_rapids_project(path: str) -> bool:
    """
    Check if a path belongs to a RAPIDS project.

    Args:
        path: File path to check

    Returns:
        True if the path contains a RAPIDS project name
    """
    path_parts = Path(path).parts

    # Check each part of the path
    for part in path_parts:
        part_lower = part.lower()
        # Remove common suffixes
        part_clean = part_lower.replace("-src", "").replace("_src", "")

        if part_clean in RAPIDS_PROJECTS:
            return True

    return False


def is_nvidia_project(path: str) -> bool:
    """
    Check if a path belongs to an NVIDIA project.

    Args:
        path: File path to check

    Returns:
        True if the path contains an NVIDIA project name
    """
    path_parts = Path(path).parts

    for part in path_parts:
        part_lower = part.lower()
        part_clean = part_lower.replace("-src", "").replace("_src", "")

        if part_clean in NVIDIA_PROJECTS:
            return True

    return False


def is_parent_path(parent: str, child: str) -> bool:
    """
    Check if one path's directory is a parent of another path's directory.

    For LICENSE files, this checks if the parent LICENSE is in a parent directory
    of the child LICENSE file.

    Args:
        parent: Potential parent path (typically a LICENSE file)
        child: Potential child path (typically a LICENSE file)

    Returns:
        True if parent's directory is an ancestor of child's directory
    """
    try:
        # Get parent directories (not the files themselves)
        parent_dir = Path(parent).parent.resolve()
        child_dir = Path(child).parent.resolve()

        # Try to get relative path from parent dir to child dir
        # If it succeeds and doesn't start with "..", then parent is ancestor
        try:
            rel_path = child_dir.relative_to(parent_dir)
            # Make sure they're not the same directory
            return str(rel_path) != "."
        except ValueError:
            return False
    except (ValueError, OSError):
        return False


def get_directory_depth(path: str) -> int:
    """
    Get the directory depth of a path.

    Args:
        path: File path

    Returns:
        Number of directory levels
    """
    return len(Path(path).parent.parts)


def should_prefer_parent_license(parent_paths: Set[str], child_path: str) -> bool:
    """
    Determine if a child license should be skipped in favor of a parent license.

    When multiple LICENSE files exist in a hierarchy with the same content,
    prefer the one at the higher level (closer to root). This handles cases like:
    - CCCL root license vs component licenses (thrust, cub, libcudacxx)
    - Any project with both root and subdirectory licenses

    Args:
        parent_paths: Set of paths that might be parents
        child_path: Path to check if it's a child

    Returns:
        True if child_path should be skipped in favor of a parent
    """
    return any(is_parent_path(parent_path, child_path) for parent_path in parent_paths)


def normalize_copyright_years(text: str) -> str:
    """
    Normalize copyright year ranges in license text for better deduplication.

    Replaces year ranges like "2020-2023" or "2022-2024" with a placeholder
    to allow deduplication of licenses that differ only in copyright years.

    Args:
        text: License text containing copyright years

    Returns:
        Normalized text with year ranges replaced
    """
    # Pattern to match various copyright year formats
    patterns = [
        # Copyright (c) 2020-2023
        (r"Copyright\s*\([cC]\)\s*\d{4}(?:-\d{4})?", "Copyright (c) YYYY"),
        # Copyright (c) 2020, 2021, 2022
        (r"Copyright\s*\([cC]\)\s*(?:\d{4},?\s*)+", "Copyright (c) YYYY"),
        # Copyright 2020-2023
        (r"Copyright\s+\d{4}(?:-\d{4})?", "Copyright YYYY"),
        # Copyright 2020, 2021
        (r"Copyright\s+(?:\d{4},?\s*)+", "Copyright YYYY"),
        # Just year ranges: 2020-2023
        (r"\b\d{4}-\d{4}\b", "YYYY-YYYY"),
        # Just years: 2020, 2021, 2022
        (r"\b\d{4}\b", "YYYY"),
    ]

    normalized = text
    for pattern, replacement in patterns:
        normalized = re.sub(pattern, replacement, normalized)

    return normalized


def compute_normalized_hash(text: str) -> str:
    """
    Compute a hash of license text after normalizing years.

    Args:
        text: License text

    Returns:
        SHA256 hash of normalized text
    """
    normalized = normalize_copyright_years(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def should_deduplicate_rapids_license(paths: Set[str], license_text: str) -> bool:
    """
    Determine if this RAPIDS Apache-2.0 license should be deduplicated.

    All RAPIDS projects use Apache-2.0, so we can deduplicate them by
    checking if all paths belong to RAPIDS projects.

    Args:
        paths: Set of file paths for this license
        license_text: The license text

    Returns:
        True if this license should be deduplicated
    """
    # Check if license is Apache-2.0
    if "Apache License" not in license_text and "Apache-2.0" not in license_text:
        return False

    # Check if all paths are RAPIDS projects
    return all(is_rapids_project(str(path)) for path in paths)


def find_parent_licenses_with_same_content(
    path: str, all_licenses: Dict[str, Dict[str, Any]], content_hash: str
) -> Set[str]:
    """
    Find parent directory licenses with the same content.

    Args:
        path: Path to check
        all_licenses: Dictionary of all licenses (content_hash -> info)
        content_hash: Content hash of the license at path

    Returns:
        Set of parent paths with the same content
    """
    parent_paths = set()

    # Look through all licenses with the same content hash
    for hash_key, info in all_licenses.items():
        if hash_key != content_hash:
            continue

        for other_path in info["paths"]:
            if is_parent_path(other_path, path):
                parent_paths.add(other_path)

    return parent_paths


def group_licenses_with_deduplication(
    content_map: dict,
    use_year_normalization: bool = False,
    deduplicate_rapids: bool = False,
    deduplicate_hierarchical: bool = False,
) -> dict:
    """
    Apply content-based deduplication to license content map.

    By default, only deduplicates licenses with IDENTICAL content (via SHA256 hash).
    This is the safest approach that preserves all attribution and provenance.

    Optional deduplication modes (USE WITH CAUTION):
    - year_normalization: Treats licenses as identical if they differ only in years
      (while preserving copyright holder differences)
    - deduplicate_rapids: Groups RAPIDS projects' Apache-2.0 licenses
      WARNING: Loses individual project attribution
    - deduplicate_hierarchical: Prefers parent over child licenses with identical content
      WARNING: Loses information about which subdirectories have licenses

    Args:
        content_map: Original content map (hash -> {content, filenames, paths})
        use_year_normalization: Enable year normalization (default: False)
        deduplicate_rapids: Enable RAPIDS deduplication (default: False)
        deduplicate_hierarchical: Prefer parent licenses (default: False)

    Returns:
        Deduplicated content map (by default, only exact content matches are merged)
    """
    # Content-based deduplication is already done via SHA256 hashing in extract_license_files
    # The content_map keys ARE the content hashes, so identical licenses are already grouped

    if not any([use_year_normalization, deduplicate_rapids, deduplicate_hierarchical]):
        # No additional deduplication requested - return as-is
        # Licenses with identical content are already grouped by hash
        return content_map

    result = {}
    rapids_apache_seen = False
    rapids_apache_key = None

    for content_hash, info in content_map.items():
        content = info["content"]
        paths_dict = info["paths"].copy()  # Make a copy to modify

        # Hierarchical deduplication: remove child paths if parent exists with same content
        # WARNING: This loses provenance information about subdirectories
        if deduplicate_hierarchical:
            # Get all paths with the same content (same hash or normalized hash)
            same_content_paths = set(paths_dict.keys())

            # Find paths to remove (children of other paths with same content)
            paths_to_remove = set()
            for path in list(paths_dict.keys()):
                for other_path in same_content_paths:
                    if other_path != path and is_parent_path(other_path, path):
                        # Found a parent with same content - mark child for removal
                        paths_to_remove.add(path)
                        break

            # Remove child paths
            for path in paths_to_remove:
                del paths_dict[path]

            # If all paths were removed, skip this entry entirely
            if not paths_dict:
                continue

            # Update the info with filtered paths
            info = {
                "content": content,
                "filenames": info["filenames"],
                "paths": paths_dict,
            }

        # RAPIDS deduplication
        # WARNING: This merges different copyright holders/years from different projects
        if deduplicate_rapids and should_deduplicate_rapids_license(
            set(paths_dict.keys()), content
        ):
            if rapids_apache_seen:
                result[rapids_apache_key]["paths"].update(info["paths"])
                result[rapids_apache_key]["filenames"].update(info["filenames"])
                continue
            else:
                rapids_apache_seen = True
                rapids_apache_key = content_hash

        # Year normalization
        # Normalizes year ranges while preserving copyright holder differences
        if use_year_normalization:
            normalized_hash = compute_normalized_hash(content)

            found = False
            for _existing_hash, existing_info in result.items():
                if compute_normalized_hash(existing_info["content"]) == normalized_hash:
                    existing_info["paths"].update(info["paths"])
                    existing_info["filenames"].update(info["filenames"])
                    found = True
                    break

            if found:
                continue

        result[content_hash] = info

    return result
