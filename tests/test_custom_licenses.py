# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION.
# SPDX-License-Identifier: Apache-2.0
#

"""
Tests for custom license functionality.
"""

import json
from pathlib import Path
from unittest import mock

import pytest

from spdx_license_builder.extractors import SpdxExtractor
from spdx_license_builder.utility import get_license_text


class TestCustomLicenses:
    """Test custom license reference handling."""

    def test_get_license_text_custom_license_found(self, tmp_path):
        """Test retrieving a custom license that exists locally."""
        # Create custom_licenses directory with a license file
        custom_dir = tmp_path / "custom_licenses"
        custom_dir.mkdir()
        
        license_file = custom_dir / "LicenseRef-TestLicense.txt"
        license_text = "This is a test custom license."
        license_file.write_text(license_text)
        
        # Get the license text
        result = get_license_text("LicenseRef-TestLicense", tmp_path)
        
        assert result == license_text

    def test_get_license_text_custom_license_not_found(self, tmp_path, capsys):
        """Test handling of missing custom license."""
        # Create empty custom_licenses directory
        custom_dir = tmp_path / "custom_licenses"
        custom_dir.mkdir()
        
        # Try to get a non-existent custom license
        result = get_license_text("LicenseRef-NonExistent", tmp_path)
        
        assert result is None
        
        # Check warning message
        captured = capsys.readouterr()
        assert "LicenseRef-NonExistent" in captured.err
        assert "update_custom_licenses" in captured.err

    def test_get_license_text_custom_license_priority(self, tmp_path):
        """Test that custom licenses are checked first for LicenseRef-* identifiers."""
        # Create both custom_licenses and common_licenses directories
        custom_dir = tmp_path / "custom_licenses"
        custom_dir.mkdir()
        common_dir = tmp_path / "common_licenses"
        common_dir.mkdir()
        
        # Put the same license in both directories with different content
        custom_license = custom_dir / "LicenseRef-Test.txt"
        custom_license.write_text("Custom license text")
        
        common_license = common_dir / "LicenseRef-Test.txt"
        common_license.write_text("Common license text")
        
        # Should get the custom version
        result = get_license_text("LicenseRef-Test", tmp_path)
        assert result == "Custom license text"

    def test_spdx_extractor_with_custom_license(self, tmp_path):
        """Test extracting SPDX entries with custom license references."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        
        test_file = src_dir / "test.py"
        test_file.write_text(
            """
# SPDX-FileCopyrightText: Copyright (c) 2025 Test Corp
# SPDX-License-Identifier: LicenseRef-TestProprietary

def test_function():
    pass
