#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Tests for the unified CLI.
"""

import sys

import pytest


class TestUnifiedCLI:
    """Test the unified license-builder CLI."""

    def test_cli_help(self, monkeypatch, capsys):
        """Test that CLI help displays correctly."""
        from spdx_license_builder.cli import main

        # Mock sys.argv
        monkeypatch.setattr(sys, "argv", ["license-builder", "--help"])

        # Should exit with code 0 and display help
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        output = captured.out

        # Verify help contains expected subcommands
        assert "extract" in output
        assert "copy" in output
        assert "license-builder" in output

    def test_cli_version(self, monkeypatch, capsys):
        """Test that CLI version displays correctly."""
        from spdx_license_builder.cli import main

        monkeypatch.setattr(sys, "argv", ["license-builder", "--version"])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        output = captured.out

        # Should display version number
        assert "license-builder" in output
        # Version should be present (format: X.Y.Z)
        assert any(char.isdigit() for char in output)

    def test_extract_subcommand_help(self, monkeypatch, capsys):
        """Test extract subcommand help."""
        from spdx_license_builder.cli import main

        monkeypatch.setattr(sys, "argv", ["license-builder", "extract", "--help"])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        output = captured.out

        # Verify extract help content
        assert "extract" in output
        assert "project_path" in output
        assert "--with-licenses" in output
        assert "SPDX" in output

    def test_copy_subcommand_help(self, monkeypatch, capsys):
        """Test copy subcommand help."""
        from spdx_license_builder.cli import main

        monkeypatch.setattr(sys, "argv", ["license-builder", "copy", "--help"])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        output = captured.out

        # Verify copy help content
        assert "copy" in output
        assert "project_path" in output
        assert "LICENSE" in output

    def test_no_subcommand_error(self, monkeypatch, capsys):
        """Test that CLI errors when no subcommand is provided."""
        from spdx_license_builder.cli import main

        monkeypatch.setattr(sys, "argv", ["license-builder"])

        # Should exit with non-zero code
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code != 0

    def test_extract_with_project_path(self, monkeypatch, tmp_path, capsys):
        """Test extract subcommand with a project path."""
        from spdx_license_builder.cli import main

        # Create a minimal test project
        cpp_dir = tmp_path / "cpp"
        cpp_dir.mkdir()

        test_file = cpp_dir / "test.cpp"
        test_file.write_text(
            """
// SPDX-FileCopyrightText: Copyright (c) 2020 Example Corp
// SPDX-License-Identifier: MIT
"""
        )

        monkeypatch.setattr(sys, "argv", ["license-builder", "extract", str(tmp_path)])

        # Should run without error
        try:
            main()
        except SystemExit as e:
            # Exit code 0 is OK (normal completion)
            if e.code != 0:
                raise

        # Check that some output was produced
        captured = capsys.readouterr()
        # Output goes to stdout and stderr
        assert len(captured.out) > 0 or len(captured.err) > 0

    def test_copy_with_project_path(self, monkeypatch, tmp_path, capsys):
        """Test copy subcommand with a project path."""
        from spdx_license_builder.cli import main

        # Create a minimal test project with LICENSE
        cpp_dir = tmp_path / "cpp"
        cpp_dir.mkdir()

        lib_dir = cpp_dir / "lib"
        lib_dir.mkdir()

        (lib_dir / "LICENSE").write_text("MIT License")

        monkeypatch.setattr(sys, "argv", ["license-builder", "copy", str(tmp_path)])

        # Should run without error
        try:
            main()
        except SystemExit as e:
            if e.code != 0:
                raise

        # Check that output was produced
        captured = capsys.readouterr()
        assert len(captured.out) > 0 or len(captured.err) > 0


class TestModuleExecution:
    """Test running as Python module."""

    def test_module_main_help(self, monkeypatch, capsys):
        """Test python -m spdx_license_builder shows help."""
        from spdx_license_builder.__main__ import main

        monkeypatch.setattr(sys, "argv", ["spdx_license_builder", "--help"])

        with pytest.raises(SystemExit) as exc_info:
            main()

        # --help should exit with code 0
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "license-builder" in captured.out
        assert "extract" in captured.out
        assert "copy" in captured.out


class TestCLIEdgeCases:
    """Test CLI edge cases and error handling."""

    def test_nonexistent_project_path(self, monkeypatch, capsys):
        """Test handling of non-existent project path."""
        from spdx_license_builder.cli import main

        monkeypatch.setattr(sys, "argv", ["license-builder", "extract", "/nonexistent/path/12345"])

        # Should exit with error
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code != 0

        # Error message should be printed to stderr
        captured = capsys.readouterr()
        assert "does not exist" in captured.err.lower() or "error" in captured.err.lower()

    def test_multiple_project_paths(self, monkeypatch, tmp_path, capsys):
        """Test CLI with multiple project paths."""
        from spdx_license_builder.cli import main

        # Create two test projects
        project1 = tmp_path / "project1"
        project1.mkdir()
        (project1 / "cpp").mkdir()

        project2 = tmp_path / "project2"
        project2.mkdir()
        (project2 / "cpp").mkdir()

        monkeypatch.setattr(
            sys, "argv", ["license-builder", "extract", str(project1), str(project2)]
        )

        # Should run without error
        try:
            main()
        except SystemExit as e:
            if e.code != 0:
                raise

        # Should have processed both projects
        captured = capsys.readouterr()
        # Output should mention both projects (in stderr logging)
        output = captured.err + captured.out
        assert "project1" in output or "project2" in output
