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

  # Multiple projects
  license-builder /path/to/project1 /path/to/project2 --output LICENSE

  # Exclude additional directories (adds to defaults)
  license-builder /path/to/project --exclude-dirs build _skbuild
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
    # Backward compatibility aliases
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Alias for --output-json (backward compatibility)",
    )
    parser.add_argument(
        "--output-user",
        type=str,
        default=None,
        help="Alias for --output-txt (backward compatibility)",
    )
    parser.add_argument(
        "--no-license-text",
        action="store_true",
        help="Exclude full license text for SPDX entries (enabled by default)",
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

    # Output format options
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format instead of text",
    )

    # Filtering options
    parser.add_argument(
        "--exclude-nvidia",
        action="store_true",
        help="Filter out NVIDIA copyrights from SPDX entries (default: include all)",
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
        with_licenses=not args.no_license_text,  # Enabled by default
        additional_exclude_dirs=additional_exclude_dirs,
        verbose=True,
        parallel=parallel,
        max_workers=args.max_workers,
        exclude_nvidia=args.exclude_nvidia,
        enable_validation=args.enable_validation,
        use_cache=use_cache,
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

    # Handle output flags (new flags take precedence over aliases)
    output_json_file = args.output_json or args.output
    output_txt_file = args.output_txt or args.output_user

    # Write output(s)
    # Machine-friendly format is ALWAYS JSON
    if output_json_file:
        json_output = filtered_report.to_json(indent=2)
        with open(output_json_file, "w", encoding="utf-8") as f:
            f.write(json_output)
        print(f"Machine-friendly JSON output written to: {output_json_file}", file=sys.stderr)

    # User-friendly format (NVIDIA header + third-party) is text
    if output_txt_file:
        with open(output_txt_file, "w", encoding="utf-8") as f:
            filtered_report.write_user_friendly(f)
        print(f"User-friendly text output written to: {output_txt_file}", file=sys.stderr)

    # If neither output specified, print to stdout
    if not output_json_file and not output_txt_file:
        if args.json:
            print(filtered_report.to_json(indent=2))
        else:
            # Default to user-friendly format (NVIDIA header + filtered third-party)
            filtered_report.write_user_friendly(sys.stdout)


if __name__ == "__main__":
    main()
