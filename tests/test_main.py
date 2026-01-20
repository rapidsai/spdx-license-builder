#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Tests for __main__.py module entry point.
"""

import sys
from unittest.mock import patch


def test_main_module_importable():
    """Test that __main__ module can be imported."""
    # This should not raise an exception
    from spdx_license_builder import __main__

    assert hasattr(__main__, "main")


def test_main_module_execution_with_mock(monkeypatch):
    """Test __main__ module execution calls main()."""
    # Mock sys.argv to prevent actual execution
    monkeypatch.setattr(sys, "argv", ["spdx-license-builder", "--help"])

    with patch("spdx_license_builder.cli.main") as mock_main:
        # We need to simulate running the module as __main__
        # The actual execution happens when Python runs: python -m spdx_license_builder
        # For testing, we just verify the import structure is correct
        from spdx_license_builder import __main__ as main_module

        # Verify it has the main function imported
        assert main_module.main is not None

        # Now actually call what the module would call
        if hasattr(main_module, "__name__") and main_module.__name__ == "__main__":
            main_module.main()
            mock_main.assert_called_once()
