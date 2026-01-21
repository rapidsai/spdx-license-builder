#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for JSON output functionality."""

import json

from spdx_license_builder.extractors import LicenseReportBuilder
from spdx_license_builder.license_records import UnifiedLicenseEntry


class TestJSONOutput:
    """Test JSON serialization of license reports."""

    def test_unified_entry_to_dict(self):
        """Test UnifiedLicenseEntry.to_dict() produces valid structure."""
        entry = UnifiedLicenseEntry(
            license_id="Apache-2.0",
            spdx_files={
                "test.cpp": {
                    "locations": {"project1": {"src/test.cpp"}},
                    "copyrights": [("2023", "Test Corp")],
                }
            },
            license_files={"project1": {"LICENSE"}},
            license_file_copyrights={"LICENSE": [("2023-2024", "Test Inc")]},
            license_text="Apache License...",
            in_project_license=True,
            validation_warnings=["Test warning"],
        )

        result = entry.to_dict()

        # Verify structure
        assert result["license_id"] == "Apache-2.0"
        assert result["license_text"] == "Apache License..."
        assert result["in_project_license"] is True
        assert result["validation_warnings"] == ["Test warning"]

        # Verify spdx_files structure
        assert len(result["spdx_files"]) == 1
        spdx_file = result["spdx_files"][0]
        assert spdx_file["filename"] == "test.cpp"
        assert len(spdx_file["paths"]) == 1
        assert spdx_file["paths"][0] == {"project": "project1", "path": "src/test.cpp"}
        assert len(spdx_file["copyrights"]) == 1
        assert spdx_file["copyrights"][0] == {"year_range": "2023", "owner": "Test Corp"}

        # Verify license_files structure
        assert len(result["license_files"]) == 1
        license_file = result["license_files"][0]
        assert license_file["project"] == "project1"
        assert license_file["path"] == "LICENSE"
        assert len(license_file["copyrights"]) == 1
        assert license_file["copyrights"][0] == {"year_range": "2023-2024", "owner": "Test Inc"}

    def test_license_report_to_dict(self, test_project_dir):
        """Test LicenseReport.to_dict() produces valid structure."""
        builder = LicenseReportBuilder([test_project_dir], verbose=False, parallel=False)
        report = builder.build()

        result = report.to_dict()

        # Verify structure
        assert "licenses" in result
        assert "summary" in result
        assert isinstance(result["licenses"], list)
        assert isinstance(result["summary"], dict)

        # Verify summary
        assert "total_licenses" in result["summary"]
        assert "license_ids" in result["summary"]
        assert result["summary"]["total_licenses"] == len(result["licenses"])
        assert result["summary"]["total_licenses"] == len(result["summary"]["license_ids"])

    def test_license_report_to_json(self, test_project_dir):
        """Test LicenseReport.to_json() produces valid JSON string."""
        builder = LicenseReportBuilder([test_project_dir], verbose=False, parallel=False)
        report = builder.build()

        json_str = report.to_json()

        # Verify it's valid JSON
        parsed = json.loads(json_str)
        assert "licenses" in parsed
        assert "summary" in parsed

        # Verify we can serialize to JSON without errors
        json.dumps(parsed)  # Should not raise

    def test_json_output_copyrights_separate_from_paths(self, test_project_dir):
        """Test that copyrights are in a separate list from file paths in JSON."""
        builder = LicenseReportBuilder([test_project_dir], verbose=False, parallel=False)
        report = builder.build()

        result = report.to_dict()

        # Check at least one entry has separate copyrights
        found_path = False

        for license_entry in result["licenses"]:
            # Check SPDX files
            for spdx_file in license_entry.get("spdx_files", []):
                if "copyrights" in spdx_file and spdx_file["copyrights"]:
                    # Verify structure
                    for copyright_item in spdx_file["copyrights"]:
                        assert "year_range" in copyright_item
                        assert "owner" in copyright_item

                if "paths" in spdx_file and spdx_file["paths"]:
                    found_path = True
                    # Verify structure
                    for path_item in spdx_file["paths"]:
                        assert "project" in path_item
                        assert "path" in path_item

            # Check LICENSE files
            for license_file in license_entry.get("license_files", []):
                assert "project" in license_file
                assert "path" in license_file
                assert "copyrights" in license_file
                found_path = True

                if license_file["copyrights"]:
                    for copyright_item in license_file["copyrights"]:
                        assert "year_range" in copyright_item
                        assert "owner" in copyright_item

        # Verify we actually tested something
        assert found_path, "Should have found at least one file path"

    def test_json_output_empty_copyrights(self):
        """Test JSON serialization with empty copyrights list."""
        entry = UnifiedLicenseEntry(
            license_id="MIT",
            spdx_files={
                "test.h": {
                    "locations": {"proj": {"include/test.h"}},
                    "copyrights": [],  # Empty copyrights
                }
            },
            license_text="MIT License...",
        )

        result = entry.to_dict()

        assert len(result["spdx_files"]) == 1
        assert result["spdx_files"][0]["copyrights"] == []

    def test_json_output_multiple_paths_same_file(self):
        """Test JSON serialization with same file in multiple locations."""
        entry = UnifiedLicenseEntry(
            license_id="BSD-3-Clause",
            spdx_files={
                "common.h": {
                    "locations": {
                        "proj1": {"src/common.h"},
                        "proj2": {"lib/common.h", "include/common.h"},
                    },
                    "copyrights": [("2024", "Multi Corp")],
                }
            },
        )

        result = entry.to_dict()

        spdx_file = result["spdx_files"][0]
        assert len(spdx_file["paths"]) == 3  # Should have 3 total paths

        # Verify all paths are present
        paths_set = {(p["project"], p["path"]) for p in spdx_file["paths"]}
        assert ("proj1", "src/common.h") in paths_set
        assert ("proj2", "lib/common.h") in paths_set
        assert ("proj2", "include/common.h") in paths_set

    def test_json_serializable_no_sets(self):
        """Test that to_dict() doesn't include non-serializable sets."""
        entry = UnifiedLicenseEntry(
            license_id="Apache-2.0",
            license_files={"proj": {"LICENSE", "LICENSE.txt"}},  # Set input
        )

        result = entry.to_dict()

        # Try to serialize to JSON - should not raise
        json_str = json.dumps(result)
        assert json_str  # Should produce valid JSON string

    def test_validation_fields_in_json(self):
        """Test that validation fields are included in JSON output."""
        entry = UnifiedLicenseEntry(
            license_id="GPL-3.0-only",
            in_project_license=False,
            validation_warnings=[
                "License not found in project LICENSE",
                "Consider adding GPL-3.0 to project LICENSE",
            ],
        )

        result = entry.to_dict()

        assert result["in_project_license"] is False
        assert len(result["validation_warnings"]) == 2
        assert "License not found in project LICENSE" in result["validation_warnings"]


class TestJSONCLI:
    """Test JSON output via CLI."""

    def test_cli_json_output(self, test_project_dir, tmp_path):
        """Test that --output-json produces valid JSON output."""
        import subprocess

        output_file = tmp_path / "output.json"

        result = subprocess.run(
            [
                "license-builder",
                str(test_project_dir),
                "--output-json",
                str(output_file),
                "--no-parallel",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert output_file.exists()

        # Verify it's valid JSON
        with open(output_file) as f:
            data = json.load(f)

        assert "licenses" in data
        assert "summary" in data
        assert isinstance(data["licenses"], list)

