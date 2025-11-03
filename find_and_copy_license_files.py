#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION.
# SPDX-License-Identifier: Apache-2.0
#

"""
Script to extract all LICENSE files from project directories and organize them by project.

Uses the same directory search logic as extract_licenses_via_spdx.py to find LICENSE files in 'c' and 'cpp' directories.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

# Import shared utility functions
from utility import get_project_relative_path, walk_directories_for_files


def extract_license_files(project_paths, output_dir):
    """
    Extract LICENSE files from project directories and copy them to output directory.

    Args:
        project_paths: List of project root directories to scan
        output_dir: Output directory where LICENSE files will be copied

    Returns:
        Dictionary mapping (filename, project, subdirs) -> source_path
    """
    # Dictionary to track license files by project and subdirectory
    license_files = {}

    # Directories to scan within each project (same as extract_licenses_via_spdx.py)
    directories_to_scan = ["c", "cpp"]

    for project_path in project_paths:
        print(f"Scanning project: {project_path}", file=sys.stderr)

        # Find all files starting with LICENSE
        matching_files = walk_directories_for_files(
            str(project_path),
            directories_to_scan,
            "LICENSE"
        )

        print(f"Found {len(matching_files)} LICENSE file(s)", file=sys.stderr)

        # Process each LICENSE file
        for file_path in matching_files:
            # Get project name using the heuristic function
            project_name, relative_path = get_project_relative_path(file_path)

            # Use 'unknown' if no project detected
            if project_name is None:
                project_name = "unknown"

            # Get just the filename
            filename = os.path.basename(file_path)

            # Extract subdirectory path (everything between project root and filename)
            # relative_path contains the full path from project root, including filename
            # We want the directory components only
            rel_path_obj = Path(relative_path)
            if len(rel_path_obj.parts) > 1:
                # There are subdirectories between project root and the file
                subdirs = '-'.join(rel_path_obj.parts[:-1])  # All parts except filename
            else:
                # File is directly in project root
                subdirs = ""

            # Track this license file with subdirectory information
            key = (filename, project_name, subdirs)
            if key not in license_files:
                license_files[key] = []
            license_files[key].append(file_path)

    return license_files


def copy_license_files(license_files, output_dir):
    """
    Copy license files to the output directory with project-specific names.

    Args:
        license_files: Dictionary mapping (filename, project, subdirs) -> list of source paths
        output_dir: Output directory where files will be copied
    """
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    copied_count = 0

    for (filename, project_name, subdirs), source_paths in license_files.items():
        # Use the first occurrence of each (filename, project, subdirs) tuple
        source_path = source_paths[0]

        # Create output filename: <filename>-<project>[-<subdirs>]
        # Format: LICENSE-cccl or LICENSE.TXT-cccl-libcudacxx
        if subdirs:
            output_filename = f"{filename}-{project_name}-{subdirs}"
        else:
            output_filename = f"{filename}-{project_name}"

        output_file_path = output_path / output_filename

        try:
            # Copy the file
            shutil.copy2(source_path, output_file_path)
            print(f"Copied: {source_path} -> {output_file_path}", file=sys.stderr)
            copied_count += 1

            # If there are multiple sources for this key, note it
            if len(source_paths) > 1:
                print(f"  Note: {len(source_paths)} instances found, using first one", file=sys.stderr)

        except Exception as e:
            print(f"Error copying {source_path}: {e}", file=sys.stderr)

    print(f"\nTotal files copied: {copied_count}", file=sys.stderr)


def main():
    """Main function to extract LICENSE files."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Extract LICENSE files from project directories and organize by project.'
    )
    parser.add_argument(
        'project_path',
        type=str,
        nargs='+',
        help='Path(s) to the project root directory/directories to scan'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        required=True,
        help='Output directory where LICENSE files will be copied'
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

    print(f"Project path(s): {', '.join(str(p) for p in project_paths)}", file=sys.stderr)
    print(f"Output directory: {args.output}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # Extract license files from all project paths
    license_files = extract_license_files(project_paths, args.output)

    if not license_files:
        print("No LICENSE files found.", file=sys.stderr)
        return

    # Display what was found
    print("=" * 60, file=sys.stderr)
    print(f"Found LICENSE files in {len(license_files)} unique location(s):", file=sys.stderr)
    for (filename, project_name, subdirs), paths in sorted(license_files.items()):
        location = f"{project_name}/{subdirs}" if subdirs else project_name
        print(f"  {filename} in '{location}': {len(paths)} instance(s)", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # Copy files to output directory
    copy_license_files(license_files, args.output)


if __name__ == "__main__":
    main()

