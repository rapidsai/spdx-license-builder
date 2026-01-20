#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Unified command-line interface for SPDX License Builder tools.

Provides a single entry point with subcommands:
  license-builder extract  - Extract SPDX copyright entries
  license-builder copy     - Find and copy LICENSE files
  license-builder all      - Run both extract and copy (combined output)
"""

import argparse
import sys
from typing import NoReturn

from . import __version__


def main() -> NoReturn:
    """Main entry point for the unified CLI."""
    parser = argparse.ArgumentParser(
        prog="license-builder",
        description="Tools for extracting and managing license information from projects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract SPDX copyright entries
  license-builder extract /path/to/project
  license-builder extract /path/to/project --with-licenses --output third_party.txt

  # Find and copy LICENSE files
  license-builder copy /path/to/project
  license-builder copy /path/to/project1 /path/to/project2 --output licenses.txt

  # Run both extract and copy (recommended for complete license information)
  license-builder all /path/to/project --output LICENSE

For more help on a specific command:
  license-builder extract --help
  license-builder copy --help
  license-builder all --help
        """,
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(
        title="commands",
        description="Available commands",
        dest="command",
        required=True,
        help="Command to run",
    )

    # Subcommand: extract
    extract_parser = subparsers.add_parser(
        "extract",
        help="Extract SPDX copyright entries from source files",
        description="Extract non-NVIDIA third-party SPDX license information from source code.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  license-builder extract /path/to/project
  license-builder extract /path/to/project --with-licenses --output third_party.txt
  license-builder extract /path/to/project1 /path/to/project2 --with-licenses

This command scans C/C++ source files for SPDX copyright tags and extracts
non-NVIDIA third-party copyright information.
        """,
    )
    extract_parser.add_argument(
        "project_path",
        type=str,
        nargs="+",
        help="Path(s) to the project root directory/directories to scan",
    )
    extract_parser.add_argument(
        "--with-licenses",
        action="store_true",
        help="Include full license text for each license type found",
    )
    extract_parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Write output to file instead of stdout (default: stdout)",
    )

    # Subcommand: copy
    copy_parser = subparsers.add_parser(
        "copy",
        help="Find and extract LICENSE files from projects",
        description="Find all LICENSE files in project directories and output their contents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  license-builder copy /path/to/project
  license-builder copy /path/to/project1 /path/to/project2 --output all_licenses.txt
  license-builder copy /path/to/project --deduplicate-rapids --deduplicate-hierarchical

This command searches for all files starting with "LICENSE" and outputs
their full contents in a formatted report.
        """,
    )
    copy_parser.add_argument(
        "project_path",
        type=str,
        nargs="+",
        help="Path(s) to the project root directory/directories to scan",
    )
    copy_parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Write output to file instead of stdout (default: stdout)",
    )
    copy_parser.add_argument(
        "--deduplicate-rapids",
        action="store_true",
        help="[RISKY] Deduplicate RAPIDS Apache-2.0 licenses (may lose individual project attribution)",
    )
    copy_parser.add_argument(
        "--deduplicate-hierarchical",
        action="store_true",
        help="[RISKY] Prefer parent licenses over child licenses when content is identical (may lose subdirectory provenance)",
    )
    copy_parser.add_argument(
        "--normalize-years",
        action="store_true",
        help="[RISKY] Normalize copyright years for deduplication (may merge different copyright holders)",
    )

    # Subcommand: all (combined)
    all_parser = subparsers.add_parser(
        "all",
        help="Run both extract and copy commands (combined output)",
        description="Extract SPDX copyright entries and LICENSE files in a single command.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  license-builder all /path/to/project --output LICENSE
  license-builder all /path/to/project --with-licenses --output all_licenses.txt
  license-builder all /path/to/project1 /path/to/project2 --with-licenses

This command runs both 'extract' and 'copy' operations and combines their
output into a single comprehensive license report.
        """,
    )
    all_parser.add_argument(
        "project_path",
        type=str,
        nargs="+",
        help="Path(s) to the project root directory/directories to scan",
    )
    all_parser.add_argument(
        "--with-licenses",
        action="store_true",
        help="Include full license text for SPDX entries (default: True)",
        default=True,
    )
    all_parser.add_argument(
        "--no-licenses",
        action="store_false",
        dest="with_licenses",
        help="Don't include full license text for SPDX entries",
    )
    all_parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Write output to file instead of stdout (default: stdout)",
    )
    all_parser.add_argument(
        "--deduplicate-rapids",
        action="store_true",
        help="[RISKY] Deduplicate RAPIDS Apache-2.0 licenses (may lose individual project attribution)",
    )
    all_parser.add_argument(
        "--deduplicate-hierarchical",
        action="store_true",
        help="[RISKY] Prefer parent licenses over child licenses when content is identical (may lose subdirectory provenance)",
    )
    all_parser.add_argument(
        "--normalize-years",
        action="store_true",
        help="[RISKY] Normalize copyright years for deduplication (may merge different copyright holders)",
    )

    # Parse arguments
    args = parser.parse_args()

    # Route to appropriate command
    if args.command == "extract":
        _run_extract_command(args)

    elif args.command == "copy":
        _run_copy_command(args)

    elif args.command == "all":
        _run_all_command(args)

    else:
        parser.print_help()
        sys.exit(1)


def _run_extract_command(args) -> None:
    """Run the extract command using OOP classes."""
    import contextlib
    from pathlib import Path

    from .extractors import SpdxExtractor
    from .license_records import LicenseText, SpdxEntry
    from .utility import get_license_text, get_project_relative_path

    project_paths = [Path(p) for p in args.project_path]

    print(f"Project path(s): {', '.join(str(p) for p in project_paths)}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    if args.output:
        print(f"Writing output to: {args.output}", file=sys.stderr)

    # Extract SPDX entries
    extractor = SpdxExtractor(project_paths, verbose=True)
    file_map = extractor.extract()

    print("=" * 60, file=sys.stderr)
    print("Non-NVIDIA Third-Party Licenses:", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # Build SPDX entries
    spdx_entries = []
    found_licenses = set()

    for filename in sorted(file_map.keys()):
        file_info = file_map[filename]
        file_paths = file_info["paths"]
        license_copyright_set = file_info["licenses"]

        locations = {}
        for fpath in file_paths:
            project_name, rel_path = get_project_relative_path(fpath)
            project_key = project_name if project_name else "unknown"
            if project_key not in locations:
                locations[project_key] = set()
            locations[project_key].add(rel_path)

        licenses_dict = {}
        for copyright_info in license_copyright_set:
            if copyright_info.license_type not in licenses_dict:
                licenses_dict[copyright_info.license_type] = []
            licenses_dict[copyright_info.license_type].append(
                (copyright_info.year_range, copyright_info.owner)
            )
            found_licenses.add(copyright_info.license_type)

        spdx_entries.append(
            SpdxEntry(filename=filename, locations=locations, licenses=licenses_dict)
        )

    # Build license texts if requested
    license_texts = []
    if args.with_licenses and found_licenses:
        script_dir = Path(__file__).parent.absolute()
        for license_type in sorted(found_licenses):
            license_components = SpdxExtractor._parse_license_components(license_type)
            for component in license_components:
                if not any(lt.license_id == component for lt in license_texts):
                    text = get_license_text(component, script_dir)
                    license_texts.append(LicenseText(license_id=component, text=text))

    # Write output
    @contextlib.contextmanager
    def output_context(output_file):
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                yield f
        else:
            yield sys.stdout

    with output_context(args.output) as out:
        print("=" * 80, file=out)
        print("Non-NVIDIA Third-Party Licenses for specific files", file=out)
        print("=" * 80, file=out)
        print(file=out)
        print("Files are listed with their associated licenses and copyright holders.", file=out)
        print(file=out)

        for entry in spdx_entries:
            entry.write(out)

        if license_texts:
            print(file=out)
            print("=" * 80, file=out)
            print("FULL LICENSE TEXTS", file=out)
            print("=" * 80, file=out)
            print(file=out)

            for license_text in license_texts:
                license_text.write(out)


def _run_copy_command(args) -> None:
    """Run the copy command using OOP classes."""
    import contextlib
    from pathlib import Path

    from .extractors import DependencyLicenseExtractor
    from .license_records import DependencyLicense
    from .utility import get_project_relative_path

    project_paths = [Path(p) for p in args.project_path]

    print(f"Project path(s): {', '.join(str(p) for p in project_paths)}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    if args.output:
        print(f"Writing output to: {args.output}", file=sys.stderr)

    # Extract using OOP
    extractor = DependencyLicenseExtractor(
        project_paths,
        verbose=True,
        deduplicate_rapids=args.deduplicate_rapids,
        deduplicate_hierarchical=args.deduplicate_hierarchical,
        normalize_years=args.normalize_years,
    )

    content_map = extractor.extract()

    if not content_map:
        print("No LICENSE files found.", file=sys.stderr)
        return

    # Build dependency licenses
    dependency_licenses = []
    sorted_items = sorted(content_map.items(), key=lambda x: sorted(x[1]["filenames"])[0])

    for _content_hash, file_info in sorted_items:
        file_paths_dict = file_info["paths"]
        license_content = file_info["content"]

        locations = {}
        for full_path, rel_path in file_paths_dict.items():
            matching_root = None
            for proj_path in project_paths:
                if full_path.startswith(str(proj_path)):
                    matching_root = str(proj_path)
                    break

            project_name, _ = get_project_relative_path(full_path, project_root=matching_root)
            project_key = project_name if project_name else "unknown"
            if project_key not in locations:
                locations[project_key] = set()
            locations[project_key].add(rel_path)

        dependency_licenses.append(DependencyLicense(locations=locations, content=license_content))

    # Write output
    @contextlib.contextmanager
    def output_context(output_file):
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                yield f
        else:
            yield sys.stdout

    with output_context(args.output) as out:
        for dep_license in dependency_licenses:
            dep_license.write(out)


def _run_all_command(args) -> None:
    """
    Run combined extract and copy operations.

    Builds a complete license report combining SPDX copyright entries
    and LICENSE files from dependencies.
    """
    import contextlib
    from pathlib import Path
    from typing import Iterator, TextIO

    from .extractors import LicenseReportBuilder

    @contextlib.contextmanager
    def output_context(output_file: str | None) -> Iterator[TextIO]:
        """Context manager for writing to file or stdout."""
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                yield f
        else:
            yield sys.stdout

    # Convert string paths to Path objects
    validated_paths = [Path(p) for p in args.project_path]

    if args.output:
        print(f"Writing output to: {args.output}", file=sys.stderr)

    # Build the license report
    builder = LicenseReportBuilder(
        project_paths=validated_paths,
        with_licenses=args.with_licenses,
        deduplicate_rapids=args.deduplicate_rapids,
        deduplicate_hierarchical=args.deduplicate_hierarchical,
        normalize_years=args.normalize_years,
        verbose=True,
    )

    report = builder.build()

    # Write the report
    with output_context(args.output) as out:
        report.write(out)


if __name__ == "__main__":
    main()
