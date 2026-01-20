#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Command-line interface for SPDX License Builder.

Extracts license information from projects by:
  - Scanning source files for SPDX copyright headers
  - Finding LICENSE files in dependencies

By default, runs both modes. Use --no-extract or --no-copy to disable one.
"""

import argparse
import sys
from pathlib import Path
from typing import NoReturn

from . import __version__


def main() -> NoReturn:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="license-builder",
        description="Extract and manage license information from projects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract all license info (default: both SPDX and LICENSE files)
  license-builder /path/to/project --output LICENSE

  # Extract SPDX entries only
  license-builder /path/to/project --no-copy

  # Extract LICENSE files only
  license-builder /path/to/project --no-extract

  # Multiple projects with deduplication
  license-builder /path/to/project1 /path/to/project2 \\
    --deduplicate-rapids --output LICENSE
""",
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    # Project paths (required)
    parser.add_argument(
        "project_path",
        type=str,
        nargs="+",
        help="Path(s) to project directory/directories to scan",
    )

    # Mode control flags
    parser.add_argument(
        "--no-extract",
        action="store_true",
        help="Skip SPDX copyright extraction (only find LICENSE files)",
    )
    parser.add_argument(
        "--no-copy",
        action="store_true",
        help="Skip LICENSE file extraction (only extract SPDX entries)",
    )

    # Output options
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Write output to file instead of stdout",
    )
    parser.add_argument(
        "--no-license-text",
        action="store_true",
        help="Exclude full license text for SPDX entries (enabled by default)",
    )

    # Deduplication options
    parser.add_argument(
        "--deduplicate-rapids",
        action="store_true",
        help="[RISKY] Deduplicate RAPIDS project licenses (may lose individual project attribution)",
    )
    parser.add_argument(
        "--deduplicate-hierarchical",
        action="store_true",
        help="[RISKY] Prefer parent licenses over child licenses when content is identical (may lose subdirectory provenance)",
    )
    parser.add_argument(
        "--no-normalize-years",
        action="store_true",
        help="Disable copyright year normalization (by default, year ranges are normalized for deduplication)",
    )

    args = parser.parse_args()

    # Validate that at least one mode is enabled
    if args.no_extract and args.no_copy:
        parser.error("Cannot use both --no-extract and --no-copy (nothing to do)")

    # Run the license extraction
    try:
        _run_license_builder(args)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _run_license_builder(args) -> None:
    """Run the license builder with given arguments."""
    from .extractors import LicenseReportBuilder
    from .license_records import LicenseReport

    project_paths = [Path(p) for p in args.project_path]

    print(f"Project path(s): {', '.join(str(p) for p in project_paths)}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    if args.output:
        print(f"Writing output to: {args.output}", file=sys.stderr)

    # Determine which modes to run
    run_extract = not args.no_extract
    run_copy = not args.no_copy

    if run_extract and run_copy:
        print("Mode: Extracting SPDX entries + LICENSE files", file=sys.stderr)
    elif run_extract:
        print("Mode: Extracting SPDX entries only (--no-copy)", file=sys.stderr)
    else:
        print("Mode: Extracting LICENSE files only (--no-extract)", file=sys.stderr)

    # Build the report using LicenseReportBuilder
    builder = LicenseReportBuilder(
        project_paths=project_paths,
        with_licenses=not args.no_license_text,  # Enabled by default
        deduplicate_rapids=args.deduplicate_rapids,
        deduplicate_hierarchical=args.deduplicate_hierarchical,
        normalize_years=not args.no_normalize_years,  # Enabled by default
        verbose=True,
    )

    report = builder.build()

    # Filter report based on mode
    if args.no_extract:
        # Only dependency licenses
        filtered_report = LicenseReport(
            spdx_entries=[],
            license_texts=[],
            dependency_licenses=report.dependency_licenses,
        )
    elif args.no_copy:
        # Only SPDX entries
        filtered_report = LicenseReport(
            spdx_entries=report.spdx_entries,
            license_texts=report.license_texts,
            dependency_licenses=[],
        )
    else:
        # Both (default)
        filtered_report = report

    # Write output
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            filtered_report.write(f)
    else:
        filtered_report.write(sys.stdout)


if __name__ == "__main__":
    main()
