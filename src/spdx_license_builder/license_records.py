#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Data classes for representing license records.

Provides clean separation of data and formatting logic.

This module contains all data structures used throughout the license extraction process:
- CopyrightInfo: Base copyright information from SPDX headers
- SpdxCopyright: Copyright info with file location
- SpdxEntry: Aggregated SPDX entries for reporting
- LicenseText: Full license text for display
- DependencyLicense: LICENSE file from dependencies
- LicenseReport: Complete combined report
"""

import contextlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, TextIO, Tuple


@dataclass(frozen=True)
class CopyrightInfo:
    """
    Copyright license information extracted from SPDX headers.

    Frozen dataclass that can be used in sets for deduplication.

    Attributes:
        license_type: SPDX license identifier (e.g., "Apache-2.0", "MIT")
        year_range: Copyright year or year range (e.g., "2014-2022", "2019")
        owner: Copyright owner name (e.g., "Facebook, Inc.")
    """

    license_type: str
    year_range: str
    owner: str


@dataclass(frozen=True)
class SpdxCopyright(CopyrightInfo):
    """
    Individual SPDX copyright entry from a source file.

    Extends CopyrightInfo with file location context. Frozen dataclass representing
    a single copyright declaration found in source code.

    Attributes:
        license_type: SPDX license identifier (inherited from CopyrightInfo)
        year_range: Copyright year or year range (inherited from CopyrightInfo)
        owner: Copyright owner name (inherited from CopyrightInfo)
        file_path: Path to the file containing this SPDX entry
    """

    file_path: str


@dataclass
class SpdxEntry:
    """Represents a third-party code entry found via SPDX headers in source files."""

    filename: str
    locations: Dict[str, Set[str]]  # project_name -> set of relative paths
    licenses: Dict[str, List[Tuple[str, str]]]  # license_type -> list of (year_range, owner)

    def write(self, out: TextIO) -> None:
        """Write this SPDX entry to output."""
        print("-" * 80, file=out)
        print(f"File: {self.filename}", file=out)
        print("-" * 80, file=out)
        print(file=out)

        # Display file locations
        print("  Locations:", file=out)
        for project in sorted(self.locations.keys()):
            for rel_path in sorted(self.locations[project]):
                print(f"    {project}: {rel_path}", file=out)
        print(file=out)

        # Display licenses and copyrights
        for license_type in sorted(self.licenses.keys()):
            print(f"  License: {license_type}", file=out)
            print(file=out)
            for year_range, owner in sorted(self.licenses[license_type]):
                if year_range:
                    print(f"    Copyright (c) {year_range}, {owner}", file=out)
                else:
                    print(f"    Copyright (c) {owner}", file=out)
            print(file=out)


@dataclass
class LicenseText:
    """Represents a full license text to be displayed."""

    license_id: str
    text: Optional[str]

    def write(self, out: TextIO) -> None:
        """Write this license text to output."""
        print("-" * 80, file=out)
        print(f"License: {self.license_id}", file=out)
        print("-" * 80, file=out)
        print(file=out)

        if self.text:
            for line in self.text.splitlines():
                print(line, file=out)
        else:
            print(f"License text for {self.license_id} not available.", file=out)

        print(file=out)
        print(file=out)


@dataclass
class DependencyLicense:
    """Represents a LICENSE file from a dependency."""

    locations: Dict[str, Set[str]]  # project_name -> set of relative paths
    content: str

    def write(self, out: TextIO) -> None:
        """Write this dependency license to output."""
        print("-" * 80, file=out)
        print("  Locations:", file=out)

        for project in sorted(self.locations.keys()):
            for rel_path in sorted(self.locations[project]):
                print(f"    {project}: {rel_path}", file=out)
        print(file=out)

        # Output the license content
        if self.content:
            print("  License Text:", file=out)
            print(file=out)
            for line in self.content.splitlines():
                print(f"    {line}", file=out)
            print(file=out)
        else:
            print("  (License text could not be read)", file=out)
            print(file=out)

        print("-" * 80, file=out)
        print(file=out)


@dataclass
class UnifiedLicenseEntry:
    """
    Unified license entry grouping all sources for a specific license.

    Groups both SPDX-tagged files and LICENSE files by license identifier,
    showing all sources together with the full license text.

    Attributes:
        license_id: License identifier (e.g., "Apache-2.0", "MIT", "Apache-2.0 AND MIT")
        spdx_files: Dict of {filename: {project: [paths], copyrights: [(year, owner)]}}
        license_files: Dict of {project: [paths]} for standalone LICENSE files
        license_file_copyrights: Dict mapping file_path -> List[(year, owner)] for LICENSE files
        license_text: Full text of the license
        in_project_license: Whether this license is found in the project's main LICENSE file
        validation_warnings: List of validation warnings for this license
    """

    license_id: str
    spdx_files: Dict[str, Dict] = field(
        default_factory=dict
    )  # filename -> {project: paths, copyrights: [(year, owner)]}
    license_files: Dict[str, Set[str]] = field(default_factory=dict)  # project -> set of paths
    license_file_copyrights: Dict[str, List[Tuple[str, str]]] = field(
        default_factory=dict
    )  # path -> [(year, owner)]
    license_text: Optional[str] = None
    in_project_license: Optional[bool] = None  # None = not checked, True = found, False = missing
    validation_warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        # Convert spdx_files to have separate copyright and file paths
        spdx_files_json = []
        for filename, file_info in self.spdx_files.items():
            locations = file_info.get("locations", {})
            copyrights = file_info.get("copyrights", [])

            # Flatten locations into list of {project, path} dicts
            file_paths = []
            for project in sorted(locations.keys()):
                for path in sorted(locations[project]):
                    file_paths.append({"project": project, "path": path})

            # Convert copyrights to list of dicts
            copyright_list = [
                {"year_range": year_range, "owner": owner} for year_range, owner in copyrights
            ]

            spdx_files_json.append(
                {"filename": filename, "paths": file_paths, "copyrights": copyright_list}
            )

        # Convert license_files to list format
        license_files_json = []
        for project in sorted(self.license_files.keys()):
            for path in sorted(self.license_files[project]):
                # Get copyrights for this specific file
                copyrights = self.license_file_copyrights.get(path, [])
                copyright_list = [
                    {"year_range": year_range, "owner": owner} for year_range, owner in copyrights
                ]

                license_files_json.append(
                    {"project": project, "path": path, "copyrights": copyright_list}
                )

        return {
            "license_id": self.license_id,
            "spdx_files": spdx_files_json,
            "license_files": license_files_json,
            "license_text": self.license_text,
            "in_project_license": self.in_project_license,
            "validation_warnings": self.validation_warnings,
        }

    def write(self, out: TextIO, show_validation: bool = False) -> None:
        """
        Write this unified license entry to output.

        Args:
            out: Output stream to write to
            show_validation: Whether to include validation status (default: False for file output)
        """
        print("=" * 80, file=out)
        print(f"License: {self.license_id}", file=out)
        print("=" * 80, file=out)
        print(file=out)

        # Show validation status if checked (optional, typically for terminal output)
        if show_validation and self.in_project_license is not None:
            if self.in_project_license:
                print("  [✓] License found in project LICENSE file", file=out)
            else:
                print("  [⚠] WARNING: License NOT found in project LICENSE file", file=out)
            print(file=out)

        # Show any validation warnings
        if show_validation and self.validation_warnings:
            for warning in self.validation_warnings:
                print(f"  [⚠] {warning}", file=out)
            print(file=out)

        has_content = False

        # Section 1: SPDX-tagged source files
        if self.spdx_files:
            has_content = True
            print("Files with SPDX headers:", file=out)
            print(file=out)

            # Group files by their copyright
            copyright_to_files = {}
            for filename in self.spdx_files:
                file_info = self.spdx_files[filename]
                copyrights = file_info.get("copyrights", [])
                locations = file_info.get("locations", {})

                # Use copyright tuple as key
                copyright_key = tuple(sorted(copyrights)) if copyrights else ()

                if copyright_key not in copyright_to_files:
                    copyright_to_files[copyright_key] = []

                # Store all locations for this file
                for project in sorted(locations.keys()):
                    for path in sorted(locations[project]):
                        copyright_to_files[copyright_key].append((project, path))

            # Display grouped by copyright, merging date ranges for same owner
            owner_to_copyrights = {}
            for copyright_key in copyright_to_files:
                if copyright_key:
                    for year_range, owner in copyright_key:
                        if owner not in owner_to_copyrights:
                            owner_to_copyrights[owner] = []
                        if year_range:
                            owner_to_copyrights[owner].append(year_range)

            for copyright_key, file_paths in sorted(copyright_to_files.items()):
                # Show copyright first (merge dates for same owner)
                if copyright_key:
                    displayed_owners = set()
                    for year_range, owner in copyright_key:
                        if owner not in displayed_owners:
                            from .utility import merge_date_ranges

                            merged_dates = merge_date_ranges(
                                owner_to_copyrights.get(owner, [year_range])
                            )
                            if merged_dates:
                                print(f"  Copyright (c) {merged_dates}, {owner}", file=out)
                            else:
                                print(f"  Copyright (c) {owner}", file=out)
                            displayed_owners.add(owner)

                # Show all file paths under this copyright
                for project, path in sorted(file_paths):
                    print(f"    {project}: {path}", file=out)
                print(file=out)

        # Section 2: LICENSE files
        if self.license_files:
            has_content = True
            print("LICENSE files:", file=out)
            print(file=out)

            # Group files by their copyright info
            # Build a mapping: copyright_tuple -> list of (project, path)
            copyright_groups = {}

            for project in sorted(self.license_files.keys()):
                for path in sorted(self.license_files[project]):
                    # Get copyright for this file (if available)
                    copyrights = self.license_file_copyrights.get(path, [])
                    copyright_key = tuple(copyrights) if copyrights else ()

                    if copyright_key not in copyright_groups:
                        copyright_groups[copyright_key] = []
                    copyright_groups[copyright_key].append((project, path))

            # Group and merge date ranges by owner
            owner_to_dates = {}
            for copyright_key in copyright_groups:
                if copyright_key:
                    for year_range, owner in copyright_key:
                        if owner not in owner_to_dates:
                            owner_to_dates[owner] = []
                        if year_range:
                            owner_to_dates[owner].append(year_range)

            # Display grouped by copyright
            for copyright_key, file_list in sorted(copyright_groups.items()):
                # Display copyright headers first (merge dates for same owner)
                if copyright_key:
                    displayed_owners = set()
                    for year_range, owner in copyright_key:
                        if owner not in displayed_owners:
                            from .utility import merge_date_ranges

                            merged_dates = merge_date_ranges(
                                owner_to_dates.get(owner, [year_range])
                            )
                            if merged_dates:
                                print(f"  Copyright (c) {merged_dates}, {owner}", file=out)
                            else:
                                print(f"  Copyright (c) {owner}", file=out)
                            displayed_owners.add(owner)

                # Display files under this copyright
                for project, path in sorted(file_list):
                    print(f"    {project}: {path}", file=out)
                print(file=out)

        # Section 3: Full license text
        if self.license_text:
            print("Full License Text:", file=out)
            print(file=out)
            for line in self.license_text.splitlines():
                print(f"  {line}", file=out)
            print(file=out)
        else:
            print(f"(Full license text for {self.license_id} not available)", file=out)
            print(file=out)

        if not has_content:
            print("(No files found for this license)", file=out)
            print(file=out)


@dataclass
class LicenseReport:
    """Complete license report combining SPDX entries and dependency licenses."""

    spdx_entries: List[SpdxEntry] = field(default_factory=list)
    license_texts: List[LicenseText] = field(default_factory=list)
    dependency_licenses: List[DependencyLicense] = field(default_factory=list)
    unified_entries: List[UnifiedLicenseEntry] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "licenses": [entry.to_dict() for entry in self.unified_entries],
            "summary": {
                "total_licenses": len(self.unified_entries),
                "license_ids": [entry.license_id for entry in self.unified_entries],
            },
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def write(self, out: TextIO, show_validation: bool = False) -> None:
        """
        Write the complete license report to output (machine-friendly format).

        Args:
            out: Output stream to write to
            show_validation: Whether to include validation status
        """
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

        # Use unified format if available
        if self.unified_entries:
            print(
                "The following licenses were found in source files (SPDX headers) and/or LICENSE files.",
                file=out,
            )
            print(file=out)

            for entry in self.unified_entries:
                entry.write(out, show_validation=show_validation)
            return

        # Fallback to old two-section format
        # Section 1: SPDX Copyright Entries
        if self.spdx_entries:
            print("=" * 80, file=out)
            print("SECTION 1: Third-Party Code in Source Files (SPDX Entries)", file=out)
            print("=" * 80, file=out)
            print(file=out)
            print(
                "The following files contain third-party code with SPDX copyright headers.",
                file=out,
            )
            print(file=out)

            for entry in self.spdx_entries:
                entry.write(out)

            # Full license texts
            if self.license_texts:
                print("=" * 80, file=out)
                print("Full License Texts for SPDX Entries", file=out)
                print("=" * 80, file=out)
                print(file=out)

                for license_text in self.license_texts:
                    license_text.write(out)

        # Section 2: Dependency LICENSE Files
        if self.dependency_licenses:
            print("=" * 80, file=out)
            print("SECTION 2: Dependency LICENSE Files", file=out)
            print("=" * 80, file=out)
            print(file=out)
            print("The following LICENSE files were found in dependency directories.", file=out)
            print(file=out)

            for dep_license in self.dependency_licenses:
                dep_license.write(out)

        # Final message
        if not self.spdx_entries and not self.dependency_licenses and not self.unified_entries:
            print("No third-party licenses found.", file=out)
            print(file=out)

    def write_user_friendly(self, out: TextIO, nvidia_license_text: Optional[str] = None) -> None:
        """
        Write user-friendly license report with NVIDIA header + third-party licenses.

        This format:
        1. Starts with NVIDIA Apache-2.0 license and copyright
        2. Adds separator
        3. Lists third-party licenses (with NVIDIA copyrights filtered out)

        Args:
            out: Output stream to write to
            nvidia_license_text: Optional Apache-2.0 license text (will be fetched if not provided)
        """
        from datetime import datetime

        from .utility import get_license_text

        # Collect all NVIDIA copyright date ranges to compute full range
        nvidia_years = set()
        for entry in self.unified_entries:
            # Check SPDX files
            for filename in entry.spdx_files:
                file_info = entry.spdx_files[filename]
                copyrights = file_info.get("copyrights", [])
                for year_range, owner in copyrights:
                    # Parse year range (e.g., "2020-2024" or "2023")
                    if "NVIDIA" in owner.upper() and year_range:
                        years_str = year_range.replace(" ", "")
                        if "-" in years_str:
                            start, end = years_str.split("-", 1)
                            try:
                                nvidia_years.add(int(start))
                                nvidia_years.add(int(end))
                            except ValueError:
                                pass
                        else:
                            with contextlib.suppress(ValueError):
                                nvidia_years.add(int(years_str))

            # Check LICENSE files
            for path in entry.license_file_copyrights:
                copyrights = entry.license_file_copyrights[path]
                for year_range, owner in copyrights:
                    if "NVIDIA" in owner.upper() and year_range:
                        years_str = year_range.replace(" ", "")
                        if "-" in years_str:
                            start, end = years_str.split("-", 1)
                            try:
                                nvidia_years.add(int(start))
                                nvidia_years.add(int(end))
                            except ValueError:
                                pass
                        else:
                            with contextlib.suppress(ValueError):
                                nvidia_years.add(int(years_str))

        # Determine copyright date range
        current_year = datetime.now().year
        if nvidia_years:
            min_year = min(nvidia_years)
            max_year = max(max(nvidia_years), current_year)
            copyright_range = f"{min_year}-{max_year}" if min_year < max_year else str(min_year)
        else:
            # Fallback to current year if no NVIDIA copyrights found
            copyright_range = str(current_year)

        # Header
        print("=" * 80, file=out)
        print("SOFTWARE LICENSES", file=out)
        print("=" * 80, file=out)
        print(file=out)

        # NVIDIA Section
        print("=" * 80, file=out)
        print("License: Apache-2.0 (NVIDIA Code)", file=out)
        print("=" * 80, file=out)
        print(file=out)

        print(
            f"Copyright (c) {copyright_range}, NVIDIA CORPORATION & AFFILIATES. All rights reserved.",
            file=out,
        )
        print(file=out)

        print("Full License Text:", file=out)
        print(file=out)

        # Get Apache-2.0 license text
        if nvidia_license_text is None:
            from pathlib import Path

            nvidia_license_text = get_license_text("Apache-2.0", Path.cwd())

        if nvidia_license_text:
            for line in nvidia_license_text.splitlines():
                print(f"  {line}", file=out)
        else:
            print("  Apache License", file=out)
            print("  Version 2.0, January 2004", file=out)
            print("  http://www.apache.org/licenses/", file=out)
        print(file=out)

        # Separator for third-party licenses
        print("=" * 80, file=out)
        print("THIRD-PARTY SOFTWARE LICENSES", file=out)
        print("=" * 80, file=out)
        print(file=out)
        print(
            "The following third-party licenses were found in this project.",
            file=out,
        )
        print(file=out)

        # Filter out NVIDIA-only entries and write third-party licenses
        if self.unified_entries:
            for entry in self.unified_entries:
                # Check if this entry has any non-NVIDIA content
                has_non_nvidia = False

                # Check SPDX files
                if entry.spdx_files:
                    for file_info in entry.spdx_files.values():
                        copyrights = file_info.get("copyrights", [])
                        if any("NVIDIA" not in owner.upper() for _, owner in copyrights):
                            has_non_nvidia = True
                            break

                # Check LICENSE files
                if not has_non_nvidia and entry.license_files:
                    for copyrights in entry.license_file_copyrights.values():
                        if any("NVIDIA" not in owner.upper() for _, owner in copyrights):
                            has_non_nvidia = True
                            break

                # Only write entries that have non-NVIDIA content
                if has_non_nvidia:
                    # Create a filtered version of the entry
                    filtered_entry = self._filter_nvidia_from_entry(entry)
                    filtered_entry.write(out, show_validation=False)

        if not self.unified_entries:
            print("No third-party licenses found.", file=out)
            print(file=out)

    @staticmethod
    def _filter_nvidia_from_entry(entry: UnifiedLicenseEntry) -> UnifiedLicenseEntry:
        """Create a copy of entry with NVIDIA copyrights filtered out."""

        filtered = UnifiedLicenseEntry(
            license_id=entry.license_id,
            license_text=entry.license_text,
            in_project_license=entry.in_project_license,
            validation_warnings=entry.validation_warnings,
        )

        # Filter SPDX files
        for filename, file_info in entry.spdx_files.items():
            copyrights = file_info.get("copyrights", [])
            locations = file_info.get("locations", {})

            # Keep only non-NVIDIA copyrights
            filtered_copyrights = [
                (year, owner) for year, owner in copyrights if "NVIDIA" not in owner.upper()
            ]

            if filtered_copyrights:
                filtered.spdx_files[filename] = {
                    "locations": locations,
                    "copyrights": filtered_copyrights,
                }

        # Filter LICENSE files
        for project, paths in entry.license_files.items():
            for path in paths:
                copyrights = entry.license_file_copyrights.get(path, [])
                filtered_copyrights = [
                    (year, owner) for year, owner in copyrights if "NVIDIA" not in owner.upper()
                ]

                if (
                    filtered_copyrights or not copyrights
                ):  # Include if no copyrights or has non-NVIDIA
                    if project not in filtered.license_files:
                        filtered.license_files[project] = set()
                    filtered.license_files[project].add(path)
                    if filtered_copyrights:
                        filtered.license_file_copyrights[path] = filtered_copyrights

        return filtered
