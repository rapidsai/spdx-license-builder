#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Tests for utility functions.
"""

import pytest
from pathlib import Path
from spdx_license_builder.utility import (
    get_project_relative_path,
    get_license_text,
)


class TestGetProjectRelativePath:
    """Test the get_project_relative_path function."""
    
    def test_c_directory_heuristic(self):
        """Test that files in 'c' directories are detected correctly."""
        file_path = "/home/user/raft/c/include/raft/core.hpp"
        project_name, rel_path = get_project_relative_path(file_path)
        
        assert project_name == "raft"
        assert "c/include/raft/core.hpp" in rel_path
    
    def test_cpp_directory_heuristic(self):
        """Test that files in 'cpp' directories are detected correctly."""
        file_path = "/home/user/cudf/cpp/src/io/csv/reader.cpp"
        project_name, rel_path = get_project_relative_path(file_path)
        
        assert project_name == "cudf"
        assert "cpp/src/io/csv/reader.cpp" in rel_path
    
    def test_src_suffix_heuristic(self):
        """Test that directories with '-src' suffix are detected (higher priority)."""
        file_path = "/home/user/build/fmt-src/include/fmt/core.h"
        project_name, rel_path = get_project_relative_path(file_path)
        
        assert project_name == "fmt"
        assert "include/fmt/core.h" in rel_path
    
    def test_src_suffix_priority_over_cpp(self):
        """Test that -src suffix has priority over c/cpp directories."""
        file_path = "/home/user/build/cuco-src/cpp/include/cuco/hash.hpp"
        project_name, rel_path = get_project_relative_path(file_path)
        
        # Should match -src first, not cpp parent
        assert project_name == "cuco"
        # Path should start after cuco-src
        assert "cpp/include/cuco/hash.hpp" in rel_path
    
    def test_no_project_detected(self):
        """Test files that don't match any heuristic."""
        file_path = "/home/user/random/file.cpp"
        project_name, rel_path = get_project_relative_path(file_path)
        
        assert project_name is None
        assert rel_path == "file.cpp"
    
    def test_nested_cpp_directories(self):
        """Test that only the first cpp/c parent is used."""
        file_path = "/home/user/raft/cpp/src/nested/file.cpp"
        project_name, rel_path = get_project_relative_path(file_path)
        
        assert project_name == "raft"
        # Should capture from the first cpp onwards
        assert "cpp" in rel_path


class TestGetLicenseText:
    """Test the get_license_text function."""
    
    def test_get_common_license(self, tmp_path):
        """Test fetching a license from common_licenses directory."""
        # Create a mock license file
        common_licenses = tmp_path / "common_licenses"
        common_licenses.mkdir()
        
        license_file = common_licenses / "Apache-2.0.txt"
        license_text = "Apache License 2.0 - Full Text"
        license_file.write_text(license_text)
        
        result = get_license_text("Apache-2.0", tmp_path)
        assert result == license_text
    
    def test_get_infrequent_license(self, tmp_path):
        """Test fetching a license from infrequent_licenses directory."""
        common_licenses = tmp_path / "common_licenses"
        common_licenses.mkdir()
        
        infrequent_licenses = tmp_path / "infrequent_licenses"
        infrequent_licenses.mkdir()
        
        license_file = infrequent_licenses / "ISC.txt"
        license_text = "ISC License - Full Text"
        license_file.write_text(license_text)
        
        result = get_license_text("ISC", tmp_path)
        assert result == license_text
    
    def test_common_license_priority(self, tmp_path):
        """Test that common_licenses is checked before infrequent_licenses."""
        common_licenses = tmp_path / "common_licenses"
        common_licenses.mkdir()
        
        infrequent_licenses = tmp_path / "infrequent_licenses"
        infrequent_licenses.mkdir()
        
        # Create same license in both directories
        common_file = common_licenses / "MIT.txt"
        common_file.write_text("MIT from common")
        
        infrequent_file = infrequent_licenses / "MIT.txt"
        infrequent_file.write_text("MIT from infrequent")
        
        result = get_license_text("MIT", tmp_path)
        # Should return from common_licenses
        assert result == "MIT from common"
    
    def test_license_not_found(self, tmp_path):
        """Test handling of license that doesn't exist locally and can't be fetched."""
        common_licenses = tmp_path / "common_licenses"
        common_licenses.mkdir()
        
        # Try to get a license that doesn't exist
        # This will try to fetch from SPDX API, which should fail for invalid license
        result = get_license_text("INVALID-LICENSE-ID-12345", tmp_path)
        assert result is None
    
    def test_clean_license_type(self, tmp_path):
        """Test that license type is cleaned (trailing whitespace, comment markers)."""
        common_licenses = tmp_path / "common_licenses"
        common_licenses.mkdir()
        
        license_file = common_licenses / "BSD-3-Clause.txt"
        license_text = "BSD 3-Clause License"
        license_file.write_text(license_text)
        
        # Test with trailing comment markers and whitespace
        result = get_license_text("BSD-3-Clause  */  ", tmp_path)
        assert result == license_text


