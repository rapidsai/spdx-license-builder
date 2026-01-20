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

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, TextIO, Tuple


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

    def write(self, out: TextIO) -> None:
        """Write this unified license entry to output."""
        print("=" * 80, file=out)
        print(f"License: {self.license_id}", file=out)
        print("=" * 80, file=out)
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

            # Display grouped by copyright
            for copyright_key, file_paths in sorted(copyright_to_files.items()):
                # Show copyright first
                if copyright_key:
                    for year_range, owner in copyright_key:
                        if year_range:
                            print(f"  Copyright (c) {year_range}, {owner}", file=out)
                        else:
                            print(f"  Copyright (c) {owner}", file=out)

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

            # Display grouped by copyright
            for copyright_key, file_list in sorted(copyright_groups.items()):
                # Display copyright headers first
                if copyright_key:
                    for year_range, owner in copyright_key:
                        if year_range:
                            print(f"  Copyright (c) {year_range}, {owner}", file=out)
                        else:
                            print(f"  Copyright (c) {owner}", file=out)

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

    def write(self, out: TextIO) -> None:
        """Write the complete license report to output."""
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
                entry.write(out)
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
