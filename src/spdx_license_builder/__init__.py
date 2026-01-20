#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
SPDX License Builder Tools

A collection of tools for extracting and managing license information from projects.
"""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("spdx-license-builder")
except importlib.metadata.PackageNotFoundError:
    # Package is not installed, read from VERSION file
    from pathlib import Path

    _version_file = Path(__file__).parent.parent.parent / "VERSION"
    __version__ = _version_file.read_text().strip()

from .deduplication import (
    compute_normalized_hash,
    find_parent_licenses_with_same_content,
    get_directory_depth,
    group_licenses_with_deduplication,
    is_nvidia_project,
    is_parent_path,
    is_rapids_project,
    normalize_copyright_years,
    should_deduplicate_rapids_license,
    should_prefer_parent_license,
)
from .extractors import (
    DependencyLicenseExtractor,
    LicenseExtractor,
    LicenseReportBuilder,
    SpdxExtractor,
)
from .license_records import (
    CopyrightInfo,
    DependencyLicense,
    LicenseReport,
    LicenseText,
    SpdxCopyright,
    SpdxEntry,
)
from .utility import get_license_text, get_project_relative_path, walk_directories_for_files

__all__ = [
    # Utility functions
    "get_project_relative_path",
    "get_license_text",
    "walk_directories_for_files",
    # Deduplication functions
    "normalize_copyright_years",
    "compute_normalized_hash",
    "is_rapids_project",
    "is_nvidia_project",
    "is_parent_path",
    "get_directory_depth",
    "should_deduplicate_rapids_license",
    "should_prefer_parent_license",
    "find_parent_licenses_with_same_content",
    "group_licenses_with_deduplication",
    # OOP classes - Extractors
    "LicenseExtractor",
    "SpdxExtractor",
    "DependencyLicenseExtractor",
    "LicenseReportBuilder",
    # OOP classes - Data records
    "SpdxEntry",
    "LicenseText",
    "DependencyLicense",
    "LicenseReport",
    "CopyrightInfo",
    "SpdxCopyright",
]
