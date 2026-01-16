#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Script to extract all LICENSE files from project directories and output them to stdout.

Uses the same directory search logic as extract_licenses_via_spdx.py to find LICENSE files in 'c' and 'cpp' directories.
Outputs found licenses in a formatted report similar to extract_licenses_via_spdx.py.
"""

import argparse
import hashlib
import os
import sys
from pathlib import Path

# Import shared utility functions
from .utility import get_project_relative_path, walk_directories_for_files


def extract_license_files(project_paths):
    """
    Extract LICENSE files from project directories.

    Args:
        project_paths: List of project root directories to scan

    Returns:
        Dictionary mapping content_hash -> dict with 'content', 'filenames', 'paths'
        Grouped by unique license content (using hash as key), not filename
    """
    # Dictionary to track license files organized by content hash
    # Structure: content_hash -> {'content': text, 'filenames': set of filenames, 'paths': {full_path: relative_path}}
    content_map = {}
    total_files = 0

    # Directories to exclude from scanning (common non-source directories)
    # NOTE: We intentionally DO NOT exclude third-party/thirdparty directories
    # because that's where dependency licenses are typically stored!
    directories_to_exclude = (
        ".git",
        ".github",
        "build",
        "dist",
        "_build",
        "node_modules",
        "venv",
        ".venv",
        "python",
        "cmake",
        "rust",
        "test",
        "tests",
        "benchmark",
        "benchmarks",
        "docs",
        "examples",
    )

    for project_path in project_paths:
        print(f"Scanning project: {project_path}", file=sys.stderr)

        # Find all files starting with LICENSE in the entire project
        matching_files = walk_directories_for_files(
            str(project_path), directories_to_exclude, "LICENSE"
        )

        print(f"Found {len(matching_files)} LICENSE file(s)", file=sys.stderr)
        total_files += len(matching_files)

        # Process each LICENSE file
        for file_path in matching_files:
            # Get project name using the heuristic function, with project_path as fallback
            project_name, relative_path = get_project_relative_path(
                file_path, project_root=str(project_path)
            )

            # Get just the filename
            filename = os.path.basename(file_path)

            # Read the license content
            try:
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # Compute hash of content to use as key
                content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

                # Use hash as the key to group identical licenses
                if content_hash not in content_map:
                    content_map[content_hash] = {
                        "content": content,
                        "filenames": set(),
                        "paths": {},
                    }

                # Track the filename and path for this content
                content_map[content_hash]["filenames"].add(filename)
                content_map[content_hash]["paths"][file_path] = relative_path

            except (OSError, UnicodeDecodeError) as e:
                print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)
            except Exception as e:
                print(f"Unexpected error reading {file_path}: {e}", file=sys.stderr)
                raise

    print(f"Found {total_files} total LICENSE files", file=sys.stderr)
    print(f"Found {len(content_map)} unique LICENSE contents", file=sys.stderr)

    return content_map


def main():
    """Main function to extract and output LICENSE files."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Extract LICENSE files from project directories and output to stdout."
    )
    parser.add_argument(
        "project_path",
        type=str,
        nargs="+",
        help="Path(s) to the project root directory/directories to scan",
    )
    parser.add_argument(
        "--deduplicate-rapids",
        action="store_true",
        default=True,
        help="Deduplicate RAPIDS Apache-2.0 licenses (default: enabled)",
    )
    parser.add_argument(
        "--no-deduplicate-rapids",
        action="store_false",
        dest="deduplicate_rapids",
        help="Disable RAPIDS license deduplication",
    )
    parser.add_argument(
        "--handle-cccl",
        action="store_true",
        default=True,
        help="Skip CCCL component licenses when root exists (default: enabled)",
    )
    parser.add_argument(
        "--no-handle-cccl",
        action="store_false",
        dest="handle_cccl",
        help="Disable CCCL special handling",
    )
    parser.add_argument(
        "--normalize-years",
        action="store_true",
        default=True,
        help="Normalize copyright years for better deduplication (default: enabled)",
    )
    parser.add_argument(
        "--no-normalize-years",
        action="store_false",
        dest="normalize_years",
        help="Disable year normalization",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Write output to file instead of stdout",
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
    print("=" * 60, file=sys.stderr)
    if args.output:
        print(f"Writing output to: {args.output}", file=sys.stderr)

    # Extract license files from all project paths
    content_map = extract_license_files(project_paths)

    if not content_map:
        print("No LICENSE files found.", file=sys.stderr)
        return

    # Apply advanced deduplication
    from .deduplication import group_licenses_with_deduplication

    content_map = group_licenses_with_deduplication(
        content_map,
        use_year_normalization=args.normalize_years,
        deduplicate_rapids=args.deduplicate_rapids,
        handle_cccl=args.handle_cccl,
    )

    print(
        f"Applied deduplication (RAPIDS: {args.deduplicate_rapids}, "
        f"CCCL: {args.handle_cccl}, Years: {args.normalize_years})",
        file=sys.stderr,
    )

    # Open output file if specified, otherwise use stdout
    import contextlib

    @contextlib.contextmanager
    def output_context(output_file):
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                yield f
        else:
            yield sys.stdout

    with output_context(args.output) as out:
        # Sort by the first filename found for each unique content for consistent output
        sorted_items = sorted(content_map.items(), key=lambda x: sorted(x[1]["filenames"])[0])

        for _idx, (_content_hash, file_info) in enumerate(sorted_items, 1):
            file_paths_dict = file_info["paths"]
            license_content = file_info["content"]

            print("=" * 80, file=out)
            # Display file locations using project heuristic
            print("  Locations:", file=out)
            # Group paths by project for cleaner output
            project_paths_map = {}
            for full_path, rel_path in file_paths_dict.items():
                # Try to determine which project_root this file belongs to
                matching_root = None
                for proj_path in project_paths:
                    if full_path.startswith(str(proj_path)):
                        matching_root = str(proj_path)
                        break

                project_name, _ = get_project_relative_path(full_path, project_root=matching_root)
                if project_name:
                    if project_name not in project_paths_map:
                        project_paths_map[project_name] = set()
                    project_paths_map[project_name].add(rel_path)
                else:
                    # No project detected, use relative path
                    if "unknown" not in project_paths_map:
                        project_paths_map["unknown"] = set()
                    project_paths_map["unknown"].add(rel_path)

            # Print grouped by project
            for project in sorted(project_paths_map.keys()):
                for rel_path in sorted(project_paths_map[project]):
                    print(f"    {project}: {rel_path}", file=out)
            print(file=out)

            # Output the license content
            if license_content:
                print("  License Text:", file=out)
                print(file=out)
                # Indent the license text for readability
                for line in license_content.splitlines():
                    print(f"    {line}", file=out)
                print(file=out)
            else:
                print("  (License text could not be read)", file=out)
                print(file=out)

            print("=" * 80, file=out)
            print(file=out)


if __name__ == "__main__":
    main()
