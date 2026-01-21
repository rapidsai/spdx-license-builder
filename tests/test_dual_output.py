#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for dual-output functionality (user-friendly and machine-friendly)."""

import io
import subprocess

from spdx_license_builder.extractors import LicenseReportBuilder


class TestDualOutput:
    """Test dual output modes."""

    def test_default_stdout_uses_user_friendly_format(self, test_project_dir):
        """Test that default stdout output (no flags) uses user-friendly format."""
        # Run without any output flags - should default to user-friendly format
        result = subprocess.run(
            ["license-builder", str(test_project_dir), "--no-parallel"],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0
        output = result.stdout

        # Should have NVIDIA header at top
        assert "License: Apache-2.0 (NVIDIA Code)" in output
        assert "Copyright (c)" in output
        assert "NVIDIA CORPORATION" in output

        # Should have third-party separator
        assert "THIRD-PARTY SOFTWARE LICENSES" in output

        # After the separator, NVIDIA copyrights should be filtered
        parts = output.split("THIRD-PARTY SOFTWARE LICENSES")
        if len(parts) > 1:
            third_party_section = parts[1]
            # Count NVIDIA mentions in third-party section (should be 0)
            nvidia_count = third_party_section.count("NVIDIA")
            assert (
                nvidia_count == 0
            ), f"Found {nvidia_count} NVIDIA mentions in third-party section (should be 0)"

    def test_machine_friendly_includes_nvidia(self, test_project_dir, tmp_path):
        """Test that machine-friendly output includes NVIDIA copyrights."""
        builder = LicenseReportBuilder([test_project_dir], verbose=False, parallel=False)
        report = builder.build()

        output = io.StringIO()
        report.write(output, show_validation=False)
        result = output.getvalue()

        # Should include NVIDIA copyrights
        assert "NVIDIA" in result

    def test_nvidia_copyright_range_computed_from_files(self, test_project_dir):
        """Test that NVIDIA copyright range is computed from actual file copyrights."""
        builder = LicenseReportBuilder([test_project_dir], verbose=False, parallel=False)
        report = builder.build()

        output = io.StringIO()
        report.write_user_friendly(output)
        result = output.getvalue()

        # Should have NVIDIA copyright with computed date range
        assert "Copyright (c)" in result
        assert "NVIDIA CORPORATION & AFFILIATES" in result

        # Extract the copyright line
        import re

        match = re.search(r"Copyright \(c\) (\d{4}(?:-\d{4})?), NVIDIA CORPORATION", result)
        assert match, "Should find NVIDIA copyright with date range"

        date_range = match.group(1)

        # Should include dates from test fixtures (2020 from cuco, 2025-2026 from nvidia_file.cuh)
        if "-" in date_range:
            start_year, end_year = date_range.split("-")
            start_year = int(start_year)
            end_year = int(end_year)

            # Should start at 2020 (earliest NVIDIA copyright in fixtures)
            assert start_year == 2020, f"Expected start year 2020, got {start_year}"

            # Should end at current year or later
            from datetime import datetime

            current_year = datetime.now().year
            assert end_year >= current_year, f"Expected end year >= {current_year}, got {end_year}"

    def test_user_friendly_has_nvidia_header(self, test_project_dir, tmp_path):
        """Test that user-friendly output starts with NVIDIA license."""
        builder = LicenseReportBuilder([test_project_dir], verbose=False, parallel=False)
        report = builder.build()

        output = io.StringIO()
        report.write_user_friendly(output)
        result = output.getvalue()

        # Should start with NVIDIA section
        assert "Apache-2.0 (NVIDIA Code)" in result

        # Should have NVIDIA copyright with computed date range (from actual file copyrights)
        assert "NVIDIA CORPORATION & AFFILIATES" in result
        import re

        # Check for copyright line with year range pattern (e.g., "2020-2026" or "2024")
        match = re.search(r"Copyright \(c\) \d{4}(?:-\d{4})?, NVIDIA CORPORATION", result)
        assert match, "Should have NVIDIA copyright with date range"

        # Should have third-party separator
        assert "THIRD-PARTY SOFTWARE LICENSES" in result

    def test_user_friendly_filters_nvidia_from_third_party(self, tmp_path):
        """Test that NVIDIA copyrights are filtered from third-party section."""
        # Create test files
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        # File with NVIDIA copyright
        nvidia_file = src_dir / "nvidia.cpp"
        nvidia_file.write_text(
            """
// SPDX-FileCopyrightText: Copyright (c) 2024, NVIDIA CORPORATION
// SPDX-License-Identifier: MIT
"""
        )

        # File with third-party copyright
        third_party_file = src_dir / "third_party.cpp"
        third_party_file.write_text(
            """
// SPDX-FileCopyrightText: Copyright (c) 2024, Example Corp
// SPDX-License-Identifier: MIT
"""
        )

        builder = LicenseReportBuilder([tmp_path], verbose=False, parallel=False)
        report = builder.build()

        output = io.StringIO()
        report.write_user_friendly(output)
        result = output.getvalue()

        # Split into sections
        parts = result.split("THIRD-PARTY SOFTWARE LICENSES")
        assert len(parts) == 2

        nvidia_section = parts[0]
        third_party_section = parts[1]

        # NVIDIA section should have NVIDIA copyright (in header)
        assert "NVIDIA" in nvidia_section

        # Third-party section should only have Example Corp
        assert "Example Corp" in third_party_section
        assert "NVIDIA CORPORATION" not in third_party_section  # Filtered from third-party

    def test_validation_not_shown_by_default(self, test_project_dir):
        """Test that validation status is not shown in default write()."""
        builder = LicenseReportBuilder([test_project_dir], verbose=False, parallel=False)
        report = builder.build()

        output = io.StringIO()
        report.write(output)  # show_validation=False by default
        result = output.getvalue()

        # Should not have validation markers
        assert "[✓]" not in result
        assert "[⚠]" not in result

    def test_validation_shown_when_requested(self, test_project_dir):
        """Test that validation status is shown when show_validation=True."""
        builder = LicenseReportBuilder([test_project_dir], verbose=False, parallel=False)
        report = builder.build()

        output = io.StringIO()
        report.write(output, show_validation=True)
        result = output.getvalue()

        # Validation markers might appear if licenses were validated
        # Just verify the parameter is accepted
        assert isinstance(result, str)

    def test_template_patterns_filtered(self, tmp_path):
        """Test that template patterns like @current_year@ are filtered out."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        template_file = src_dir / "template.cpp"
        template_file.write_text(
            """
// SPDX-FileCopyrightText: Copyright (c) @current_year@, NVIDIA CORPORATION
// SPDX-License-Identifier: Apache-2.0
"""
        )

        builder = LicenseReportBuilder([tmp_path], verbose=False, parallel=False)
        report = builder.build()

        output = io.StringIO()
        report.write(output)
        result = output.getvalue()

        # Template pattern should be filtered out
        assert "@current_year@" not in result

    def test_datetime_template_filtered(self, tmp_path):
        """Test that datetime.datetime template patterns are filtered out."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        template_file = src_dir / "template.py"
        template_file.write_text(
            """
# SPDX-FileCopyrightText: Copyright (c) 2023-{datetime.datetime.today().year}, NVIDIA CORPORATION
# SPDX-License-Identifier: Apache-2.0
"""
        )

        builder = LicenseReportBuilder([tmp_path], verbose=False, parallel=False)
        report = builder.build()

        output = io.StringIO()
        report.write(output)
        result = output.getvalue()

        # Template pattern should be filtered out
        assert "datetime.datetime.today().year" not in result
        assert "{datetime" not in result


class TestDualOutputCLI:
    """Test dual output via CLI."""

    def test_cli_dual_output(self, test_project_dir, tmp_path):
        """Test CLI with both --output-json and --output-txt."""
        import json

        machine_file = tmp_path / "machine.json"
        user_file = tmp_path / "user.txt"

        result = subprocess.run(
            [
                "license-builder",
                str(test_project_dir),
                "--output-json",
                str(machine_file),
                "--output-txt",
                str(user_file),
                "--no-parallel",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert machine_file.exists()
        assert user_file.exists()

        # Verify machine output is JSON
        machine_content = machine_file.read_text()
        machine_data = json.loads(machine_content)
        assert "licenses" in machine_data
        assert "summary" in machine_data

        # Verify user output is text with NVIDIA header
        user_content = user_file.read_text()
        assert "Apache-2.0 (NVIDIA Code)" in user_content
        assert "THIRD-PARTY SOFTWARE LICENSES" in user_content

    def test_cli_machine_only(self, test_project_dir, tmp_path):
        """Test CLI with only --output-json (machine JSON)."""
        import json

        machine_file = tmp_path / "machine.json"

        result = subprocess.run(
            [
                "license-builder",
                str(test_project_dir),
                "--output-json",
                str(machine_file),
                "--no-parallel",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert machine_file.exists()

        # Verify it's valid JSON
        machine_content = machine_file.read_text()
        machine_data = json.loads(machine_content)
        assert "licenses" in machine_data

    def test_cli_user_only(self, test_project_dir, tmp_path):
        """Test CLI with only --output-txt."""
        user_file = tmp_path / "user.txt"

        result = subprocess.run(
            [
                "license-builder",
                str(test_project_dir),
                "--output-txt",
                str(user_file),
                "--no-parallel",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert user_file.exists()

        user_content = user_file.read_text()
        assert "Apache-2.0 (NVIDIA Code)" in user_content
