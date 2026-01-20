#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Tests for the unified CLI.
"""

import sys

import pytest


class TestCLI:
    """Test the license-builder CLI."""

    def test_cli_help(self, monkeypatch, capsys):
        """Test that CLI help displays correctly."""
        from spdx_license_builder.cli import main

        monkeypatch.setattr(sys, "argv", ["license-builder", "--help"])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        output = captured.out

        # Verify help contains expected options
        assert "project_path" in output
        assert "--no-extract" in output
        assert "--no-copy" in output
        assert "--output" in output

    def test_cli_version(self, monkeypatch, capsys):
        """Test that CLI version displays correctly."""
        from spdx_license_builder.cli import main

        monkeypatch.setattr(sys, "argv", ["license-builder", "--version"])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

    def test_no_args_error(self, monkeypatch, capsys):
        """Test that running without args shows error."""
        from spdx_license_builder.cli import main

        monkeypatch.setattr(sys, "argv", ["license-builder"])

        with pytest.raises(SystemExit) as exc_info:
            main()

        # Should exit with error code
        assert exc_info.value.code != 0

    def test_both_no_flags_error(self, monkeypatch, capsys):
        """Test that using both --no-extract and --no-copy shows error."""
        from spdx_license_builder.cli import main

        monkeypatch.setattr(
            sys, "argv", ["license-builder", "/path/to/project", "--no-extract", "--no-copy"]
        )

        with pytest.raises(SystemExit) as exc_info:
            main()

        # Should exit with error
        assert exc_info.value.code != 0

        captured = capsys.readouterr()
        assert "Cannot use both --no-extract and --no-copy" in captured.err

    def test_with_project_path(self, monkeypatch, test_project_dir):
        """Test running with a valid project path."""
        from spdx_license_builder.cli import main

        monkeypatch.setattr(sys, "argv", ["license-builder", str(test_project_dir)])

        # Should succeed
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

    def test_no_extract_mode(self, monkeypatch, test_project_dir):
        """Test --no-extract flag (LICENSE files only)."""
        from spdx_license_builder.cli import main

        monkeypatch.setattr(sys, "argv", ["license-builder", str(test_project_dir), "--no-extract"])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

    def test_no_copy_mode(self, monkeypatch, test_project_dir):
        """Test --no-copy flag (SPDX entries only)."""
        from spdx_license_builder.cli import main

        monkeypatch.setattr(sys, "argv", ["license-builder", str(test_project_dir), "--no-copy"])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

    def test_no_license_text_flag(self, monkeypatch, test_project_dir):
        """Test --no-license-text flag."""
        from spdx_license_builder.cli import main

        monkeypatch.setattr(
            sys, "argv", ["license-builder", str(test_project_dir), "--no-license-text"]
        )

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

    def test_deduplication_flags(self, monkeypatch, test_project_dir):
        """Test deduplication flags."""
        from spdx_license_builder.cli import main

        monkeypatch.setattr(
            sys,
            "argv",
            [
                "license-builder",
                str(test_project_dir),
                "--deduplicate-rapids",
                "--deduplicate-hierarchical",
            ],
        )

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

    def test_no_normalize_years_flag(self, monkeypatch, test_project_dir):
        """Test --no-normalize-years flag."""
        from spdx_license_builder.cli import main

        monkeypatch.setattr(
            sys, "argv", ["license-builder", str(test_project_dir), "--no-normalize-years"]
        )

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0


class TestModuleExecution:
    """Test running as a module."""

    def test_module_main_help(self, monkeypatch, capsys):
        """Test running as python -m spdx_license_builder."""
        monkeypatch.setattr(sys, "argv", ["python", "-m", "spdx_license_builder", "--help"])

        from spdx_license_builder.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0


class TestCLIEdgeCases:
    """Test edge cases and error handling."""

    def test_nonexistent_project_path(self, monkeypatch, tmp_path):
        """Test handling of nonexistent project paths."""
        from spdx_license_builder.cli import main

        fake_path = tmp_path / "nonexistent"
        monkeypatch.setattr(sys, "argv", ["license-builder", str(fake_path)])

        # Should exit with error
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    def test_multiple_project_paths(self, monkeypatch, test_project_dir, tmp_path):
        """Test with multiple project paths."""
        from spdx_license_builder.cli import main

        monkeypatch.setattr(sys, "argv", ["license-builder", str(test_project_dir), str(tmp_path)])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

    def test_output_file(self, monkeypatch, test_project_dir, tmp_path):
        """Test writing to output file."""
        from spdx_license_builder.cli import main

        output_file = tmp_path / "output.txt"
        monkeypatch.setattr(
            sys, "argv", ["license-builder", str(test_project_dir), "--output", str(output_file)]
        )

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0
        assert output_file.exists()
        assert output_file.stat().st_size > 0
