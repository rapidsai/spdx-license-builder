#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Tests for package metadata and version handling.
"""

import sys
from unittest.mock import patch


class TestPackageMetadata:
    """Test package metadata handling."""

    def test_version_from_metadata(self):
        """Test that version is read from package metadata when installed."""
        import spdx_license_builder

        # When the package is installed, __version__ should be available
        assert hasattr(spdx_license_builder, "__version__")
        assert isinstance(spdx_license_builder.__version__, str)
        assert len(spdx_license_builder.__version__) > 0

    def test_version_fallback_to_file(self):
        """Test that version falls back to VERSION file when package not installed."""
        # This test covers the except block in __init__.py lines 17-22

        # We need to reload the module with the metadata.version mocked to raise an exception
        import importlib
        import importlib.metadata

        with patch.object(
            importlib.metadata, "version", side_effect=importlib.metadata.PackageNotFoundError()
        ):
            # Remove the module from cache so it re-imports
            if "spdx_license_builder" in sys.modules:
                del sys.modules["spdx_license_builder"]

            # Re-import should trigger the fallback path
            import spdx_license_builder

            # Should have read from VERSION file
            assert hasattr(spdx_license_builder, "__version__")
            assert isinstance(spdx_license_builder.__version__, str)

    def test_all_exports_available(self):
        """Test that all exported names are available."""
        import spdx_license_builder

        # Check that __all__ items are accessible
        for name in spdx_license_builder.__all__:
            assert hasattr(spdx_license_builder, name), f"{name} not available"


class TestMainModule:
    """Test running as __main__ module."""

    def test_main_module_execution(self, monkeypatch, capsys):
        """Test running python -m spdx_license_builder."""
        import subprocess

        result = subprocess.run(
            [sys.executable, "-m", "spdx_license_builder", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0
        assert "license-builder" in result.stdout
        assert "--output-json" in result.stdout
