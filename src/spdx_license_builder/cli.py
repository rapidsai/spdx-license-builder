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
  # Extract all license info (SPDX headers + LICENSE files)
  license-builder /path/to/project --output-json licenses.json --output-txt LICENSE.txt

  # Multiple projects
  license-builder /path/to/project1 /path/to/project2 --output-json licenses.json

  # Exclude additional directories (adds to defaults)
  license-builder /path/to/project --exclude-dirs build _skbuild

  # Clear cache and rescan
  license-builder /path/to/project --clear-cache --output-json licenses.json
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

    # Output options
    parser.add_argument(
        "--output-json",
        type=str,
        default=None,
        help="Output file for machine-friendly JSON format (all licenses explicitly listed)",
    )
    parser.add_argument(
        "--output-txt",
        type=str,
        default=None,
        help="Output file for user-friendly text format (NVIDIA header + third-party licenses)",
    )

    # Exclusion options
    parser.add_argument(
        "--exclude-dirs",
        type=str,
        nargs="+",
        default=None,
        help="Additional directories to exclude (adds to default exclusions: .git, .github, dist, _build, node_modules, venv, .venv)",
    )

    # Performance options
    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Disable parallel processing (enabled by default, auto-disabled in debugger)",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Maximum number of worker threads for parallel processing (default: number of CPUs)",
    )

    # Validation options
    parser.add_argument(
        "--enable-validation",
        action="store_true",
        help="Enable license validation warnings (experimental, disabled by default)",
    )

    # Cache options
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching (slower but ensures fresh scan)",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear cache before running",
    )

    args = parser.parse_args()

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

    project_paths = [Path(p) for p in args.project_path]

    print(f"Project path(s): {', '.join(str(p) for p in project_paths)}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # Build the report using LicenseReportBuilder
    additional_exclude_dirs = tuple(args.exclude_dirs) if args.exclude_dirs else None

    # Determine parallel mode: None = auto-detect, False = explicitly disabled
    parallel = None if not args.no_parallel else False

    # Handle cache options
    use_cache = not args.no_cache
    if args.clear_cache:
        from .cache import ExtractionCache

        cache = ExtractionCache()
        cache.clear()
        print("Cache cleared.", file=sys.stderr)

    builder = LicenseReportBuilder(
        project_paths=project_paths,
        additional_exclude_dirs=additional_exclude_dirs,
        verbose=True,
        parallel=parallel,
        max_workers=args.max_workers,
        enable_validation=args.enable_validation,
        use_cache=use_cache,
    )

    report = builder.build()

    # Handle output flags
    output_json_file = args.output_json
    output_txt_file = args.output_txt

    # Write output(s)
    # Machine-friendly format is ALWAYS JSON
    if output_json_file:
        json_output = report.to_json(indent=2)
        with open(output_json_file, "w", encoding="utf-8") as f:
            f.write(json_output)
        print(f"Machine-friendly JSON output written to: {output_json_file}", file=sys.stderr)

    # User-friendly format (NVIDIA header + third-party) is text
    if output_txt_file:
        with open(output_txt_file, "w", encoding="utf-8") as f:
            report.write_user_friendly(f)
        print(f"User-friendly text output written to: {output_txt_file}", file=sys.stderr)

    # If neither output specified, print to stdout (user-friendly format)
    if not output_json_file and not output_txt_file:
        # Default to user-friendly format (NVIDIA header + filtered third-party)
        report.write_user_friendly(sys.stdout)


if __name__ == "__main__":
    main()
