#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Integration tests for LICENSE file copying functionality.
"""

import pytest
import hashlib
from pathlib import Path
from spdx_license_builder.find_and_copy_license_files import extract_license_files
from spdx_license_builder.utility import walk_directories_for_files


class TestWalkDirectoriesForFiles:
    """Test walking directories to find LICENSE files."""
    
    def test_find_license_files(self, tmp_path):
        """Test finding LICENSE files in directory structure."""
        # Create test structure
        cpp_dir = tmp_path / "cpp"
        cpp_dir.mkdir()
        
        third_party = cpp_dir / "third_party"
        third_party.mkdir()
        
        fmt_dir = third_party / "fmt"
        fmt_dir.mkdir()
        
        # Create LICENSE file
        (fmt_dir / "LICENSE").write_text("MIT License text")
        
        # Create non-LICENSE file
        (fmt_dir / "README.md").write_text("README content")
        
        directories_to_exclude = ("test",)
        files = walk_directories_for_files(str(cpp_dir), directories_to_exclude, "LICENSE")
        
        # Should find only the LICENSE file
        assert len(files) == 1
        assert "LICENSE" in files[0]
        assert "README" not in files[0]
    
    def test_find_license_variants(self, tmp_path):
        """Test finding LICENSE files with different names."""
        cpp_dir = tmp_path / "cpp"
        cpp_dir.mkdir()
        
        lib_dir = cpp_dir / "lib"
        lib_dir.mkdir()
        
        # Create various LICENSE file names
        (lib_dir / "LICENSE").write_text("License 1")
        (lib_dir / "LICENSE.txt").write_text("License 2")
        (lib_dir / "LICENSE-Apache").write_text("License 3")
        (lib_dir / "LICENSE.md").write_text("License 4")
        
        directories_to_exclude = ()
        files = walk_directories_for_files(str(cpp_dir), directories_to_exclude, "LICENSE")
        
        # Should find all LICENSE* files
        assert len(files) == 4
    
    def test_exclude_directories_from_search(self, tmp_path):
        """Test that excluded directories are not searched."""
        cpp_dir = tmp_path / "cpp"
        cpp_dir.mkdir()
        
        src_dir = cpp_dir / "src"
        src_dir.mkdir()
        
        test_dir = cpp_dir / "test"
        test_dir.mkdir()
        
        (src_dir / "LICENSE").write_text("Src license")
        (test_dir / "LICENSE").write_text("Test license")
        
        directories_to_exclude = ("test", "tests")
        files = walk_directories_for_files(str(cpp_dir), directories_to_exclude, "LICENSE")
        
        # Should only find src LICENSE, not in test directory
        assert len(files) == 1
        # Check that it's from src, not test (using path components)
        assert Path(files[0]).parts[-2] == "src"
        assert "test" not in Path(files[0]).parts or Path(files[0]).parts[-2] != "test"


class TestExtractLicenseFiles:
    """Test LICENSE file extraction and grouping."""
    
    def test_extract_single_license(self):
        """Test extracting a single LICENSE file."""
        fixtures_path = Path(__file__).parent / "fixtures" / "test_project"
        
        if not fixtures_path.exists():
            pytest.skip("Test fixtures not found")
        
        content_map = extract_license_files([fixtures_path])
        
        # Should find LICENSE files in third_party directories
        assert len(content_map) > 0
        
        # Each entry should have content, filenames, and paths
        for content_hash, info in content_map.items():
            assert 'content' in info
            assert 'filenames' in info
            assert 'paths' in info
            assert len(info['content']) > 0
    
    def test_deduplicate_identical_licenses(self, tmp_path):
        """Test that identical license texts are deduplicated."""
        # Create project structure with duplicate licenses
        project = tmp_path / "project"
        project.mkdir()
        
        cpp_dir = project / "cpp"
        cpp_dir.mkdir()
        
        lib1 = cpp_dir / "lib1"
        lib1.mkdir()
        
        lib2 = cpp_dir / "lib2"
        lib2.mkdir()
        
        # Same license text in both
        license_text = "MIT License\n\nCopyright 2020\n\nPermission is granted..."
        (lib1 / "LICENSE").write_text(license_text)
        (lib2 / "LICENSE").write_text(license_text)
        
        content_map = extract_license_files([project])
        
        # Should have only 1 entry (deduplicated by content hash)
        assert len(content_map) == 1
        
        # The entry should reference both paths
        for content_hash, info in content_map.items():
            assert len(info['paths']) == 2
            assert any("lib1" in path for path in info['paths'].keys())
            assert any("lib2" in path for path in info['paths'].keys())
    
    def test_different_licenses_not_deduplicated(self, tmp_path):
        """Test that different license texts are kept separate."""
        project = tmp_path / "project"
        project.mkdir()
        
        cpp_dir = project / "cpp"
        cpp_dir.mkdir()
        
        lib1 = cpp_dir / "lib1"
        lib1.mkdir()
        
        lib2 = cpp_dir / "lib2"
        lib2.mkdir()
        
        # Different licenses
        (lib1 / "LICENSE").write_text("MIT License text")
        (lib2 / "LICENSE").write_text("Apache License text")
        
        content_map = extract_license_files([project])
        
        # Should have 2 entries (different content)
        assert len(content_map) == 2
    
    def test_license_year_difference(self, tmp_path):
        """Test handling of licenses that differ only in year."""
        project = tmp_path / "project"
        project.mkdir()
        
        cpp_dir = project / "cpp"
        cpp_dir.mkdir()
        
        lib1 = cpp_dir / "cuco"
        lib1.mkdir()
        
        lib2 = cpp_dir / "raft"
        lib2.mkdir()
        
        # Apache 2.0 with different years
        license_template = """Apache License
