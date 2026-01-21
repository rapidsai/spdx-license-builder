#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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
from typing import List, Optional, Tuple, Union


def merge_date_ranges(date_ranges: List[str]) -> str:
    """
    Merge continuous date ranges while preserving gaps.

    Examples:
        ["2023", "2024"] -> "2023-2024"
        ["2023-2024", "2024-2025"] -> "2023-2025"
        ["2000-2010", "2012-2025"] -> "2000-2010, 2012-2025" (gap preserved)
        ["2023"] -> "2023"

    Args:
        date_ranges: List of date ranges as strings (e.g., ["2023", "2024-2025"])

    Returns:
        Merged date range string
    """
    if not date_ranges:
        return ""

    if len(date_ranges) == 1:
        return date_ranges[0]

    # Parse all ranges into (start, end) tuples
    ranges = []
    for date_range in date_ranges:
        date_range = date_range.strip()
        if not date_range:
            continue

        if "-" in date_range:
            parts = date_range.split("-")
            try:
                start = int(parts[0].strip())
                end = int(parts[-1].strip())
                ranges.append((start, end))
            except (ValueError, IndexError):
                # Can't parse, keep as-is
                continue
        else:
            try:
                year = int(date_range)
                ranges.append((year, year))
            except ValueError:
                continue

    if not ranges:
        return ", ".join(date_ranges)

    # Sort ranges by start year
    ranges.sort()

    # Merge continuous ranges
    merged = []
    current_start, current_end = ranges[0]

    for start, end in ranges[1:]:
        # Check if ranges are continuous (no gap)
        if start <= current_end + 1:
            # Merge: extend current range
            current_end = max(current_end, end)
        else:
            # Gap found: save current range and start new one
            merged.append((current_start, current_end))
            current_start, current_end = start, end

    # Add the last range
    merged.append((current_start, current_end))

    # Format output
    formatted = []
    for start, end in merged:
        if start == end:
            formatted.append(str(start))
        else:
            formatted.append(f"{start}-{end}")

    return ", ".join(formatted)


def extract_copyright_from_license_text(license_content: str) -> List[Tuple[str, str]]:
    """
    Extract copyright statements from LICENSE file content.

    Returns a list of (year_range, owner) tuples found in the license text.
    Typically looks for copyright statements near the top of the file.

    Args:
        license_content: The full text content of the license file

    Returns:
        List of tuples (year_range, owner) for each copyright found
    """
    copyrights = []

    # Process first 20 lines (where copyright statements typically appear)
    lines = license_content.split("\n")[:20]

    # Copyright patterns (similar to SPDX extraction but adapted for LICENSE files)
    # Patterns handle years, year ranges, and "year - present" format
    patterns = [
        # Pattern 1: Copyright (c) <year-range>, <owner> (with comma separator)
        (
            r"Copyright\s*\([cC]\)\s*([\d\-]+(?:\s+-\s+\w+)?),\s+(.+?)(?:\.\s*All rights reserved\.?)?$",
            True,
            False,
        ),
        # Pattern 2: Copyright (c) <year-range> <owner> (no comma, allows "year - present")
        (
            r"Copyright\s*\([cC]\)\s*([\d\-]+(?:\s+-\s+\w+)?)\s+(.+?)(?:\.\s*All rights reserved\.?)?$",
            True,
            False,
        ),
        # Pattern 3: Copyright (<year>), <owner> (no 'c', with comma after parens)
        (r"Copyright\s*\(([\d\-]+)\),\s+(.+?)(?:\.\s*All rights reserved\.?)?$", True, False),
        # Pattern 4: Copyright (<year>) <owner> (no 'c', no comma)
        (r"Copyright\s*\(([\d\-]+)\)\s+(.+?)(?:\.\s*All rights reserved\.?)?$", True, False),
        # Pattern 5: Copyright (c) <owner> (no year)
        (r"Copyright\s*\([cC]\)\s+(.+?)(?:\.\s*All rights reserved\.?)?$", False, False),
        # Pattern 6: Copyright <year>, <owner> (no parentheses, with comma)
        (
            r"Copyright\s+([\d\-]+(?:\s+-\s+\w+)?),\s+(.+?)(?:\.\s*All rights reserved\.?)?$",
            True,
            True,
        ),
        # Pattern 7: Copyright <year> <owner> (no parentheses, no comma)
        (r"Copyright\s+([\d\-]+)\s+(.+?)(?:\.\s*All rights reserved\.?)?$", True, True),
    ]

    for line in lines:
        line = line.strip()
        if not line or not line.lower().startswith("copyright"):
            continue

        # Try patterns in order
        for pattern, has_years, validate_years in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                if has_years:
                    years = match.group(1).strip()
                    owner = match.group(2).strip()
                    # Extra validation for patterns without parentheses
                    if validate_years and not re.match(r"^[\d\-]+$", years):
                        continue
                    copyrights.append((years, owner))
                    break
                else:
                    # No years in this pattern
                    owner = match.group(1).strip()
                    copyrights.append(("", owner))
                    break

    return copyrights


