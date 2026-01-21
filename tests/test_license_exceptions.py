# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION.
# SPDX-License-Identifier: Apache-2.0
#

"""
Tests for license exception handling.
"""

from pathlib import Path

import pytest

from spdx_license_builder.extractors import SpdxExtractor
from spdx_license_builder.utility import get_license_text


class TestLicenseExceptions:
    """Test license exception handling."""

    def test_get_license_with_exception(self, tmp_path):
        """Test retrieving a license with exception (e.g., Apache-2.0 WITH LLVM-exception)."""
        # Create license directories
        common_dir = tmp_path / "common_licenses"
        common_dir.mkdir()
        exceptions_dir = tmp_path / "license_exceptions"
        exceptions_dir.mkdir()
        
        # Create Apache-2.0 license
        apache_file = common_dir / "Apache-2.0.txt"
        apache_text = "Apache License Version 2.0"
        apache_file.write_text(apache_text)
        
        # Create LLVM exception
        llvm_exception_file = exceptions_dir / "LLVM-exception.txt"
        exception_text = "LLVM Exceptions to the Apache 2.0 License"
        llvm_exception_file.write_text(exception_text)
        
        # Get the combined license text
        result = get_license_text("Apache-2.0 WITH LLVM-exception", tmp_path)
        
        assert result is not None
        assert apache_text in result
        assert exception_text in result
        assert "=" * 80 in result  # Separator between license and exception

    def test_get_license_with_exception_case_insensitive(self, tmp_path):
        """Test that WITH keyword is case-insensitive."""
        common_dir = tmp_path / "common_licenses"
        common_dir.mkdir()
        exceptions_dir = tmp_path / "license_exceptions"
        exceptions_dir.mkdir()
        
        apache_file = common_dir / "Apache-2.0.txt"
        apache_file.write_text("Apache License")
        
        llvm_file = exceptions_dir / "LLVM-exception.txt"
        llvm_file.write_text("LLVM Exception")
        
        # Test different case variations
        result1 = get_license_text("Apache-2.0 WITH LLVM-exception", tmp_path)
        result2 = get_license_text("Apache-2.0 with LLVM-exception", tmp_path)
        result3 = get_license_text("Apache-2.0 With LLVM-exception", tmp_path)
        
        assert result1 == result2 == result3

    def test_get_license_with_missing_exception(self, tmp_path, capsys):
        """Test handling when exception file is missing."""
        common_dir = tmp_path / "common_licenses"
        common_dir.mkdir()
        exceptions_dir = tmp_path / "license_exceptions"
        exceptions_dir.mkdir()
        
        apache_file = common_dir / "Apache-2.0.txt"
        apache_text = "Apache License"
        apache_file.write_text(apache_text)
        
        # Exception file doesn't exist
        result = get_license_text("Apache-2.0 WITH NonExistent-exception", tmp_path)
        
        # Should return base license even if exception is missing
        assert result == apache_text
        
        # Should warn about missing exception
        captured = capsys.readouterr()
        assert "NonExistent-exception" in captured.err
        assert "not found" in captured.err

    def test_get_license_with_missing_base(self, tmp_path):
        """Test handling when base license is missing."""
        exceptions_dir = tmp_path / "license_exceptions"
        exceptions_dir.mkdir()
        
        llvm_file = exceptions_dir / "LLVM-exception.txt"
        llvm_file.write_text("LLVM Exception")
        
        # Base license doesn't exist
        result = get_license_text("NonExistent WITH LLVM-exception", tmp_path)
        
        # Should return None if base license is missing
        assert result is None

    def test_plain_license_still_works(self, tmp_path):
        """Test that plain licenses without exceptions still work normally."""
        common_dir = tmp_path / "common_licenses"
        common_dir.mkdir()
        
        apache_file = common_dir / "Apache-2.0.txt"
        apache_text = "Apache License Version 2.0"
        apache_file.write_text(apache_text)
        
        # Get plain license without exception
        result = get_license_text("Apache-2.0", tmp_path)
        
        assert result == apache_text

    def test_spdx_extractor_with_exception(self, tmp_path):
        """Test extracting SPDX entries with license exceptions."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        
        test_file = src_dir / "test.cpp"
        test_file.write_text(
            """
// SPDX-FileCopyrightText: Copyright (c) 2023 LLVM Project
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

int main() { return 0; }
"""
        )
        
        extractor = SpdxExtractor([tmp_path], verbose=False, exclude_nvidia=False)
        file_map = extractor.extract()
        
        # Should extract the entry
        assert len(file_map) == 1
        
        # Get the first (and only) entry
        filename = next(iter(file_map.keys()))
        entry = file_map[filename]
        
        # Check license type is preserved with WITH
        licenses = entry["licenses"]
        assert len(licenses) == 1
        assert licenses[0].license_type == "Apache-2.0 WITH LLVM-exception"
        
        # Check copyright info
        assert licenses[0].owner == "LLVM Project"
        assert "2023" in licenses[0].year_range

    def test_parse_license_components_with_exception(self):
        """Test that _parse_license_components preserves WITH."""
        from spdx_license_builder.extractors import SpdxExtractor
        
        # WITH should not be split
        result = SpdxExtractor._parse_license_components("Apache-2.0 WITH LLVM-exception")
        assert result == ["Apache-2.0 WITH LLVM-exception"]
        
        # But AND should still be split
        result = SpdxExtractor._parse_license_components("Apache-2.0 AND MIT")
        assert result == ["Apache-2.0", "MIT"]
        
        # Combined: AND splits, but WITH is preserved
        result = SpdxExtractor._parse_license_components("Apache-2.0 WITH LLVM-exception AND MIT")
        assert result == ["Apache-2.0 WITH LLVM-exception", "MIT"]

    def test_llvm_exception_content(self):
        """Test that the actual LLVM exception file has correct content."""
        import spdx_license_builder
        base_path = Path(spdx_license_builder.__file__).parent
        
        llvm_file = base_path / "license_exceptions" / "LLVM-exception.txt"
        
        # File should exist
        assert llvm_file.exists(), "LLVM-exception.txt should be included in package"
        
        # Should contain key text from the LLVM exception
        content = llvm_file.read_text()
        assert "LLVM Exceptions" in content
        assert "Apache 2.0 License" in content
        assert "Object form" in content or "object form" in content.lower()
        assert "GPLv2" in content