class TestCopyrightParsing:
    """Test copyright information extraction."""
    
    def test_parse_simple_copyright(self):
        """Test parsing of simple copyright line."""
        from spdx_license_builder.extract_licenses_via_spdx import extract_copyright_info
        
        line = "Copyright (c) 2020 Example Corporation"
        result = extract_copyright_info(line)
        
        assert result is not None
        years, owner = result
        assert years == "2020"
        assert owner == "Example Corporation"
    
    def test_parse_copyright_with_range(self):
        """Test parsing copyright with year range."""
        from spdx_license_builder.extract_licenses_via_spdx import extract_copyright_info
        
        line = "Copyright (c) 2014-2022 Frank Example"
        result = extract_copyright_info(line)
        
        assert result is not None
        years, owner = result
        assert years == "2014-2022"
        assert owner == "Frank Example"
    
    def test_parse_copyright_no_year(self):
        """Test parsing copyright without year."""
        from spdx_license_builder.extract_licenses_via_spdx import extract_copyright_info
        
        line = "Copyright (c) Facebook, Inc. and its affiliates"
        result = extract_copyright_info(line)
        
        assert result is not None
        years, owner = result
        assert years == ""
        assert owner == "Facebook, Inc. and its affiliates"
    
    def test_parse_copyright_with_parentheses_no_c(self):
        """Test parsing copyright with parentheses but no 'c'."""
        from spdx_license_builder.extract_licenses_via_spdx import extract_copyright_info
        
        line = "Copyright (2019) Sandia Corporation"
        result = extract_copyright_info(line)
        
        assert result is not None
        years, owner = result
        assert years == "2019"
        assert owner == "Sandia Corporation"
    
    def test_parse_copyright_all_rights_reserved(self):
        """Test that 'All rights reserved' is stripped."""
        from spdx_license_builder.extract_licenses_via_spdx import extract_copyright_info
        
        line = "Copyright (c) 2020 Example Corp. All rights reserved."
        result = extract_copyright_info(line)
        
        assert result is not None
        years, owner = result
        assert years == "2020"
        assert owner == "Example Corp"
        assert "All rights reserved" not in owner


class TestLicenseComponentParsing:
    """Test parsing of compound license identifiers."""
    
    def test_parse_single_license(self):
        """Test parsing single license identifier."""
        from spdx_license_builder.extract_licenses_via_spdx import parse_license_components
        
        result = parse_license_components("Apache-2.0")
        assert result == ["Apache-2.0"]
    
    def test_parse_license_with_and(self):
        """Test parsing license with AND operator."""
        from spdx_license_builder.extract_licenses_via_spdx import parse_license_components
        
        result = parse_license_components("Apache-2.0 AND MIT")
        assert len(result) == 2
        assert "Apache-2.0" in result
        assert "MIT" in result
    
    def test_parse_license_with_or(self):
        """Test parsing license with OR operator."""
        from spdx_license_builder.extract_licenses_via_spdx import parse_license_components
        
        result = parse_license_components("MIT OR Apache-2.0")
        assert len(result) == 2
        assert "MIT" in result
        assert "Apache-2.0" in result
    
    def test_parse_license_with_with(self):
        """Test parsing license with WITH operator."""
        from spdx_license_builder.extract_licenses_via_spdx import parse_license_components
        
        result = parse_license_components("Apache-2.0 WITH LLVM-exception")
        assert len(result) == 2
        assert "Apache-2.0" in result
        assert "LLVM-exception" in result
    
    def test_parse_complex_license(self):
        """Test parsing complex compound license."""
        from spdx_license_builder.extract_licenses_via_spdx import parse_license_components
        
        result = parse_license_components("Apache-2.0 AND MIT OR BSD-3-Clause")
        assert len(result) == 3
        assert "Apache-2.0" in result
        assert "MIT" in result
        assert "BSD-3-Clause" in result