def detect_license_type(license_content: str) -> Optional[str]:
    """
    Attempt to detect the license type from license file content.

    Uses pattern matching against known license text signatures.
    Detects aggregate license files containing multiple distinct licenses.

    Args:
        license_content: The full text content of the license file

    Returns:
        SPDX license identifier if detected, "Multiple-Licenses" for aggregate files,
        None otherwise
    """
    matched_licenses = extract_all_licenses(license_content)

    # If we found multiple distinct licenses, it's an aggregate file
    if len(matched_licenses) >= 2:
        return "Multiple-Licenses"

    # Single license detected
    if len(matched_licenses) == 1:
        return matched_licenses[0]

    return None


def extract_all_licenses(license_content: str) -> List[str]:
    """
    Extract all license types from license file content.

    Uses pattern matching against known license text signatures.
    Useful for parsing aggregate license files that contain multiple licenses.

    Args:
        license_content: The full text content of the license file

    Returns:
        List of SPDX license identifiers found in the content
    """
    # Normalize content for matching: lowercase, collapse whitespace
    normalized = re.sub(r"\s+", " ", license_content.lower().strip())

    # License detection patterns (in order of specificity)
    # Each pattern includes unique identifying text from that license
    patterns = [
        # Apache-2.0
        (r"apache license.*version 2\.0.*january 2004", "Apache-2.0"),
        # MIT
        (
            r"permission is hereby granted.*free of charge.*to deal in the software without restriction",
            "MIT",
        ),
        # BSD-3-Clause
        (
            r"redistribution and use in source and binary forms.*neither the name.*may be used to endorse or promote",
            "BSD-3-Clause",
        ),
        # BSD-2-Clause
        (
            r"redistribution and use in source and binary forms.*redistributions in binary form must reproduce",
            "BSD-2-Clause",
        ),
        # GPL-3.0
        (r"gnu general public license.*version 3.*29 june 2007", "GPL-3.0-only"),
        # GPL-2.0
        (r"gnu general public license.*version 2.*june 1991", "GPL-2.0-only"),
        # LGPL-3.0
        (r"gnu lesser general public license.*version 3.*29 june 2007", "LGPL-3.0-only"),
        # LGPL-2.1
        (r"gnu lesser general public license.*version 2\.1.*february 1999", "LGPL-2.1-only"),
        # MPL-2.0
        (r"mozilla public license version 2\.0", "MPL-2.0"),
        # ISC
        (
            r"permission to use, copy, modify.*and\/or distribute.*provided that.*above copyright notice",
            "ISC",
        ),
        # Unlicense
        (r"this is free and unencumbered software released into the public domain", "Unlicense"),
        # BSL-1.0 (Boost Software License)
        (r"boost software license.*version 1\.0", "BSL-1.0"),
        # NCSA (University of Illinois/NCSA Open Source License)
        (
            r"university of illinois.*ncsa.*open source license",
            "NCSA",
        ),
    ]

    # Check for all license types present
    matched_licenses = []
    for pattern, license_id in patterns:
        if re.search(pattern, normalized):
            # Avoid counting BSD-2 and BSD-3 as separate if both match
            # (BSD-3 patterns often match BSD-2 text too)
            if license_id == "BSD-2-Clause" and "BSD-3-Clause" in matched_licenses:
                continue
            matched_licenses.append(license_id)

    return matched_licenses


