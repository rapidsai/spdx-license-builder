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

from . import __version__


def main():
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
  license-builder copy /path/to/project --deduplicate-rapids --handle-cccl

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
        help="Deduplicate licenses from known RAPIDS/NVIDIA projects",
    )
    copy_parser.add_argument(
        "--handle-cccl",
        action="store_true",
        help="Special handling for CCCL component licenses (skip components if root exists)",
    )
    copy_parser.add_argument(
        "--normalize-years",
        action="store_true",
        help="Normalize copyright years for better deduplication",
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
        default=True,
        help="Deduplicate licenses from known RAPIDS/NVIDIA projects (default: enabled)",
    )
    all_parser.add_argument(
        "--no-deduplicate-rapids",
        action="store_false",
        dest="deduplicate_rapids",
        help="Disable RAPIDS license deduplication",
    )
    all_parser.add_argument(
        "--handle-cccl",
        action="store_true",
        default=True,
        help="Special handling for CCCL component licenses (default: enabled)",
    )
    all_parser.add_argument(
        "--no-handle-cccl",
        action="store_false",
        dest="handle_cccl",
        help="Disable CCCL special handling",
    )
    all_parser.add_argument(
        "--normalize-years",
        action="store_true",
        default=True,
        help="Normalize copyright years for better deduplication (default: enabled)",
    )
    all_parser.add_argument(
        "--no-normalize-years",
        action="store_false",
        dest="normalize_years",
        help="Disable year normalization",
    )

    # Parse arguments
    args = parser.parse_args()

    # Route to appropriate command
    if args.command == "extract":
        from .extract_licenses_via_spdx import main as extract_main

        # Replace sys.argv to pass arguments to the subcommand
        sys.argv = ["extract-licenses-via-spdx"] + args.project_path
        if args.with_licenses:
            sys.argv.append("--with-licenses")
        if args.output:
            sys.argv.extend(["--output", args.output])
        extract_main()

    elif args.command == "copy":
        from .find_and_copy_license_files import main as copy_main

        # Replace sys.argv to pass arguments to the subcommand
        sys.argv = ["find-and-copy-license-files"] + args.project_path
        if args.output:
            sys.argv.extend(["--output", args.output])
        if args.deduplicate_rapids:
            sys.argv.append("--deduplicate-rapids")
        if args.handle_cccl:
            sys.argv.append("--handle-cccl")
        if args.normalize_years:
            sys.argv.append("--normalize-years")
        copy_main()

    elif args.command == "all":
        from .combined import run_combined

        run_combined(
            project_paths=args.project_path,
            with_licenses=args.with_licenses,
            output_file=args.output,
            deduplicate_rapids=args.deduplicate_rapids,
            handle_cccl=args.handle_cccl,
            normalize_years=args.normalize_years,
        )

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
