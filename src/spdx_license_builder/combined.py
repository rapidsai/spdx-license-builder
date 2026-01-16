#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Combined license extraction: runs both SPDX extract and LICENSE file copy operations.

This module provides a single command that:
1. Extracts SPDX copyright entries from source files
2. Finds and extracts LICENSE files from dependencies
3. Combines both outputs into a single comprehensive license report
"""

import contextlib
import sys
from pathlib import Path


@contextlib.contextmanager
def output_context(output_file):
    """Context manager for writing to file or stdout."""
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            yield f
    else:
        yield sys.stdout


def run_combined(
    project_paths,
    with_licenses=True,
    output_file=None,
    deduplicate_rapids=True,
    handle_cccl=True,
    normalize_years=True,
):
    """
    Run both extract and copy operations and combine their output.

    Args:
        project_paths: List of project paths to scan
        with_licenses: Include full license texts for SPDX entries
        output_file: Output file path (None for stdout)
        deduplicate_rapids: Deduplicate RAPIDS/NVIDIA licenses
        handle_cccl: Special handling for CCCL licenses
        normalize_years: Normalize copyright years for deduplication
    """
    from .deduplication import group_licenses_with_deduplication
    from .extract_licenses_via_spdx import walk_directories
    from .find_and_copy_license_files import extract_license_files
    from .utility import get_license_text, get_project_relative_path

    # Validate project paths
    validated_paths = []
    for path_str in project_paths:
        project_path = Path(path_str).absolute()
        if not project_path.exists():
            print(f"Error: Project path '{project_path}' does not exist", file=sys.stderr)
            sys.exit(1)
        if not project_path.is_dir():
            print(f"Error: Project path '{project_path}' is not a directory", file=sys.stderr)
            sys.exit(1)
        validated_paths.append(project_path)

    print(f"Project path(s): {', '.join(str(p) for p in validated_paths)}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    if output_file:
        print(f"Writing output to: {output_file}", file=sys.stderr)

    # ========================================================================
    # PART 1: Extract SPDX copyright entries from source files
    # ========================================================================
    print("Step 1: Extracting SPDX copyright entries from source files...", file=sys.stderr)

    directories_to_exclude_extract = (
        ".git",
        ".github",
        "build",
        "dist",
        "_build",
        "node_modules",
        "venv",
        ".venv",
        "benchmark",
        "benchmarks",
        "cmake",
        "test",
        "tests",
        "docs",
        "examples",
    )

    file_map = {}
    for project_path in validated_paths:
        print(f"  Scanning directory: {project_path}", file=sys.stderr)
        path_file_map = walk_directories(str(project_path), directories_to_exclude_extract)

        # Merge results
        for filename, file_info in path_file_map.items():
            if filename not in file_map:
                file_map[filename] = {"paths": set(), "licenses": set()}
            file_map[filename]["paths"].update(file_info["paths"])
            file_map[filename]["licenses"].update(file_info["licenses"])

    total_spdx_files = sum(len(info["paths"]) for info in file_map.values())
    print(
        f"  Found {len(file_map)} unique files with {total_spdx_files} SPDX entries",
        file=sys.stderr,
    )

    # ========================================================================
    # PART 2: Extract LICENSE files from dependencies
    # ========================================================================
    print("Step 2: Extracting LICENSE files from dependencies...", file=sys.stderr)

    content_map = extract_license_files(validated_paths)

    if content_map:
        # Apply deduplication
        content_map = group_licenses_with_deduplication(
            content_map,
            use_year_normalization=normalize_years,
            deduplicate_rapids=deduplicate_rapids,
            handle_cccl=handle_cccl,
        )
        print(
            f"  Found {len(content_map)} unique LICENSE files "
            f"(RAPIDS: {deduplicate_rapids}, CCCL: {handle_cccl}, Years: {normalize_years})",
            file=sys.stderr,
        )
    else:
        print("  No LICENSE files found", file=sys.stderr)

    print("=" * 60, file=sys.stderr)

    # ========================================================================
    # PART 3: Combine and output results
    # ========================================================================
    with output_context(output_file) as out:
        # Output header
        print("=" * 80, file=out)
        print("THIRD-PARTY SOFTWARE LICENSES", file=out)
        print("=" * 80, file=out)
        print(file=out)
        print(
            "This file contains license information for third-party software used in this project.",
            file=out,
        )
        print(file=out)

        # ====================================================================
        # Section 1: SPDX Copyright Entries (embedded third-party code)
        # ====================================================================
        if file_map:
            print("=" * 80, file=out)
            print("SECTION 1: Third-Party Code in Source Files (SPDX Entries)", file=out)
            print("=" * 80, file=out)
            print(file=out)
            print(
                "The following files contain third-party code with SPDX copyright headers.",
                file=out,
            )
            print(file=out)

            # Track which license types we found
            found_licenses = set()

            # Sort files alphabetically for consistent output
            for filename in sorted(file_map.keys()):
                file_info = file_map[filename]
                file_paths = file_info["paths"]
                license_copyright_set = file_info["licenses"]

                print("-" * 80, file=out)
                print(f"File: {filename}", file=out)
                print("-" * 80, file=out)
                print(file=out)

                # Display file locations
                print("  Locations:", file=out)
                project_paths_dict = {}
                for fpath in file_paths:
                    matching_root = None
                    for proj_path in validated_paths:
                        if fpath.startswith(str(proj_path)):
                            matching_root = str(proj_path)
                            break
                    project_name, rel_path = get_project_relative_path(
                        fpath, project_root=matching_root
                    )
                    if project_name:
                        if project_name not in project_paths_dict:
                            project_paths_dict[project_name] = set()
                        project_paths_dict[project_name].add(rel_path)
                    else:
                        if "unknown" not in project_paths_dict:
                            project_paths_dict["unknown"] = set()
                        project_paths_dict["unknown"].add(rel_path)

                for project in sorted(project_paths_dict.keys()):
                    for rel_path in sorted(project_paths_dict[project]):
                        print(f"    {project}: {rel_path}", file=out)
                print(file=out)

                # Group by license type
                licenses_dict = {}
                for license_type, year_range, owner in license_copyright_set:
                    if license_type not in licenses_dict:
                        licenses_dict[license_type] = []
                        found_licenses.add(license_type)
                    licenses_dict[license_type].append((year_range, owner))

                for license_type in sorted(licenses_dict.keys()):
                    print(f"  License: {license_type}", file=out)
                    print(file=out)
                    for year_range, owner in sorted(licenses_dict[license_type]):
                        if year_range:
                            print(f"    Copyright (c) {year_range}, {owner}", file=out)
                        else:
                            print(f"    Copyright (c) {owner}", file=out)
                    print(file=out)

            # Output full license texts if requested
            if with_licenses and found_licenses:
                print("=" * 80, file=out)
                print("Full License Texts for SPDX Entries", file=out)
                print("=" * 80, file=out)
                print(file=out)

                for license_id in sorted(found_licenses):
                    print("-" * 80, file=out)
                    print(f"License: {license_id}", file=out)
                    print("-" * 80, file=out)
                    print(file=out)

                    # Get license text using the first project path as base
                    base_path = Path(__file__).parent
                    license_text = get_license_text(license_id, base_path)

                    if license_text:
                        for line in license_text.splitlines():
                            print(line, file=out)
                    else:
                        print(f"License text for {license_id} not available.", file=out)

                    print(file=out)
                    print(file=out)

        # ====================================================================
        # Section 2: LICENSE Files (dependencies)
        # ====================================================================
        if content_map:
            print("=" * 80, file=out)
            print("SECTION 2: Dependency LICENSE Files", file=out)
            print("=" * 80, file=out)
            print(file=out)
            print("The following LICENSE files were found in dependency directories.", file=out)
            print(file=out)

            sorted_items = sorted(content_map.items(), key=lambda x: sorted(x[1]["filenames"])[0])

            for _idx, (_content_hash, file_info) in enumerate(sorted_items, 1):
                file_paths_dict = file_info["paths"]
                license_content = file_info["content"]

                print("-" * 80, file=out)
                print("  Locations:", file=out)
                project_paths_map = {}
                for full_path, rel_path in file_paths_dict.items():
                    matching_root = None
                    for proj_path in validated_paths:
                        if full_path.startswith(str(proj_path)):
                            matching_root = str(proj_path)
                            break

                    project_name, _ = get_project_relative_path(
                        full_path, project_root=matching_root
                    )
                    if project_name:
                        if project_name not in project_paths_map:
                            project_paths_map[project_name] = set()
                        project_paths_map[project_name].add(rel_path)
                    else:
                        if "unknown" not in project_paths_map:
                            project_paths_map["unknown"] = set()
                        project_paths_map["unknown"].add(rel_path)

                for project in sorted(project_paths_map.keys()):
                    for rel_path in sorted(project_paths_map[project]):
                        print(f"    {project}: {rel_path}", file=out)
                print(file=out)

                # Output the license content
                if license_content:
                    print("  License Text:", file=out)
                    print(file=out)
                    for line in license_content.splitlines():
                        print(f"    {line}", file=out)
                    print(file=out)
                else:
                    print("  (License text could not be read)", file=out)
                    print(file=out)

                print("-" * 80, file=out)
                print(file=out)

        # Final message
        if not file_map and not content_map:
            print("No third-party licenses found.", file=out)
            print(file=out)


if __name__ == "__main__":
    print("This module should be run via 'license-builder all'", file=sys.stderr)
    sys.exit(1)