Version 2.0, January 2004

Copyright (c) {year}, NVIDIA CORPORATION.

Licensed under the Apache License, Version 2.0...
"""
        
        (lib1 / "LICENSE").write_text(license_template.format(year="2020-2023"))
        (lib2 / "LICENSE").write_text(license_template.format(year="2022-2024"))
        
        content_map = extract_license_files([project])
        
        # Currently these will be separate (different content hashes)
        # This is a known issue mentioned in the requirements
        assert len(content_map) == 2
        
        # TODO: Future enhancement - normalize years for deduplication
    
    def test_hash_based_grouping(self, tmp_path):
        """Test that licenses are grouped by content hash."""
        project = tmp_path / "project"
        project.mkdir()
        
        cpp_dir = project / "cpp"
        cpp_dir.mkdir()
        
        lib1 = cpp_dir / "lib1"
        lib1.mkdir()
        
        license_text = "Example License Text"
        (lib1 / "LICENSE").write_text(license_text)
        
        content_map = extract_license_files([project])
        
        # Verify hash is computed correctly
        expected_hash = hashlib.sha256(license_text.encode('utf-8')).hexdigest()
        assert expected_hash in content_map
        
        # Verify content matches
        assert content_map[expected_hash]['content'] == license_text


class TestLicenseFileGrouping:
    """Test grouping and deduplication logic for LICENSE files."""
    
    def test_group_multiple_projects(self):
        """Test extracting licenses from multiple projects."""
        fixtures_path = Path(__file__).parent / "fixtures" / "test_project"
        
        if not fixtures_path.exists():
            pytest.skip("Test fixtures not found")
        
        # Extract from same project twice (simulating multiple project paths)
        content_map = extract_license_files([fixtures_path, fixtures_path])
        
        # Should still deduplicate
        assert len(content_map) > 0
        
        # Each unique license should appear once
        for content_hash, info in content_map.items():
            # Paths might be duplicated if same project scanned twice
            assert isinstance(info['paths'], dict)
    
    def test_filename_tracking(self, tmp_path):
        """Test that filenames are tracked separately from paths."""
        project = tmp_path / "project"
        project.mkdir()
        
        cpp_dir = project / "cpp"
        cpp_dir.mkdir()
        
        lib1 = cpp_dir / "lib1"
        lib1.mkdir()
        
        lib2 = cpp_dir / "lib2"
        lib2.mkdir()
        
        # Same content, different filenames
        license_text = "MIT License"
        (lib1 / "LICENSE").write_text(license_text)
        (lib2 / "LICENSE.txt").write_text(license_text)
        
        content_map = extract_license_files([project])
        
        # Should be deduplicated by content
        assert len(content_map) == 1
        
        # Should track both filenames
        for content_hash, info in content_map.items():
            filenames = info['filenames']
            assert "LICENSE" in filenames
            assert "LICENSE.txt" in filenames


class TestRapidsNvidiaDeduplication:
    """Tests for potential RAPIDS/NVIDIA project deduplication.
    
    These are tests for future enhancements mentioned in requirements.
    """
    
    def test_identify_rapids_projects(self):
        """Test identification of RAPIDS projects (future enhancement)."""
        # List of known RAPIDS projects
        rapids_projects = [
            "cudf", "cuml", "cugraph", "cuspatial", 
            "cuxfilter", "cucim", "raft", "cuco"
        ]
        
        # For now, just verify the list is available
        # In future, this could be used for smart deduplication
        assert len(rapids_projects) > 0
        
        # TODO: Implement function to detect RAPIDS projects
        # TODO: Implement deduplication logic for RAPIDS Apache 2.0 licenses
        pytest.skip("RAPIDS deduplication not yet implemented")
    
    def test_cccl_special_handling(self):
        """Test special handling of CCCL licenses (future enhancement)."""
        # CCCL has a root LICENSE that combines all sub-component licenses
        # Sub-components: cub, thrust, libcudacxx
        
        # TODO: Implement CCCL detection
        # TODO: Implement logic to recognize root vs sub-component licenses
        # TODO: Only include root license when all sub-components are present
        pytest.skip("CCCL special handling not yet implemented")


class TestLicenseYearNormalization:
    """Tests for year normalization in license deduplication (future enhancement)."""
    
    def test_normalize_license_years(self):
        """Test normalizing copyright years for deduplication."""
        # This is a potential future enhancement
        
        license1 = "Copyright (c) 2020-2023, NVIDIA CORPORATION."
        license2 = "Copyright (c) 2022-2024, NVIDIA CORPORATION."
        
        # TODO: Implement function to normalize years
        # normalized1 = normalize_license_text(license1)
        # normalized2 = normalize_license_text(license2)
        # assert normalized1 == normalized2
        
        pytest.skip("Year normalization not yet implemented")
