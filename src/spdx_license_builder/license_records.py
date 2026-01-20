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
class LicenseReport:
    """Complete license report combining SPDX entries and dependency licenses."""

    spdx_entries: List[SpdxEntry] = field(default_factory=list)
    license_texts: List[LicenseText] = field(default_factory=list)
    dependency_licenses: List[DependencyLicense] = field(default_factory=list)

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
        if not self.spdx_entries and not self.dependency_licenses:
            print("No third-party licenses found.", file=out)
            print(file=out)