def get_project_relative_path(
    file_path: str, project_root: Optional[str] = None
) -> Tuple[Optional[str], str]:
    """
    Extract the project name and relative path from a file path using heuristics.

    Heuristics (in priority order):
    1. If a directory has a '-src' suffix, that's the project name (highest priority)
       - Common in CMake build directories for extracted dependencies
    2. If a directory is 'c' or 'cpp', the parent directory is the project name
       - Common in monorepos with language-specific subdirectories
    3. If project_root is provided, use its basename as the project name
       - Allows explicit project boundary definition

    Args:
        file_path: Full file path
        project_root: Optional project root directory path

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
        if part in ("c", "cpp") and i > 0 and c_cpp_match is None:
            project_name = path_parts[i - 1]
            remaining_parts = path_parts[i:]
            if remaining_parts:
                relative_path = str(Path(*remaining_parts))
                c_cpp_match = (project_name, relative_path)

        # Check for -src directories (higher priority)
        # Return immediately when found, overriding any c/cpp match
        if part.endswith("-src"):
            project_name = part.replace("-src", "")
            remaining_parts = path_parts[i + 1 :]
            if remaining_parts:
                relative_path = str(Path(*remaining_parts))
                return (project_name, relative_path)
            else:
                return (project_name, filename)

    # If we found a c/cpp match but no -src, return the c/cpp match
    if c_cpp_match:
        return c_cpp_match

    # Heuristic 3: Use project_root if provided
    if project_root:
        project_root_path = Path(project_root)
        try:
            relative = Path(file_path).relative_to(project_root_path)
            return project_root_path.name, str(relative)
        except ValueError:
            # file_path is not under project_root
            pass

    # No project detected - return just the filename
    return None, filename


def get_license_text(license_type: str, base_path: Path) -> Optional[str]:
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
    license_id = re.sub(r"[*/\s]+$", "", license_type.strip())

    # Alias common license variations to their canonical SPDX identifiers
    LICENSE_ALIASES = {
        "BSD-3": "BSD-3-Clause",
    }
    license_id = LICENSE_ALIASES.get(license_id, license_id)

    # Check local directories in priority order
    license_directories = ["common_licenses", "infrequent_licenses"]

    for dir_name in license_directories:
        license_path = base_path / dir_name / f"{license_id}.txt"
        if license_path.exists():
            try:
                with open(license_path, encoding="utf-8") as f:
                    return f.read()
            except (OSError, UnicodeDecodeError) as e:
                print(f"Warning: Could not read license file {license_path}: {e}", file=sys.stderr)
            except Exception as e:
                print(f"Unexpected error reading {license_path}: {e}", file=sys.stderr)
                raise

    # Fetch from SPDX API
    spdx_url = f"http://spdx.org/licenses/{license_id}.json"
    try:
        print(f"Fetching license {license_id} from SPDX API...", file=sys.stderr)
        with urllib.request.urlopen(spdx_url, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            license_text = data.get("licenseText")

            if license_text:
                # Cache the license in infrequent_licenses directory
                infrequent_dir = base_path / "infrequent_licenses"
                infrequent_dir.mkdir(exist_ok=True)

                cache_path = infrequent_dir / f"{license_id}.txt"
                try:
                    with open(cache_path, "w", encoding="utf-8") as f:
                        f.write(license_text)
                    print(f"Cached license {license_id} to {cache_path}", file=sys.stderr)
                except OSError as e:
                    print(
                        f"Warning: Could not cache license file {cache_path}: {e}", file=sys.stderr
                    )
                except Exception as e:
                    print(f"Unexpected error caching {cache_path}: {e}", file=sys.stderr)
                    raise

                return license_text
            else:
                print(
                    f"Warning: No licenseText field found in SPDX response for {license_id}",
                    file=sys.stderr,
                )
                return None

    except urllib.error.HTTPError as e:
        print(
            f"Warning: Could not fetch license {license_id} from SPDX API (HTTP {e.code})",
            file=sys.stderr,
        )
        return None
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        print(f"Warning: Error fetching license {license_id} from SPDX API: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Unexpected error fetching {license_id}: {e}", file=sys.stderr)
        raise


def walk_directories_for_files(
    dir_path: str,
    directories_to_exclude: Tuple[str, ...],
    file_pattern: Union[str, List[str]],
) -> List[str]:
    """
    Walk through specified directories and collect all files matching pattern(s).

    Args:
        dir_path: Base path to start searching from
        directories_to_exclude: Tuple of directory names to exclude (e.g., ("python", "rust"))
        file_pattern: Pattern(s) to match files. Can be:
                     - A single string (e.g., "LICENSE") - matches files starting with pattern
                     - A list of strings (e.g., ["LICENSE", "COPYING"]) - matches any pattern

    Returns:
        List of file paths that match the pattern(s)
    """
    matching_files = []
    excluded = set(directories_to_exclude)

    # Normalize to list
    patterns = [file_pattern] if isinstance(file_pattern, str) else file_pattern

    for root, dirs, files in os.walk(dir_path, topdown=True):
        # Filter directories in-place to prune tree traversal
        dirs[:] = [d for d in dirs if d not in excluded]

        # Filter matching files
        for file in files:
            # Check if file matches any pattern (startswith)
            if any(file.startswith(pattern) for pattern in patterns):
                matching_files.append(os.path.join(root, file))

    return matching_files


def find_project_license_file(project_path: Path) -> Optional[Tuple[Path, str, List[str]]]:
    """
    Find and parse the main LICENSE file for a project.

    Searches for LICENSE files at the project root and extracts all licenses contained within.

    Args:
        project_path: Path to the project root directory

    Returns:
        Tuple of (license_file_path, content, list_of_licenses) if found, None otherwise
        The list_of_licenses contains SPDX identifiers found in the LICENSE file.
    """
    # Common license file names to search for (in priority order)
    license_filenames = ["LICENSE", "COPYING", "COPYRIGHT", "LICENSE.txt", "LICENSE.md"]

    for filename in license_filenames:
        license_path = project_path / filename
        if license_path.exists() and license_path.is_file():
            try:
                with open(license_path, encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # Extract all licenses from the content
                licenses = extract_all_licenses(content)

                return (license_path, content, licenses)
            except (OSError, UnicodeDecodeError) as e:
                print(
                    f"Warning: Could not read project LICENSE file {license_path}: {e}",
                    file=sys.stderr,
                )
                continue
            except Exception as e:
                print(f"Unexpected error reading {license_path}: {e}", file=sys.stderr)
                raise

    return None
