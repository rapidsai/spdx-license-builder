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
from typing import Optional, Set

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

# CCCL sub-components
CCCL_COMPONENTS = {"cub", "thrust", "libcudacxx"}


def is_rapids_project(path: str) -> bool:
    """
    Check if a path belongs to a RAPIDS project.

    Args:
        path: File path to check

    Returns:
        True if the path contains a RAPIDS project name
    """
    path.lower()
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


def is_cccl_component(path: str) -> Optional[str]:
    """
    Check if a path belongs to a CCCL sub-component.

    Args:
        path: File path to check

    Returns:
        Component name if found, None otherwise
    """
    path_parts = Path(path).parts

    for part in path_parts:
        part_lower = part.lower()
        part_clean = part_lower.replace("-src", "").replace("_src", "")

        if part_clean in CCCL_COMPONENTS:
            return part_clean

    return None


def is_cccl_root(path: str) -> bool:
    """
    Check if a path is the CCCL root LICENSE.

    Args:
        path: File path to check

    Returns:
        True if this is the CCCL root LICENSE
    """
    path_parts = Path(path).parts

    # Look for "cccl" in path but NOT followed by a component name
    for i, part in enumerate(path_parts):
        part_lower = part.lower()
        part_clean = part_lower.replace("-src", "").replace("_src", "")

        if part_clean == "cccl":
            # Check if the next part is a component
            if i + 1 < len(path_parts):
                next_part = path_parts[i + 1].lower()
                if next_part not in CCCL_COMPONENTS:
                    return True
            else:
                return True

    return False


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


def should_skip_cccl_component_license(path: str, all_paths: Set[str]) -> bool:
    """
    Determine if a CCCL component license should be skipped.

    If we have the CCCL root LICENSE, we should skip component licenses
    since the root LICENSE contains all of them.

    Args:
        path: Path to the component LICENSE
        all_paths: All LICENSE file paths found

    Returns:
        True if this component license should be skipped
    """
    # Check if this is a CCCL component
    component = is_cccl_component(path)
    if not component:
        return False

    # Check if we have the CCCL root license
    has_root = any(is_cccl_root(str(p)) for p in all_paths)

    return has_root


def group_licenses_with_deduplication(
    content_map: dict,
    use_year_normalization: bool = True,
    deduplicate_rapids: bool = True,
    handle_cccl: bool = True,
) -> dict:
    """
    Apply advanced deduplication logic to license content map.

    Args:
        content_map: Original content map (hash -> {content, filenames, paths})
        use_year_normalization: Enable year normalization
        deduplicate_rapids: Enable RAPIDS deduplication
        handle_cccl: Enable CCCL special handling

    Returns:
        Deduplicated content map
    """
    if not any([use_year_normalization, deduplicate_rapids, handle_cccl]):
        # No deduplication requested
        return content_map

    result = {}
    rapids_apache_seen = False
    rapids_apache_key = None
    all_paths = set()

    # Collect all paths
    for info in content_map.values():
        all_paths.update(info["paths"].keys())

    for content_hash, info in content_map.items():
        content = info["content"]
        paths = set(info["paths"].keys())

        # CCCL handling: skip component licenses if we have root
        if handle_cccl:
            # Check if all paths are CCCL components that should be skipped
            skip_all = all(should_skip_cccl_component_license(p, all_paths) for p in paths)
            if skip_all:
                continue

        # RAPIDS deduplication
        if deduplicate_rapids and should_deduplicate_rapids_license(paths, content):
            if rapids_apache_seen:
                # Merge with existing RAPIDS Apache license
                result[rapids_apache_key]["paths"].update(info["paths"])
                result[rapids_apache_key]["filenames"].update(info["filenames"])
                continue
            else:
                # First RAPIDS Apache license
                rapids_apache_seen = True
                rapids_apache_key = content_hash

        # Year normalization
        if use_year_normalization:
            normalized_hash = compute_normalized_hash(content)

            # Check if we already have this normalized license
            found = False
            for _existing_hash, existing_info in result.items():
                if compute_normalized_hash(existing_info["content"]) == normalized_hash:
                    # Merge with existing
                    existing_info["paths"].update(info["paths"])
                    existing_info["filenames"].update(info["filenames"])
                    found = True
                    break

            if found:
                continue

        # Add to result
        result[content_hash] = info

    return result
