#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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

from .utility import get_project_relative_path, get_license_text, walk_directories_for_files

__all__ = [
    'get_project_relative_path',
    'get_license_text',
    'walk_directories_for_files',
]
