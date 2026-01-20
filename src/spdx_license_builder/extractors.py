#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Object-oriented interface for license extraction.

This module provides classes for extracting license information from projects:
- LicenseExtractor: Base class with common functionality
- SpdxExtractor: Extracts SPDX copyright entries from source files
- DependencyLicenseExtractor: Extracts LICENSE files from dependencies
- LicenseReportBuilder: Builds comprehensive license reports
"""

import hashlib
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .deduplication import group_licenses_with_deduplication
from .license_records import (
    CopyrightInfo,
    DependencyLicense,
    LicenseReport,
    LicenseText,
    SpdxCopyright,
    SpdxEntry,
    UnifiedLicenseEntry,
)
from .utility import get_license_text, get_project_relative_path, walk_directories_for_files

# Module-level constants for directory exclusions
# Using frozenset for O(1) membership testing
_BASE_EXCLUDED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".github",
        "build",
        "dist",
        "_build",
        "node_modules",
        "venv",
        ".venv",
    }
)

_SPDX_ADDITIONAL_EXCLUDES: frozenset[str] = frozenset(
    {
        "benchmark",
        "benchmarks",
        "cmake",
        "test",
        "tests",
        "docs",
        "examples",
    }
)

# Dependency extraction excludes language-specific dirs but NOT build (where deps are)
_DEPENDENCY_ADDITIONAL_EXCLUDES: frozenset[str] = _SPDX_ADDITIONAL_EXCLUDES | frozenset(
    {
        "python",
        "rust",
    }
)

# Common license file patterns to search for
_LICENSE_FILE_PATTERNS: List[str] = [
    "LICENSE",
    "COPYING",
    "COPYRIGHT",
    "NOTICE",
]


class LicenseExtractor:
    """Base class for license extraction with common functionality."""

    def __init__(
        self,
        project_paths: List[Path],
        directories_to_exclude: Optional[Tuple[str, ...]] = None,
        verbose: bool = True,
    ):
        """
        Initialize the license extractor.

        Args:
            project_paths: List of project paths to scan
            directories_to_exclude: Optional tuple of directory names to exclude
            verbose: Whether to print progress messages to stderr
        """
        self.project_paths = self._validate_paths(project_paths)
        self.directories_to_exclude = directories_to_exclude or self._default_excluded_dirs()
        self.verbose = verbose

    @staticmethod
    def _default_excluded_dirs() -> Tuple[str, ...]:
        """Return default directories to exclude from scanning."""
        return tuple(_BASE_EXCLUDED_DIRS)

    def _validate_paths(self, project_paths: List[Path]) -> List[Path]:
        """
        Validate that all project paths exist and are directories.

        Args:
            project_paths: List of paths to validate

        Returns:
            List of validated Path objects

        Raises:
            SystemExit: If any path is invalid
        """
        validated = []
        for path in project_paths:
            abs_path = path.absolute()
            if not abs_path.exists():
                print(f"Error: Project path '{abs_path}' does not exist", file=sys.stderr)
                sys.exit(1)
            if not abs_path.is_dir():
                print(f"Error: Project path '{abs_path}' is not a directory", file=sys.stderr)
                sys.exit(1)
            validated.append(abs_path)
        return validated

    def _log(self, message: str) -> None:
        """Log a message to stderr if verbose mode is enabled."""
        if self.verbose:
            print(message, file=sys.stderr)

    def _walk_with_exclusions(self, dir_path: str):
        """
        Walk directory tree, yielding (root, files) tuples while excluding specified directories.

        Moved from utility module to base class - both extractors need this.

        Args:
            dir_path: Base path to start walking from

        Yields:
            Tuple of (root_path, files_list) for each non-excluded directory
        """
        excluded = set(self.directories_to_exclude)

        for root, dirs, files in os.walk(dir_path, topdown=True):
            # Filter directories in-place to prune tree traversal
            dirs[:] = [d for d in dirs if d not in excluded]
            yield root, files

    def extract(self) -> Any:
        """
        Extract license information. To be implemented by subclasses.

        Returns:
            Extracted license data in format specific to subclass
        """
        raise NotImplementedError("Subclasses must implement extract()")


class SpdxExtractor(LicenseExtractor):
    """Extractor for SPDX copyright entries from source files."""

    def __init__(
        self,
        project_paths: List[Path],
        directories_to_exclude: Optional[Tuple[str, ...]] = None,
        verbose: bool = True,
    ):
        """Initialize SPDX extractor with instance state for results."""
        super().__init__(project_paths, directories_to_exclude, verbose)
        self.file_map = {}  # Store results on instance
        self.file_count = 0
        self.total_entries = 0

    @staticmethod
    def _default_excluded_dirs() -> Tuple[str, ...]:
        """Return directories to exclude for SPDX extraction (base + test/docs/examples)."""
        return tuple(_BASE_EXCLUDED_DIRS | _SPDX_ADDITIONAL_EXCLUDES)

    def extract(self) -> Dict[str, Dict[str, Any]]:
        """
        Extract SPDX copyright entries from source files.

        Returns:
            Dictionary mapping filename -> {'paths': set, 'licenses': set}
        """
        self._log("Extracting SPDX copyright entries from source files...")

        for project_path in self.project_paths:
            self._log(f"  Scanning directory: {project_path}")
            self._walk_directory(str(project_path))

        self._log(f"  Scanned {self.file_count} files")
        self._log(f"  Found {self.total_entries} non-NVIDIA copyright entries")
        self._log(f"  In {len(self.file_map)} unique files with third-party licenses")

        return self.file_map

    def _walk_directory(self, dir_path: str) -> None:
        """
        Walk through directory and collect all non-NVIDIA SPDX entries.

        Updates self.file_map, self.file_count, and self.total_entries.

        Args:
            dir_path: Directory path to scan
        """
        for root, files in self._walk_with_exclusions(dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                self._process_file(file_path)

    def _process_file(self, file_path: str) -> None:
        """
        Process a single file for SPDX entries.

        Updates self.file_map, self.file_count, and self.total_entries.

        Args:
            file_path: Path to file to process
        """
        self.file_count += 1
        entries = self._find_spdx_entries(file_path)
        self.total_entries += len(entries)

        # Organize entries by filename
        for entry in entries:
            filename = os.path.basename(entry.file_path)

            if filename not in self.file_map:
                self.file_map[filename] = {"paths": set(), "licenses": set()}

            # Store the file path and license info
            self.file_map[filename]["paths"].add(entry.file_path)
            self.file_map[filename]["licenses"].add(
                CopyrightInfo(entry.license_type, entry.year_range, entry.owner)
            )

    @staticmethod
    def _parse_license_components(license_type: str) -> List[str]:
        """
        Parse a license string and extract individual license components.

        Handles compound licenses like "Apache-2.0 AND MIT" or "MIT OR Apache-2.0".

        Args:
            license_type: The SPDX license identifier (may be compound)

        Returns:
            List of individual license identifiers
        """
        components = []
        # Split by AND/OR operators (case insensitive)
        parts = re.split(r"\s+(?:AND|OR|WITH)\s+", license_type, flags=re.IGNORECASE)
        for part in parts:
            part = part.strip()
            if part:
                components.append(part)
        return components if components else [license_type]

    @staticmethod
    def _extract_copyright_info(line: str) -> Optional[Tuple[str, str]]:
        """
        Extract year range and owner from a copyright line.

        Examples:
          "Copyright (c) 2014-2022 Frank Example" -> ("2014-2022", "Frank Example")
          "Copyright (2019) Sandia Corporation" -> ("2019", "Sandia Corporation")
          "Copyright (c) Facebook, Inc. and its affiliates." -> ("", "Facebook, Inc. and its affiliates")
        """
        # Define patterns: (regex, has_years, validate_years)
        patterns = [
            # Pattern 1: Copyright (c) <year> <owner> or Copyright (C) <year> <owner>
            (
                r"Copyright\s*\([cC]\)\s*([\d\-,\s]+)\s+(.+?)(?:\.\s*All rights reserved\.?)?$",
                True,
                False,
            ),
            # Pattern 2: Copyright (<year>) <owner> (no 'c')
            (r"Copyright\s*\(([\d\-,\s]+)\)\s+(.+?)(?:\.\s*All rights reserved\.?)?$", True, False),
            # Pattern 3: Copyright (c) <owner> (no year)
            (r"Copyright\s*\([cC]\)\s+(.+?)(?:\.\s*All rights reserved\.?)?$", False, False),
            # Pattern 4: Copyright <year> <owner> (no parentheses, needs validation)
            (r"Copyright\s+([\d\-,\s]+)\s+(.+?)(?:\.\s*All rights reserved\.?)?$", True, True),
        ]

        for pattern, has_years, validate_years in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                if has_years:
                    years = match.group(1).strip()
                    owner = match.group(2).strip()
                    # Validate years if needed (Pattern 4 requires this)
                    if validate_years and not re.match(r"^[\d\-,\s]+$", years):
                        continue
                else:
                    # No years in this pattern (Pattern 3)
                    years = ""
                    owner = match.group(1).strip()
                return (years, owner.rstrip(".,;"))
        return None

    def _find_spdx_entries(self, file_path: str) -> List[SpdxCopyright]:
        """
        Extract non-NVIDIA SPDX copyright entries from a file and associate them with licenses.

        Args:
            file_path: Path to the file to scan for SPDX entries

        Returns:
            List of SpdxCopyright objects containing license info and file path.
            Only includes non-NVIDIA copyrights.
        """
        entries = []

        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

                i = 0
                while i < len(lines):
                    line = lines[i].strip()

                    # Look for SPDX-FileCopyrightText
                    if "SPDX-FileCopyrightText:" in line:
                        # Check if it contains NVIDIA
                        if "NVIDIA" in line.upper():
                            i += 1
                            continue

                        # This is a non-NVIDIA copyright, start collecting
                        copyrights = []

                        # Extract copyright from current line
                        copyright_info = self._extract_copyright_info(line)
                        if copyright_info:
                            copyrights.append(copyright_info)

                        # Continue reading following lines for more SPDX-FileCopyrightText
                        i += 1
                        while i < len(lines):
                            next_line = lines[i].strip()

                            # If we hit a license identifier, associate it with all copyrights
                            if "SPDX-License-Identifier:" in next_line:
                                # Extract the license type
                                license_match = re.search(
                                    r"SPDX-License-Identifier:\s*(.+?)(?:\s*$)", next_line
                                )
                                if license_match:
                                    license_type = license_match.group(1).strip()
                                    # Clean up any trailing comment markers
                                    license_type = re.sub(r"[*/\s]+$", "", license_type)

                                    # Associate this license with all collected copyrights
                                    for year_range, owner in copyrights:
                                        entries.append(
                                            SpdxCopyright(
                                                license_type, year_range, owner, file_path
                                            )
                                        )
                                break

                            # If we hit another FileCopyrightText (non-NVIDIA), collect it
                            elif "SPDX-FileCopyrightText:" in next_line:
                                if "NVIDIA" not in next_line.upper():
                                    copyright_info = self._extract_copyright_info(next_line)
                                    if copyright_info:
                                        copyrights.append(copyright_info)
                                i += 1
                            else:
                                # Some other line, continue
                                i += 1
                                # Stop if we've gone too far without finding a license
                                if i - len(copyrights) > 10:
                                    break
                    else:
                        i += 1

        except (OSError, UnicodeDecodeError):
            # Skip files that can't be read
            pass
        except Exception as e:
            print(f"Unexpected error reading {file_path}: {e}", file=sys.stderr)
            raise

        return entries


class DependencyLicenseExtractor(LicenseExtractor):
    """Extractor for LICENSE files from project dependencies."""

    @staticmethod
    def _default_excluded_dirs() -> Tuple[str, ...]:
        """
        Return directories to exclude for dependency license extraction.

        Note: Includes language/test dirs but NOT 'build' (where dependencies are often located).
        """
        # Start with base exclusions but remove "build" since deps are often there
        base_without_build = _BASE_EXCLUDED_DIRS - {"build"}
        return tuple(base_without_build | _DEPENDENCY_ADDITIONAL_EXCLUDES)

    def __init__(
        self,
        project_paths: List[Path],
        directories_to_exclude: Optional[Tuple[str, ...]] = None,
        verbose: bool = True,
        deduplicate_rapids: bool = False,
        deduplicate_hierarchical: bool = False,
        normalize_years: bool = False,
    ):
        """
        Initialize the dependency license extractor.

        Args:
            project_paths: List of project paths to scan
            directories_to_exclude: Optional tuple of directory names to exclude
            verbose: Whether to print progress messages
            deduplicate_rapids: Enable RAPIDS license deduplication (default: False)
                               WARNING: May lose individual project attribution
            deduplicate_hierarchical: Prefer parent licenses over child licenses (default: False)
                                      WARNING: May lose subdirectory provenance information
            normalize_years: Enable copyright year normalization (default: False)
                            Normalizes year ranges (e.g., '2020-2023' vs '2022-2024')
                            while preserving copyright holder differences
        """
        super().__init__(project_paths, directories_to_exclude, verbose)
        self.deduplicate_rapids = deduplicate_rapids
        self.deduplicate_hierarchical = deduplicate_hierarchical
        self.normalize_years = normalize_years
        # Store results on instance
        self.content_map = {}
        self.total_files = 0

    def extract(self) -> Dict[str, Dict[str, Any]]:
        """
        Extract LICENSE files from project dependencies.

        Returns:
            Dictionary mapping content_hash -> {'content': str, 'filenames': set, 'paths': dict}
        """
        self._log("Extracting LICENSE files from dependencies...")

        for project_path in self.project_paths:
            self._process_project(project_path)

        self._log(f"  Found {self.total_files} total LICENSE files")
        self._log(f"  Found {len(self.content_map)} unique LICENSE contents")

        # Apply deduplication if requested
        if self.content_map:
            self.content_map = group_licenses_with_deduplication(
                self.content_map,
                use_year_normalization=self.normalize_years,
                deduplicate_rapids=self.deduplicate_rapids,
                deduplicate_hierarchical=self.deduplicate_hierarchical,
            )
            self._log(
                f"  After deduplication: {len(self.content_map)} unique licenses "
                f"(RAPIDS: {self.deduplicate_rapids}, Hierarchical: {self.deduplicate_hierarchical}, "
                f"Years: {self.normalize_years})"
            )

        return self.content_map

    def _process_project(self, project_path: Path) -> None:
        """
        Process a single project to find and extract LICENSE files.

        Searches for files matching common license file patterns (LICENSE, COPYING, etc.)
        including in build directories where dependencies are often located.

        Updates self.content_map and self.total_files.

        Args:
            project_path: Path to project to scan
        """
        self._log(f"  Scanning project: {project_path}")

        # Find all license files using common patterns
        matching_files = walk_directories_for_files(
            str(project_path), self.directories_to_exclude, _LICENSE_FILE_PATTERNS
        )

        self._log(f"  Found {len(matching_files)} license file(s)")
        self.total_files += len(matching_files)

        # Process each LICENSE file
        for file_path in matching_files:
            self._process_license_file(file_path, str(project_path))

    def _process_license_file(self, file_path: str, project_root: str) -> None:
        """
        Process a single LICENSE file.

        Updates self.content_map.

        Args:
            file_path: Path to LICENSE file
            project_root: Root path of the project
        """
        project_name, relative_path = get_project_relative_path(
            file_path, project_root=project_root
        )

        filename = os.path.basename(file_path)

        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Compute hash of content
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

            # Group by content hash
            if content_hash not in self.content_map:
                self.content_map[content_hash] = {
                    "content": content,
                    "filenames": set(),
                    "paths": {},
                }

            self.content_map[content_hash]["filenames"].add(filename)
            self.content_map[content_hash]["paths"][file_path] = relative_path

        except (OSError, UnicodeDecodeError) as e:
            self._log(f"Warning: Could not read {file_path}: {e}")
        except Exception as e:
            print(f"Unexpected error reading {file_path}: {e}", file=sys.stderr)
            raise


class LicenseReportBuilder:
    """Builder for creating comprehensive license reports."""

    def __init__(
        self,
        project_paths: List[Path],
        with_licenses: bool = True,
        deduplicate_rapids: bool = False,
        deduplicate_hierarchical: bool = False,
        normalize_years: bool = False,
        verbose: bool = True,
    ):
        """
        Initialize the license report builder.

        Args:
            project_paths: List of project paths to scan
            with_licenses: Include full license texts for SPDX entries
            deduplicate_rapids: Enable RAPIDS license deduplication (default: False)
                               WARNING: May lose individual project attribution
            deduplicate_hierarchical: Prefer parent licenses over child licenses (default: False)
                                      WARNING: May lose subdirectory provenance information
            normalize_years: Enable copyright year normalization (default: False)
                            Normalizes year ranges (e.g., '2020-2023' vs '2022-2024')
                            while preserving copyright holder differences
            verbose: Whether to print progress messages
        """
        self.project_paths = project_paths
        self.with_licenses = with_licenses
        self.deduplicate_rapids = deduplicate_rapids
        self.deduplicate_hierarchical = deduplicate_hierarchical
        self.normalize_years = normalize_years
        self.verbose = verbose

    def build(self) -> LicenseReport:
        """
        Build a comprehensive license report.

        Returns:
            LicenseReport containing SPDX entries and dependency licenses
        """
        if self.verbose:
            print("=" * 60, file=sys.stderr)
            print(
                f"Project path(s): {', '.join(str(p) for p in self.project_paths)}",
                file=sys.stderr,
            )
            print("=" * 60, file=sys.stderr)

        # Extract SPDX entries
        spdx_extractor = SpdxExtractor(self.project_paths, verbose=self.verbose)
        spdx_file_map = spdx_extractor.extract()

        # Extract dependency licenses
        dep_extractor = DependencyLicenseExtractor(
            self.project_paths,
            verbose=self.verbose,
            deduplicate_rapids=self.deduplicate_rapids,
            deduplicate_hierarchical=self.deduplicate_hierarchical,
            normalize_years=self.normalize_years,
        )
        dep_content_map = dep_extractor.extract()

        # Build unified entries (groups by license ID)
        unified_entries = self._build_unified_entries(spdx_file_map, dep_content_map)

        # Build SPDX entries (for backward compatibility)
        spdx_entries = self._build_spdx_entries(spdx_file_map)

        # Build license texts (if requested)
        license_texts = []
        if self.with_licenses:
            license_texts = self._build_license_texts(spdx_file_map)

        # Build dependency licenses (for backward compatibility)
        dependency_licenses = self._build_dependency_licenses(dep_content_map)

        if self.verbose:
            print("=" * 60, file=sys.stderr)

        return LicenseReport(
            spdx_entries=spdx_entries,
            license_texts=license_texts,
            dependency_licenses=dependency_licenses,
            unified_entries=unified_entries,
        )

    def _build_spdx_entries(self, file_map: Dict[str, Dict[str, Any]]) -> List[SpdxEntry]:
        """Build SPDX entry objects from file map."""
        spdx_entries = []

        for filename in sorted(file_map.keys()):
            file_info = file_map[filename]
            file_paths = file_info["paths"]
            license_copyright_set = file_info["licenses"]

            # Build location mapping
            locations = {}
            for fpath in file_paths:
                matching_root = None
                for proj_path in self.project_paths:
                    if fpath.startswith(str(proj_path)):
                        matching_root = str(proj_path)
                        break
                project_name, rel_path = get_project_relative_path(
                    fpath, project_root=matching_root
                )
                project_key = project_name if project_name else "unknown"
                if project_key not in locations:
                    locations[project_key] = set()
                locations[project_key].add(rel_path)

            # Build license mapping
            licenses_dict = {}
            for copyright_info in license_copyright_set:
                if copyright_info.license_type not in licenses_dict:
                    licenses_dict[copyright_info.license_type] = []
                licenses_dict[copyright_info.license_type].append(
                    (copyright_info.year_range, copyright_info.owner)
                )

            spdx_entries.append(
                SpdxEntry(filename=filename, locations=locations, licenses=licenses_dict)
            )

        return spdx_entries

    def _build_license_texts(self, file_map: Dict[str, Dict[str, Any]]) -> List[LicenseText]:
        """Build license text objects from file map."""
        license_texts = []
        found_licenses = set()

        # Collect all license types
        for file_info in file_map.values():
            for copyright_info in file_info["licenses"]:
                found_licenses.add(copyright_info.license_type)

        # Build license texts
        if found_licenses:
            base_path = Path(__file__).parent
            for license_type in sorted(found_licenses):
                # Parse compound licenses (e.g., "Apache-2.0 AND MIT")
                license_components = SpdxExtractor._parse_license_components(license_type)
                for component in license_components:
                    # Check if we already have this license
                    if not any(lt.license_id == component for lt in license_texts):
                        text = get_license_text(component, base_path)
                        license_texts.append(LicenseText(license_id=component, text=text))

        return license_texts

    def _build_unified_entries(
        self, spdx_file_map: Dict[str, Dict[str, Any]], dep_content_map: Dict[str, Dict[str, Any]]
    ) -> List[UnifiedLicenseEntry]:
        """
        Build unified license entries that group by license identifier.

        Args:
            spdx_file_map: Map of SPDX files and their licenses
            dep_content_map: Map of dependency LICENSE files

        Returns:
            List of UnifiedLicenseEntry objects grouped by license ID
        """
        # Dictionary to accumulate data: license_id -> UnifiedLicenseEntry data
        unified_map = {}

        # Step 1: Process SPDX entries
        for filename in spdx_file_map:
            file_info = spdx_file_map[filename]
            file_paths = file_info["paths"]

            # Build location mapping for this file
            locations_by_project = {}
            for fpath in file_paths:
                matching_root = None
                for proj_path in self.project_paths:
                    if fpath.startswith(str(proj_path)):
                        matching_root = str(proj_path)
                        break
                project_name, rel_path = get_project_relative_path(
                    fpath, project_root=matching_root
                )
                project_key = project_name if project_name else "unknown"
                if project_key not in locations_by_project:
                    locations_by_project[project_key] = set()
                locations_by_project[project_key].add(rel_path)

            # Group by license type
            for copyright_info in file_info["licenses"]:
                license_id = copyright_info.license_type

                if license_id not in unified_map:
                    unified_map[license_id] = {
                        "spdx_files": {},
                        "license_files": {},
                        "license_file_copyrights": {},
                        "license_text": None,
                    }

                # Add this file to the SPDX files for this license
                if filename not in unified_map[license_id]["spdx_files"]:
                    unified_map[license_id]["spdx_files"][filename] = {
                        "locations": {},
                        "copyrights": [],
                    }

                # Merge locations
                for proj, paths in locations_by_project.items():
                    if proj not in unified_map[license_id]["spdx_files"][filename]["locations"]:
                        unified_map[license_id]["spdx_files"][filename]["locations"][proj] = set()
                    unified_map[license_id]["spdx_files"][filename]["locations"][proj].update(paths)

                # Add copyright info
                unified_map[license_id]["spdx_files"][filename]["copyrights"].append(
                    (copyright_info.year_range, copyright_info.owner)
                )

        # Step 2: Process dependency LICENSE files
        # Try to detect license type from content; use unique paths for unrecognized licenses
        from .utility import detect_license_type, extract_copyright_from_license_text

        for _content_hash, file_info in dep_content_map.items():
            file_paths_dict = file_info["paths"]
            license_content = file_info["content"]

            # Extract copyright from license content
            copyrights = extract_copyright_from_license_text(license_content)

            # Build location mapping and copyright mapping for THIS iteration only
            locations = {}
            current_file_copyrights = {}

            for full_path, rel_path in file_paths_dict.items():
                matching_root = None
                for proj_path in self.project_paths:
                    if full_path.startswith(str(proj_path)):
                        matching_root = str(proj_path)
                        break
                project_name, _rel = get_project_relative_path(
                    full_path, project_root=matching_root
                )
                project_key = project_name if project_name else "unknown"
                if project_key not in locations:
                    locations[project_key] = set()
                locations[project_key].add(rel_path)

                # Store copyright for this file path
                if copyrights:
                    current_file_copyrights[rel_path] = copyrights

            # Try to detect the license type from the content
            detected_license = detect_license_type(license_content)

            if detected_license:
                # Use detected license ID - this will be grouped with SPDX entries of same type
                license_id = detected_license
            else:
                # For unrecognized licenses, create unique identifier using file paths
                # This ensures each different unrecognized license is kept separate
                file_paths_list = sorted(file_paths_dict.values())
                if file_paths_list:
                    # Use the first path as the unique identifier
                    license_id = f"Unrecognized license: {file_paths_list[0]}"
                else:
                    # Fallback to content hash
                    license_id = f"Unrecognized license: {_content_hash[:8]}"

            # Add or merge into unified entry for this license
            if license_id not in unified_map:
                unified_map[license_id] = {
                    "spdx_files": {},
                    "license_files": locations,
                    "license_file_copyrights": current_file_copyrights.copy(),
                    "license_text": license_content if not detected_license else None,
                }
            else:
                # Merge locations into existing entry
                for project_key, paths in locations.items():
                    if project_key not in unified_map[license_id]["license_files"]:
                        unified_map[license_id]["license_files"][project_key] = set()
                    unified_map[license_id]["license_files"][project_key].update(paths)
                # Merge copyright info for these specific files
                unified_map[license_id]["license_file_copyrights"].update(current_file_copyrights)

        # Step 3: Add full license texts for SPDX licenses
        if self.with_licenses:
            base_path = Path(__file__).parent
            for license_id in unified_map:
                if unified_map[license_id]["license_text"] is None:
                    # Parse compound licenses
                    license_components = SpdxExtractor._parse_license_components(license_id)
                    if len(license_components) == 1:
                        # Single license - get its text
                        text = get_license_text(license_components[0], base_path)
                        unified_map[license_id]["license_text"] = text
                    else:
                        # Compound license - concatenate texts
                        combined_text = []
                        for component in license_components:
                            text = get_license_text(component, base_path)
                            if text:
                                combined_text.append(f"--- {component} ---\n\n{text}")
                        unified_map[license_id]["license_text"] = "\n\n".join(combined_text)

        # Step 4: Convert to UnifiedLicenseEntry objects
        unified_entries = []
        for license_id in sorted(unified_map.keys()):
            data = unified_map[license_id]
            entry = UnifiedLicenseEntry(
                license_id=license_id,
                spdx_files=data["spdx_files"],
                license_files=data["license_files"],
                license_file_copyrights=data.get("license_file_copyrights", {}),
                license_text=data["license_text"],
            )
            unified_entries.append(entry)

        return unified_entries

    def _build_dependency_licenses(
        self, content_map: Dict[str, Dict[str, Any]]
    ) -> List[DependencyLicense]:
        """Build dependency license objects from content map."""
        dependency_licenses = []

        if not content_map:
            return dependency_licenses

        sorted_items = sorted(content_map.items(), key=lambda x: sorted(x[1]["filenames"])[0])

        for _content_hash, file_info in sorted_items:
            file_paths_dict = file_info["paths"]
            license_content = file_info["content"]

            # Build location mapping
            locations = {}
            for full_path, rel_path in file_paths_dict.items():
                matching_root = None
                for proj_path in self.project_paths:
                    if full_path.startswith(str(proj_path)):
                        matching_root = str(proj_path)
                        break

                project_name, _ = get_project_relative_path(full_path, project_root=matching_root)
                project_key = project_name if project_name else "unknown"
                if project_key not in locations:
                    locations[project_key] = set()
                locations[project_key].add(rel_path)

            dependency_licenses.append(
                DependencyLicense(locations=locations, content=license_content)
            )

        return dependency_licenses
