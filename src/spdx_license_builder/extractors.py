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
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .license_records import (
    CopyrightInfo,
    DependencyLicense,
    LicenseReport,
    LicenseText,
    SpdxCopyright,
    SpdxEntry,
    UnifiedLicenseEntry,
)
from .utility import (
    find_project_license_file,
    get_license_text,
    get_project_relative_path,
    walk_directories_for_files,
)


def _is_debugger_active() -> bool:
    """
    Detect if code is running under a debugger.

    Returns:
        True if debugger is active, False otherwise
    """
    # Check for common debugger indicators
    gettrace = getattr(sys, "gettrace", None)
    if gettrace is not None and gettrace():
        return True

    # Check for breakpoint() being set
    return bool(hasattr(sys, "breakpointhook") and sys.breakpointhook != sys.__breakpointhook__)


# Module-level constants for directory exclusions
# Using frozenset for O(1) membership testing
_BASE_EXCLUDED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".github",
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
        additional_exclude_dirs: Optional[Tuple[str, ...]] = None,
        verbose: bool = True,
        parallel: Optional[bool] = None,
        max_workers: Optional[int] = None,
    ):
        """
        Initialize the license extractor.

        Args:
            project_paths: List of project paths to scan
            directories_to_exclude: Optional tuple to completely replace default exclusions
            additional_exclude_dirs: Optional tuple to add to default exclusions
            verbose: Whether to print progress messages to stderr
            parallel: Enable parallel processing using ThreadPoolExecutor (default: True, auto-disabled in debugger)
            max_workers: Maximum number of worker threads (None = use default)
        """
        self.project_paths = self._validate_paths(project_paths)

        # Handle exclusion logic: use custom if provided, otherwise use defaults + additional
        if directories_to_exclude is not None:
            self.directories_to_exclude = directories_to_exclude
        else:
            base_excludes = set(self._default_excluded_dirs())
            if additional_exclude_dirs:
                base_excludes.update(additional_exclude_dirs)
            self.directories_to_exclude = tuple(base_excludes)

        self.verbose = verbose

        # Auto-detect parallel mode: enabled by default, disabled in debugger
        if parallel is None:
            if _is_debugger_active():
                self.parallel = False
                if self.verbose:
                    print("  [Debugger detected] Parallel processing disabled", file=sys.stderr)
            else:
                self.parallel = True
        else:
            self.parallel = parallel

        self.max_workers = max_workers

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
        additional_exclude_dirs: Optional[Tuple[str, ...]] = None,
        verbose: bool = True,
        parallel: Optional[bool] = None,
        max_workers: Optional[int] = None,
        exclude_nvidia: bool = False,
    ):
        """
        Initialize SPDX extractor with instance state for results.

        Args:
            project_paths: List of project paths to scan
            directories_to_exclude: Optional tuple to completely replace default exclusions
            additional_exclude_dirs: Optional tuple to add to default exclusions
            verbose: Whether to print progress messages
            parallel: Enable parallel processing (default: auto-detect, disabled in debugger)
            max_workers: Maximum number of worker threads
            exclude_nvidia: Filter out NVIDIA copyrights (default: False, include all)
        """
        super().__init__(
            project_paths,
            directories_to_exclude,
            additional_exclude_dirs,
            verbose,
            parallel,
            max_workers,
        )
        self.file_map = {}  # Store results on instance
        self.file_count = 0
        self.total_entries = 0
        self.exclude_nvidia = exclude_nvidia
        self._lock = threading.Lock()  # Thread safety for parallel processing

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
        entries_desc = (
            "copyright entries" if not self.exclude_nvidia else "non-NVIDIA copyright entries"
        )
        self._log(f"  Found {self.total_entries} {entries_desc}")
        self._log(f"  In {len(self.file_map)} unique files with third-party licenses")

        return self.file_map

    def _walk_directory(self, dir_path: str) -> None:
        """
        Walk through directory and collect SPDX entries.

        Updates self.file_map, self.file_count, and self.total_entries.
        Optionally filters NVIDIA copyrights based on self.exclude_nvidia.

        Args:
            dir_path: Directory path to scan
        """
        if self.parallel:
            self._walk_directory_parallel(dir_path)
        else:
            self._walk_directory_sequential(dir_path)

    def _walk_directory_sequential(self, dir_path: str) -> None:
        """Sequential directory walk (original implementation)."""
        for root, files in self._walk_with_exclusions(dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                self._process_file(file_path)

    def _walk_directory_parallel(self, dir_path: str) -> None:
        """Parallel directory walk using ThreadPoolExecutor."""
        # Collect all file paths first
        file_paths = []
        for root, files in self._walk_with_exclusions(dir_path):
            for file in files:
                file_paths.append(os.path.join(root, file))

        # Process files in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = {executor.submit(self._process_file, fp): fp for fp in file_paths}

            # Wait for completion
            for future in as_completed(futures):
                try:
                    future.result()  # This will raise any exceptions that occurred
                except Exception as e:
                    file_path = futures[future]
                    print(f"Error processing {file_path}: {e}", file=sys.stderr)

    def _process_file(self, file_path: str) -> None:
        """
        Process a single file for SPDX entries.

        Updates self.file_map, self.file_count, and self.total_entries.
        Thread-safe for parallel processing.

        Args:
            file_path: Path to file to process
        """
        entries = self._find_spdx_entries(file_path)

        # Use lock for thread-safe updates to shared data structures
        with self._lock:
            self.file_count += 1
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

        Filters out template patterns like @current_year@ or {datetime.datetime.today().year}
        """
        # Skip lines with template patterns
        if "@current_year@" in line or "{datetime.datetime.today().year}" in line:
            return None

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
                    # Clean up trailing commas/punctuation from years
                    years = years.rstrip(",;").strip()
                else:
                    # No years in this pattern (Pattern 3)
                    years = ""
                    owner = match.group(1).strip()
                return (years, owner.rstrip(".,;"))
        return None

    def _find_spdx_entries(self, file_path: str) -> List[SpdxCopyright]:
        """
        Extract SPDX copyright entries from a file and associate them with licenses.

        Args:
            file_path: Path to the file to scan for SPDX entries

        Returns:
            List of SpdxCopyright objects containing license info and file path.
            Optionally excludes NVIDIA copyrights based on self.exclude_nvidia.
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
                        # Check if it contains NVIDIA and should be filtered
                        if self.exclude_nvidia and "NVIDIA" in line.upper():
                            i += 1
                            continue

                        # Start collecting copyrights
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

                            # If we hit another FileCopyrightText, collect it (unless filtering NVIDIA)
                            elif "SPDX-FileCopyrightText:" in next_line:
                                should_skip = self.exclude_nvidia and "NVIDIA" in next_line.upper()
                                if not should_skip:
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
        additional_exclude_dirs: Optional[Tuple[str, ...]] = None,
        verbose: bool = True,
        parallel: Optional[bool] = None,
        max_workers: Optional[int] = None,
    ):
        """
        Initialize the dependency license extractor.

        Args:
            project_paths: List of project paths to scan
            directories_to_exclude: Optional tuple to completely replace default exclusions
            additional_exclude_dirs: Optional tuple to add to default exclusions
            verbose: Whether to print progress messages
            parallel: Enable parallel processing using ThreadPoolExecutor (default: True, auto-disabled in debugger)
            max_workers: Maximum number of worker threads (None = use default)
        """
        super().__init__(
            project_paths,
            directories_to_exclude,
            additional_exclude_dirs,
            verbose,
            parallel,
            max_workers,
        )
        # Store results on instance
        self.content_map = {}
        self.total_files = 0
        self._lock = threading.Lock()  # Thread safety for parallel processing

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

        with self._lock:
            self.total_files += len(matching_files)

        # Process each LICENSE file
        if self.parallel:
            self._process_files_parallel(matching_files, str(project_path))
        else:
            self._process_files_sequential(matching_files, str(project_path))

    def _process_files_sequential(self, file_paths: List[str], project_root: str) -> None:
        """Process LICENSE files sequentially."""
        for file_path in file_paths:
            self._process_license_file(file_path, project_root)

    def _process_files_parallel(self, file_paths: List[str], project_root: str) -> None:
        """Process LICENSE files in parallel."""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(self._process_license_file, fp, project_root): fp
                for fp in file_paths
            }

            # Wait for completion
            for future in as_completed(futures):
                try:
                    future.result()  # This will raise any exceptions that occurred
                except Exception as e:
                    file_path = futures[future]
                    print(f"Error processing {file_path}: {e}", file=sys.stderr)

    def _process_license_file(self, file_path: str, project_root: str) -> None:
        """
        Process a single LICENSE file.

        Updates self.content_map. Thread-safe for parallel processing.

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

            # Use lock for thread-safe updates to shared data structure
            with self._lock:
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
        additional_exclude_dirs: Optional[Tuple[str, ...]] = None,
        verbose: bool = True,
        parallel: Optional[bool] = None,
        max_workers: Optional[int] = None,
        exclude_nvidia: bool = False,
        enable_validation: bool = False,
    ):
        """
        Initialize the license report builder.

        Args:
            project_paths: List of project paths to scan
            with_licenses: Include full license texts for SPDX entries
            additional_exclude_dirs: Optional tuple of additional directories to exclude
            verbose: Whether to print progress messages
            parallel: Enable parallel processing for faster scanning (default: True, auto-disabled in debugger)
            max_workers: Maximum number of worker threads for parallel processing (None = use default)
            exclude_nvidia: Filter out NVIDIA copyrights from SPDX entries (default: False, include all)
            enable_validation: Enable license validation warnings (default: False, experimental)
        """
        self.project_paths = project_paths
        self.with_licenses = with_licenses
        self.additional_exclude_dirs = additional_exclude_dirs
        self.verbose = verbose
        self.exclude_nvidia = exclude_nvidia
        self.enable_validation = enable_validation

        # Auto-detect parallel mode: enabled by default, disabled in debugger
        if parallel is None:
            if _is_debugger_active():
                self.parallel = False
                if self.verbose:
                    print("  [Debugger detected] Parallel processing disabled", file=sys.stderr)
            else:
                self.parallel = True
        else:
            self.parallel = parallel

        self.max_workers = max_workers

    def _log(self, message: str) -> None:
        """Log a message to stderr if verbose mode is enabled."""
        if self.verbose:
            print(message, file=sys.stderr)

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

        # Parse project LICENSE files to get constituent licenses
        project_licenses_map = self._parse_project_licenses()

        # Extract SPDX entries
        spdx_extractor = SpdxExtractor(
            self.project_paths,
            additional_exclude_dirs=self.additional_exclude_dirs,
            verbose=self.verbose,
            parallel=self.parallel,
            max_workers=self.max_workers,
            exclude_nvidia=self.exclude_nvidia,
        )
        spdx_file_map = spdx_extractor.extract()

        # Extract dependency licenses
        dep_extractor = DependencyLicenseExtractor(
            self.project_paths,
            additional_exclude_dirs=self.additional_exclude_dirs,
            verbose=self.verbose,
            parallel=self.parallel,
            max_workers=self.max_workers,
        )
        dep_content_map = dep_extractor.extract()

        # Build unified entries (groups by license ID) with validation
        unified_entries = self._build_unified_entries(
            spdx_file_map, dep_content_map, project_licenses_map
        )

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

    def _parse_project_licenses(self) -> Dict[str, List[str]]:
        """
        Parse each project's main LICENSE file to extract constituent licenses.

        Returns:
            Dictionary mapping project_path -> list of SPDX license identifiers
        """
        project_licenses_map = {}

        for project_path in self.project_paths:
            self._log(f"\nChecking for project LICENSE file in: {project_path}")
            license_info = find_project_license_file(project_path)

            if license_info:
                license_path, _content, licenses = license_info
                if licenses:
                    self._log(
                        f"  Found {len(licenses)} license(s) in {license_path.name}: {', '.join(licenses)}"
                    )
                    project_licenses_map[str(project_path)] = licenses
                else:
                    self._log(
                        f"  Found LICENSE file {license_path.name} but could not identify license types"
                    )
                    project_licenses_map[str(project_path)] = []
            else:
                self._log("  No project LICENSE file found")
                project_licenses_map[str(project_path)] = []

        return project_licenses_map

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
        self,
        spdx_file_map: Dict[str, Dict[str, Any]],
        dep_content_map: Dict[str, Dict[str, Any]],
        project_licenses_map: Dict[str, List[str]],
    ) -> List[UnifiedLicenseEntry]:
        """
        Build unified license entries that group by license identifier.

        Args:
            spdx_file_map: Map of SPDX files and their licenses
            dep_content_map: Map of dependency LICENSE files
            project_licenses_map: Map of project_path -> list of licenses in project LICENSE

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
        from .utility import extract_copyright_from_license_text

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

            # Extract all licenses from the content (handles both single and aggregate files)
            from .utility import extract_all_licenses

            detected_licenses = extract_all_licenses(license_content)

            if detected_licenses:
                # Decompose aggregate LICENSE files: add this LICENSE file to each constituent license
                for license_id in detected_licenses:
                    # Add or merge into unified entry for this license
                    if license_id not in unified_map:
                        unified_map[license_id] = {
                            "spdx_files": {},
                            "license_files": locations.copy(),
                            "license_file_copyrights": current_file_copyrights.copy(),
                            "license_text": None,  # Will be fetched later
                        }
                    else:
                        # Merge locations into existing entry
                        for project_key, paths in locations.items():
                            if project_key not in unified_map[license_id]["license_files"]:
                                unified_map[license_id]["license_files"][project_key] = set()
                            unified_map[license_id]["license_files"][project_key].update(paths)
                        # Merge copyright info for these specific files
                        unified_map[license_id]["license_file_copyrights"].update(
                            current_file_copyrights
                        )
            else:
                # Unrecognized license - create a unique entry for it
                file_paths_list = sorted(file_paths_dict.values())
                if file_paths_list:
                    license_id = f"Unrecognized license: {file_paths_list[0]}"
                else:
                    license_id = f"Unrecognized license: {_content_hash[:8]}"

                # Add as a single entry with the full license text
                if license_id not in unified_map:
                    unified_map[license_id] = {
                        "spdx_files": {},
                        "license_files": locations,
                        "license_file_copyrights": current_file_copyrights.copy(),
                        "license_text": license_content,  # Store the full unrecognized text
                    }
                else:
                    # Merge locations into existing entry
                    for project_key, paths in locations.items():
                        if project_key not in unified_map[license_id]["license_files"]:
                            unified_map[license_id]["license_files"][project_key] = set()
                        unified_map[license_id]["license_files"][project_key].update(paths)
                    # Merge copyright info for these specific files
                    unified_map[license_id]["license_file_copyrights"].update(
                        current_file_copyrights
                    )

        # Step 3: Add full license texts for SPDX licenses
        if self.with_licenses:
            base_path = Path(__file__).parent
            for license_id in unified_map:
                # Skip unrecognized licenses - they already have license_text from the LICENSE file
                if license_id.startswith("Unrecognized license"):
                    continue

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

        # Step 4: Validate licenses against project LICENSE files
        self._validate_licenses(unified_map, project_licenses_map)

        # Step 5: Convert to UnifiedLicenseEntry objects
        unified_entries = []
        for license_id in sorted(unified_map.keys()):
            data = unified_map[license_id]
            entry = UnifiedLicenseEntry(
                license_id=license_id,
                spdx_files=data["spdx_files"],
                license_files=data["license_files"],
                license_file_copyrights=data.get("license_file_copyrights", {}),
                license_text=data["license_text"],
                in_project_license=data.get("in_project_license"),
                validation_warnings=data.get("validation_warnings", []),
            )
            unified_entries.append(entry)

        return unified_entries

    def _validate_licenses(
        self, unified_map: Dict[str, Dict[str, Any]], project_licenses_map: Dict[str, List[str]]
    ) -> None:
        """
        Validate that file-level SPDX licenses exist in project LICENSE files.

        Updates unified_map in-place with validation results.

        Args:
            unified_map: Map of license_id -> entry data
            project_licenses_map: Map of project_path -> list of licenses
        """
        # Build a flattened set of all project licenses for quick lookup
        all_project_licenses = set()
        for licenses in project_licenses_map.values():
            all_project_licenses.update(licenses)

        # Skip validation if no project licenses were found
        if not all_project_licenses:
            return

        for license_id, data in unified_map.items():
            # Only validate licenses that come from SPDX file headers
            # (not dependency LICENSE files or aggregate licenses)
            if not data["spdx_files"]:
                # This license only comes from dependency LICENSE files, skip validation
                continue

            # Skip validation for unrecognized licenses
            if license_id.startswith("Unrecognized license"):
                continue

            # Parse compound licenses (e.g., "Apache-2.0 AND MIT")
            license_components = SpdxExtractor._parse_license_components(license_id)

            # Check if all components are in the project licenses
            missing_components = []
            for component in license_components:
                if component not in all_project_licenses:
                    missing_components.append(component)

            # Store validation results
            if missing_components:
                data["in_project_license"] = False
                warning = (
                    f"License '{license_id}' declared in source files but not found in project LICENSE file. "
                    f"Missing components: {', '.join(missing_components)}"
                )
                data["validation_warnings"] = [warning]
                if self.enable_validation:
                    print(f"\n[⚠] {warning}", file=sys.stderr)
            else:
                data["in_project_license"] = True
                data["validation_warnings"] = []

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
