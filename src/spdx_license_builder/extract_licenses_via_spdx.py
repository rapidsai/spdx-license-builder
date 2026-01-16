#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Script to extract all unique SPDX entries from a RAPIDS C or C++ project build.

Relies on the build directory to be nested under the source directory we walk
"""

import argparse
import os
import re
import sys
from pathlib import Path
from collections import OrderedDict

# Import shared utility functions
from .utility import get_project_relative_path, get_license_text


def parse_license_components(license_type):
    """
    Parse a license string and extract individual license components.

    Handles compound licenses like "Apache-2.0 AND MIT" or "MIT OR Apache-2.0".

    Args:
        license_type: The SPDX license identifier (may be compound)

    Returns:
        List of individual license identifiers
    """
    # Split on common operators
    components = []

    # Split by AND/OR operators (case insensitive)
    parts = re.split(r'\s+(?:AND|OR|WITH)\s+', license_type, flags=re.IGNORECASE)

    for part in parts:
        part = part.strip()
        if part:
            components.append(part)

    return components if components else [license_type]


def extract_copyright_info(line):
    """
    Extract year range and owner from a copyright line.

    Examples:
      "Copyright (c) 2014-2022 Frank Example" -> ("2014-2022", "Frank Example")
      "Copyright (2019) Sandia Corporation" -> ("2019", "Sandia Corporation")
      "Copyright (c) Facebook, Inc. and its affiliates." -> ("", "Facebook, Inc. and its affiliates")
    """
    # Pattern 1: Copyright (c) <year> <owner> or Copyright (C) <year> <owner>
    match = re.search(r'Copyright\s*\([cC]\)\s*([\d\-,\s]+)\s+(.+?)(?:\.\s*All rights reserved\.?)?$', line, re.IGNORECASE)
    if match:
        years = match.group(1).strip()
        owner = match.group(2).strip()
        # Clean up trailing punctuation
        owner = owner.rstrip('.,;')
        return (years, owner)

    # Pattern 2: Copyright (<year>) <owner> (no 'c')
    match = re.search(r'Copyright\s*\(([\d\-,\s]+)\)\s+(.+?)(?:\.\s*All rights reserved\.?)?$', line, re.IGNORECASE)
    if match:
        years = match.group(1).strip()
        owner = match.group(2).strip()
        # Clean up trailing punctuation
        owner = owner.rstrip('.,;')
        return (years, owner)

    # Pattern 3: Copyright (c) <owner> (no year)
    match = re.search(r'Copyright\s*\([cC]\)\s+(.+?)(?:\.\s*All rights reserved\.?)?$', line, re.IGNORECASE)
    if match:
        owner = match.group(1).strip()
        # Clean up trailing punctuation
        owner = owner.rstrip('.,;')
        return ("", owner)

    # Pattern 4: Copyright <year> <owner> (no parentheses)
    match = re.search(r'Copyright\s+([\d\-,\s]+)\s+(.+?)(?:\.\s*All rights reserved\.?)?$', line, re.IGNORECASE)
    if match:
        # Check if first group is actually a year
        potential_year = match.group(1).strip()
        if re.match(r'^[\d\-,\s]+$', potential_year):
            years = potential_year
            owner = match.group(2).strip()
            owner = owner.rstrip('.,;')
            return (years, owner)

    return None


def find_spdx_entries(file_path):
    """
    Extract non-NVIDIA SPDX copyright entries from a file and associate them with licenses.

    Returns a list of tuples: [(license, year_range, owner, file_path), ...]
    Only includes non-NVIDIA copyrights.
    """
    entries = []

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

            i = 0
            while i < len(lines):
                line = lines[i].strip()

                # Look for SPDX-FileCopyrightText
                if 'SPDX-FileCopyrightText:' in line:
                    # Check if it contains NVIDIA
                    if 'NVIDIA' in line.upper():
                        i += 1
                        continue

                    # This is a non-NVIDIA copyright, start collecting
                    copyrights = []

                    # Extract copyright from current line
                    copyright_info = extract_copyright_info(line)
                    if copyright_info:
                        copyrights.append(copyright_info)

                    # Continue reading following lines for more SPDX-FileCopyrightText
                    i += 1
                    while i < len(lines):
                        next_line = lines[i].strip()

                        # If we hit a license identifier, associate it with all copyrights
                        if 'SPDX-License-Identifier:' in next_line:
                            # Extract the license type
                            license_match = re.search(r'SPDX-License-Identifier:\s*(.+?)(?:\s*$)', next_line)
                            if license_match:
                                license_type = license_match.group(1).strip()
                                # Clean up any trailing comment markers
                                license_type = re.sub(r'[*/\s]+$', '', license_type)

                                # Associate this license with all collected copyrights
                                for year_range, owner in copyrights:
                                    entries.append((license_type, year_range, owner, file_path))
                            break

                        # If we hit another FileCopyrightText (non-NVIDIA), collect it
                        elif 'SPDX-FileCopyrightText:' in next_line:
                            if 'NVIDIA' not in next_line.upper():
                                copyright_info = extract_copyright_info(next_line)
                                if copyright_info:
                                    copyrights.append(copyright_info)
                            i += 1
                        else:
                            # Some other line, continue
                            i += 1
                            # Stop if we've gone too far without finding a license
                            if i - len(copyrights) > 10:
                                break
                else:
                    i += 1

    except Exception as e:
        # Skip files that can't be read
        pass

    return entries


def walk_directories(dir_path, directories_to_exclude):
    """
    Walk through specified directoru and collect all non-NVIDIA SPDX entries.
    Don't entry any directory in the exclude list e.g ( "tests", "benchmarks" )

    Returns a dict mapping filename -> dict with 'paths' and 'licenses' info.
    """
    # Dictionary mapping filename -> {'paths': set of file paths, 'licenses': set of (license_type, year_range, owner)}
    file_map = {}
    file_count = 0
    total_entries = 0

    print(f"Scanning directory: {dir_path}", file=sys.stderr)
    for root, dirs, files in os.walk(dir_path):
        dirs[:] = [d for d in dirs if d not in directories_to_exclude]

        for file in files:
            file_path = os.path.join(root, file)
            file_count += 1

            entries = find_spdx_entries(file_path)
            total_entries += len(entries)

            # Organize entries by filename
            for license_type, year_range, owner, fpath in entries:
                filename = os.path.basename(fpath)

                if filename not in file_map:
                    file_map[filename] = {
                        'paths': set(),
                        'licenses': set()
                    }

                # Store the file path and license info
                file_map[filename]['paths'].add(fpath)
                file_map[filename]['licenses'].add((license_type, year_range, owner))

    unique_files = len(file_map)
    print(f"Scanned {file_count} files", file=sys.stderr)
    print(f"Found {total_entries} non-NVIDIA copyright entries", file=sys.stderr)
    print(f"In {unique_files} unique files with third-party licenses", file=sys.stderr)

    return file_map


def main():
    """Main function to extract and output SPDX entries."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Extract non-NVIDIA third-party SPDX license information from source code.'
    )
    parser.add_argument(
        'project_path',
        type=str,
        nargs='+',
        help='Path(s) to the project root directory/directories to scan'
    )
    parser.add_argument(
        '--with-licenses',
        action='store_true',
        help='Include full license text for each license type found'
    )
    args = parser.parse_args()

    # Validate project paths
    project_paths = []
    for path_str in args.project_path:
        project_path = Path(path_str).absolute()
        if not project_path.exists():
            print(f"Error: Project path '{project_path}' does not exist", file=sys.stderr)
            sys.exit(1)

        if not project_path.is_dir():
            print(f"Error: Project path '{project_path}' is not a directory", file=sys.stderr)
            sys.exit(1)

        project_paths.append(project_path)

    # Look for 'c' and 'cpp' directories within the project
    directories_to_scan = ["c", "cpp"]
    directories_to_exclude = ("benchmark", "cmake", "test", "tests")

    print(f"Project path(s): {', '.join(str(p) for p in project_paths)}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # Collect all unique SPDX entries organized by filename from all project paths
    file_map = {}
    for project_path in project_paths:

        for directory in directories_to_scan:
            dir_path = os.path.join(str(project_path), directory)
            if not os.path.exists(dir_path):
                print(f"Warning: Directory '{dir_path}' does not exist", file=sys.stderr)
                continue
            path_file_map = walk_directories(dir_path, directories_to_exclude)

            # Merge results from this path into the main file_map
            for filename, file_info in path_file_map.items():
                if filename not in file_map:
                    file_map[filename] = {
                        'paths': set(),
                        'licenses': set()
                    }
                file_map[filename]['paths'].update(file_info['paths'])
                file_map[filename]['licenses'].update(file_info['licenses'])

    # Output the results
    print("=" * 60, file=sys.stderr)
    print("Non-NVIDIA Third-Party Licenses:", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # Get the base path for license files (script directory)
    script_dir = Path(__file__).parent.absolute()
    licenses_base_path = script_dir

    # Print to stdout (can be redirected to a file)
    # Output header
    print("=" * 80)
    print("Non-NVIDIA Third-Party Licenses for specific files")
    print("=" * 80)
    print()
    print("Files are listed with their associated licenses and copyright holders.")
    print()

    # Track which license types we found
    found_licenses = set()

    # Sort files alphabetically for consistent output
    for filename in sorted(file_map.keys()):
        file_info = file_map[filename]
        file_paths = file_info['paths']
        license_copyright_set = file_info['licenses']

        print("=" * 80)
        print(f"File: {filename}")
        print("=" * 80)
        print()

        # Display file locations using project heuristic
        print("  Locations:")
        # Group paths by project for cleaner output
        project_paths = {}
        for fpath in file_paths:
            project_name, rel_path = get_project_relative_path(fpath)
            if project_name:
                if project_name not in project_paths:
                    project_paths[project_name] = set()
                project_paths[project_name].add(rel_path)
            else:
                # No project detected, use full path
                if 'unknown' not in project_paths:
                    project_paths['unknown'] = set()
                project_paths['unknown'].add(rel_path)

        # Print grouped by project
        for project in sorted(project_paths.keys()):
            for rel_path in sorted(project_paths[project]):
                print(f"    {project}: {rel_path}")
        print()

        # Group by license type for better readability
        licenses_dict = {}
        for license_type, year_range, owner in license_copyright_set:
            if license_type not in licenses_dict:
                licenses_dict[license_type] = []
            licenses_dict[license_type].append((year_range, owner))

            # Track this license type
            found_licenses.add(license_type)

        # Output each license and its copyrights
        for license_type in sorted(licenses_dict.keys()):
            print(f"  License: {license_type}")
            print()

            # Sort copyrights by owner
            copyrights = sorted(licenses_dict[license_type], key=lambda x: (x[1], x[0]))
            for year_range, owner in copyrights:
                if year_range:
                    print(f"    Copyright (c) {year_range} {owner}")
                else:
                    print(f"    Copyright (c) {owner}")
            print()

        print()

    # Output full license texts if requested
    if args.with_licenses and found_licenses:
        print()
        print("=" * 80)
        print("FULL LICENSE TEXTS")
        print("=" * 80)
        print()

        # Track which license files we've already printed
        printed_license_files = set()
        # Track unknown licenses to avoid duplicate warnings
        unknown_licenses = set()

        for license_type in sorted(found_licenses):
            # Parse compound licenses (e.g., "Apache-2.0 AND MIT" -> ["Apache-2.0", "MIT"])
            license_components = parse_license_components(license_type)

            for component in license_components:
                # If we haven't printed this license yet, print it
                if component not in printed_license_files:
                    license_text = get_license_text(component, licenses_base_path)

                    if license_text:
                        print("=" * 80)
                        print(f"{component}")
                        print("=" * 80)
                        print(license_text)
                        print()
                        printed_license_files.add(component)
                    elif component not in unknown_licenses:
                        # Could not fetch license text
                        print("=" * 80)
                        print(f"{component}")
                        print("=" * 80)
                        print(f"(Full license text not available for {component})")
                        print()
                        unknown_licenses.add(component)

        print("=" * 80)


if __name__ == "__main__":
    main()

