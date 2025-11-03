#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION.
# SPDX-License-Identifier: Apache-2.0
#

"""
Utility functions for license extraction scripts.
"""

import json
import os
import re
import sys
import urllib.request
from pathlib import Path


def get_project_relative_path(file_path):
    """
    Extract the project name and relative path from a file path using heuristics.

    Heuristics (in priority order):
    1. If a directory has a '-src' suffix, that's the project name (highest priority)
    2. If a directory is 'c' or 'cpp', the parent directory is the project name

    Args:
        file_path: Full file path

    Returns:
        Tuple of (project_name, relative_path) or (None, filename) if no project found
    """
    path_parts = Path(file_path).parts
    filename = Path(file_path).name

    # Single pass: Iterate in reverse to check both heuristics
    # Remember c/cpp match but prefer -src if found (higher priority)
    c_cpp_match = None

    for i in range(len(path_parts) - 1, -1, -1):
        part = path_parts[i]

        # Check for 'c' or 'cpp' directories (lower priority)
        # Remember the first one we find (from right to left), but keep searching for -src
        if part in ('c', 'cpp') and i > 0 and c_cpp_match is None:
            project_name = path_parts[i-1]
            remaining_parts = path_parts[i:]
            if remaining_parts:
                relative_path = str(Path(*remaining_parts))
                c_cpp_match = (project_name, relative_path)

        # Check for -src directories (higher priority)
        # Return immediately when found, overriding any c/cpp match
        if part.endswith('-src'):
            project_name = part.replace('-src', '')
            remaining_parts = path_parts[i+1:]
            if remaining_parts:
                relative_path = str(Path(*remaining_parts))
                return (project_name, relative_path)
            else:
                return (project_name, filename)

    # If we found a c/cpp match but no -src, return the c/cpp match
    if c_cpp_match:
        return c_cpp_match

    # No project found, return just the filename
    return (None, filename)


def get_license_text(license_type, base_path):
    """
    Read license text from local cache or fetch from SPDX API.

    Algorithm:
    1. First search the common_licenses directory for the short form license
    2. Then search the infrequent_licenses directory for the short form license
    3. If not found locally, pull the license via http://spdx.org/licenses/[licenseID].json
    4. Cache fetched licenses in infrequent_licenses directory

    Args:
        license_type: The SPDX license identifier
        base_path: Base path to the project directory

    Returns:
        The license text as a string, or None if not found
    """
    # Clean the license type (remove trailing whitespace, comment markers, etc.)
    license_id = re.sub(r'[*/\s]+$', '', license_type.strip())

    # Check local directories in priority order
    license_directories = ["common_licenses", "infrequent_licenses"]

    for dir_name in license_directories:
        license_path = base_path / dir_name / f"{license_id}.txt"
        if license_path.exists():
            try:
                with open(license_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                print(f"Warning: Could not read license file {license_path}: {e}", file=sys.stderr)

    # Fetch from SPDX API
    spdx_url = f"http://spdx.org/licenses/{license_id}.json"
    try:
        print(f"Fetching license {license_id} from SPDX API...", file=sys.stderr)
        with urllib.request.urlopen(spdx_url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            license_text = data.get('licenseText')

            if license_text:
                # Cache the license in infrequent_licenses directory
                infrequent_dir = base_path / "infrequent_licenses"
                infrequent_dir.mkdir(exist_ok=True)

                cache_path = infrequent_dir / f"{license_id}.txt"
                try:
                    with open(cache_path, 'w', encoding='utf-8') as f:
                        f.write(license_text)
                    print(f"Cached license {license_id} to {cache_path}", file=sys.stderr)
                except Exception as e:
                    print(f"Warning: Could not cache license file {cache_path}: {e}", file=sys.stderr)

                return license_text
            else:
                print(f"Warning: No licenseText field found in SPDX response for {license_id}", file=sys.stderr)
                return None

    except urllib.error.HTTPError as e:
        print(f"Warning: Could not fetch license {license_id} from SPDX API (HTTP {e.code})", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Warning: Error fetching license {license_id} from SPDX API: {e}", file=sys.stderr)
        return None


def walk_directories_for_files(base_path, directories, file_pattern):
    """
    Walk through specified directories and collect all files matching a pattern.

    Args:
        base_path: Base path to start searching from
        directories: List of directory names to search (e.g., ["c", "cpp"])
        file_pattern: Pattern to match files (e.g., "LICENSE*")

    Returns:
        List of file paths that match the pattern
    """
    matching_files = []

    for directory in directories:
        dir_path = os.path.join(base_path, directory)

        if not os.path.exists(dir_path):
            print(f"Warning: Directory '{dir_path}' does not exist", file=sys.stderr)
            continue

        print(f"Scanning directory: {dir_path}", file=sys.stderr)
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                # Check if file matches the pattern (starts with)
                if file.startswith(file_pattern):
                    file_path = os.path.join(root, file)
                    matching_files.append(file_path)

    return matching_files