"""
        )
        
        extractor = SpdxExtractor([tmp_path], verbose=False)
        file_map = extractor.extract()
        
        # Should extract the entry
        assert len(file_map) == 1
        entry = list(file_map.values())[0]
        
        # Check license type
        licenses = list(entry["licenses"])
        assert len(licenses) == 1
        assert licenses[0].license_type == "LicenseRef-TestProprietary"

    def test_standard_license_not_affected(self, tmp_path):
        """Test that standard SPDX licenses still work normally."""
        # Create directories
        common_dir = tmp_path / "common_licenses"
        common_dir.mkdir()
        custom_dir = tmp_path / "custom_licenses"
        custom_dir.mkdir()
        
        # Put a standard license in common_licenses
        mit_license = common_dir / "MIT.txt"
        mit_license.write_text("MIT License text")
        
        # Should find it normally
        result = get_license_text("MIT", tmp_path)
        assert result == "MIT License text"

    def test_license_ref_with_trailing_markers(self, tmp_path):
        """Test cleaning of LicenseRef identifiers with trailing markers."""
        custom_dir = tmp_path / "custom_licenses"
        custom_dir.mkdir()
        
        license_file = custom_dir / "LicenseRef-Test.txt"
        license_file.write_text("Test license")
        
        # Test with trailing comment markers
        result = get_license_text("LicenseRef-Test  */  ", tmp_path)
        assert result == "Test license"


class TestUpdateCustomLicenses:
    """Test the custom license update functionality."""

    def test_update_custom_licenses_config_not_found(self, tmp_path, capsys):
        """Test handling when config file doesn't exist."""
        from spdx_license_builder.update_custom_licenses import update_custom_licenses
        
        results = update_custom_licenses(tmp_path)
        
        assert results == {}
        captured = capsys.readouterr()
        assert "Configuration file not found" in captured.err

    def test_update_custom_licenses_no_url(self, tmp_path, capsys):
        """Test handling of license entry without URL."""
        from spdx_license_builder.update_custom_licenses import update_custom_licenses
        
        custom_dir = tmp_path / "custom_licenses"
        custom_dir.mkdir()
        
        config_path = custom_dir / "LICENSE_URLS.json"
        config = {
            "LicenseRef-NoURL": {
                "description": "License without URL",
                "last_updated": None
            }
        }
        config_path.write_text(json.dumps(config))
        
        results = update_custom_licenses(tmp_path)
        
        assert results["LicenseRef-NoURL"] is False
        captured = capsys.readouterr()
        assert "No URL configured" in captured.err

    def test_fetch_license_from_url_mock(self, tmp_path):
        """Test fetching license from URL with mocked HTTP request."""
        from spdx_license_builder.update_custom_licenses import fetch_license_from_url
        
        # Mock HTML with sufficient content (needs to be >100 chars after HTML stripping)
        mock_html = """
        <html>
        <body>
        <h1>Test License Agreement</h1>
        <p>This is the license text. This software is provided under the following terms and conditions.
        Permission is hereby granted to use, copy, modify, and distribute this software for any purpose
        with or without fee, provided that the above copyright notice appears in all copies.</p>
        </body>
        </html>
        """
        
        with mock.patch('urllib.request.urlopen') as mock_urlopen:
            mock_response = mock.MagicMock()
            mock_response.read.return_value = mock_html.encode('utf-8')
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response
            
            result = fetch_license_from_url("http://example.com/license", "LicenseRef-Test")
            
            assert result is not None
            assert "Test License Agreement" in result
            assert "This is the license text" in result
            assert "LicenseRef-Test" in result
            assert "http://example.com/license" in result

    def test_fetch_license_from_url_network_error(self, tmp_path, capsys):
        """Test handling of network errors when fetching license."""
        from spdx_license_builder.update_custom_licenses import fetch_license_from_url
        import urllib.error
        
        with mock.patch('urllib.request.urlopen') as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("Network error")
            
            result = fetch_license_from_url("http://example.com/license", "LicenseRef-Test")
            
            assert result is None
            captured = capsys.readouterr()
            assert "Error fetching license" in captured.err

    def test_main_function(self, tmp_path, capsys):
        """Test the main() function."""
        from spdx_license_builder.update_custom_licenses import main
        import sys
        
        # Mock update_custom_licenses to return controlled results
        with mock.patch('spdx_license_builder.update_custom_licenses.update_custom_licenses') as mock_update:
            mock_update.return_value = {
                "LicenseRef-Test1": True,
                "LicenseRef-Test2": False
            }
            
            # Should exit with code 1 when not all succeed
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 1
            
            # The output goes to stdout (print statements)
            captured = capsys.readouterr()
            assert "Updating custom licenses" in captured.out
            assert "1/2 licenses updated successfully" in captured.out

    def test_nvidia_html_parser(self):
        """Test NvidiaLicenseHTMLParser."""
        from spdx_license_builder.update_custom_licenses import NvidiaLicenseHTMLParser
        
        html = """
        <html>
        <body>
        <nav>Skip this</nav>
        <div>Download PDF</div>
        <h1>NVIDIA Software License Agreement</h1>
        <p>License text goes here.</p>
        <p>More license text.</p>
        <footer>Company Information</footer>
        </body>
        </html>
        """
        
        parser = NvidiaLicenseHTMLParser()
        parser.feed(html)
        text = parser.get_text()
        
        assert "NVIDIA Software License Agreement" in text
        assert "License text goes here" in text
        assert "Company Information" not in text

    def test_generic_html_parser(self):
        """Test LicenseHTMLParser."""
        from spdx_license_builder.update_custom_licenses import LicenseHTMLParser
        
        html = """
        <html>
        <head><script>skip this</script></head>
        <body>
        <h1>License Agreement</h1>
        <p>This is the license text.</p>
        </body>
        </html>
        """
        
        parser = LicenseHTMLParser()
        parser.feed(html)
        text = parser.get_text()
        
        assert "License Agreement" in text
        assert "This is the license text" in text
        assert "skip this" not in text

    def test_update_custom_licenses_write_error(self, tmp_path, capsys):
        """Test handling of write errors."""
        from spdx_license_builder.update_custom_licenses import update_custom_licenses
        
        # Create config
        custom_dir = tmp_path / "src" / "spdx_license_builder" / "custom_licenses"
        custom_dir.mkdir(parents=True)
        
        config = {
            "LicenseRef-Test": {
                "url": "http://example.com/license"
            }
        }
        
        config_path = custom_dir / "LICENSE_URLS.json"
        with open(config_path, 'w') as f:
            json.dump(config, f)
        
        # Mock fetch to return content, but make write fail
        with mock.patch('spdx_license_builder.update_custom_licenses.fetch_license_from_url') as mock_fetch:
            mock_fetch.return_value = "License text"
            
            # Make the output file read-only to cause write error
            output_file = custom_dir / "LicenseRef-Test.txt"
            output_file.touch()
            output_file.chmod(0o444)
            
            try:
                results = update_custom_licenses(base_path=tmp_path / "src" / "spdx_license_builder")
                
                # Should fail to write
                assert results["LicenseRef-Test"] is False
            finally:
                # Cleanup
                output_file.chmod(0o644)
