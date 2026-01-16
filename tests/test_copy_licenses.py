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
    """Tests for RAPIDS/NVIDIA project deduplication."""
    
    def test_identify_rapids_projects(self):
        """Test identification of RAPIDS projects."""
        from spdx_license_builder.deduplication import is_rapids_project, RAPIDS_PROJECTS
        
        # Test known RAPIDS projects
        assert len(RAPIDS_PROJECTS) > 0
        
        # Test path detection
        assert is_rapids_project("/path/to/raft/cpp/src/file.cpp")
        assert is_rapids_project("/build/cudf-src/include/header.h")
        assert is_rapids_project("/home/user/cuco/LICENSE")
        
        # Test non-RAPIDS paths
        assert not is_rapids_project("/path/to/random/file.cpp")
        assert not is_rapids_project("/home/user/myproject/src/code.cpp")
    
    def test_deduplicate_rapids_licenses(self, tmp_path):
        """Test deduplication of RAPIDS Apache 2.0 licenses."""
        from spdx_license_builder.deduplication import should_deduplicate_rapids_license
        
        apache_license = """Apache License
Version 2.0, January 2004

Copyright (c) 2020-2023, NVIDIA CORPORATION.

Licensed under the Apache License, Version 2.0..."""
        
        # RAPIDS paths should be deduplicated
        rapids_paths = {
            "/path/to/raft/LICENSE",
            "/path/to/cudf/LICENSE"
        }
        assert should_deduplicate_rapids_license(rapids_paths, apache_license)
        
        # Mixed RAPIDS and non-RAPIDS should not be deduplicated
        mixed_paths = {
            "/path/to/raft/LICENSE",
            "/path/to/other/LICENSE"
        }
        assert not should_deduplicate_rapids_license(mixed_paths, apache_license)
        
        # Non-Apache license should not be deduplicated
        mit_license = "MIT License..."
        assert not should_deduplicate_rapids_license(rapids_paths, mit_license)
    
    def test_cccl_special_handling(self):
        """Test special handling of CCCL licenses."""
        from spdx_license_builder.deduplication import (
            is_cccl_component,
            is_cccl_root,
            should_skip_cccl_component_license
        )
        
        # Test component detection
        assert is_cccl_component("/path/to/cccl/thrust/LICENSE") == "thrust"
        assert is_cccl_component("/path/to/cccl/cub/LICENSE") == "cub"
        assert is_cccl_component("/path/to/cccl/libcudacxx/LICENSE") == "libcudacxx"
        assert is_cccl_component("/path/to/other/LICENSE") is None
        
        # Test root detection
        assert is_cccl_root("/path/to/cccl/LICENSE")
        assert is_cccl_root("/build/cccl-src/LICENSE")
        assert not is_cccl_root("/path/to/cccl/thrust/LICENSE")
        assert not is_cccl_root("/path/to/other/LICENSE")
        
        # Test skip logic
        all_paths = {
            "/path/to/cccl/LICENSE",
            "/path/to/cccl/thrust/LICENSE",
            "/path/to/cccl/cub/LICENSE"
        }
        
        # Component should be skipped when root exists
        assert should_skip_cccl_component_license("/path/to/cccl/thrust/LICENSE", all_paths)
        assert should_skip_cccl_component_license("/path/to/cccl/cub/LICENSE", all_paths)
        
        # Root should not be skipped
        assert not should_skip_cccl_component_license("/path/to/cccl/LICENSE", all_paths)
        
        # Without root, components should not be skipped
        paths_no_root = {
            "/path/to/cccl/thrust/LICENSE",
            "/path/to/cccl/cub/LICENSE"
        }
        assert not should_skip_cccl_component_license("/path/to/cccl/thrust/LICENSE", paths_no_root)


class TestLicenseYearNormalization:
    """Tests for year normalization in license deduplication."""
    
    def test_normalize_copyright_years(self):
        """Test normalizing copyright years for deduplication."""
        from spdx_license_builder.deduplication import normalize_copyright_years
        
        # Year ranges should be normalized
        license1 = "Copyright (c) 2020-2023, NVIDIA CORPORATION."
        license2 = "Copyright (c) 2022-2024, NVIDIA CORPORATION."
        
        normalized1 = normalize_copyright_years(license1)
        normalized2 = normalize_copyright_years(license2)
        
        # Both should have the same normalized form
        assert normalized1 == normalized2
        assert "YYYY" in normalized1
        assert "2020" not in normalized1
        assert "2023" not in normalized1
    
    def test_normalize_various_formats(self):
        """Test normalization of various copyright year formats."""
        from spdx_license_builder.deduplication import normalize_copyright_years
        
        test_cases = [
            ("Copyright (c) 2020 Company", "Copyright (c) YYYY Company"),
            ("Copyright (C) 2020-2023 Company", "Copyright (c) YYYY Company"),
            ("Copyright 2020 Company", "Copyright YYYY Company"),
            ("Copyright (c) 2020, 2021, 2022 Company", "Copyright (c) YYYY Company"),
        ]
        
        for original, expected in test_cases:
            result = normalize_copyright_years(original)
            assert "YYYY" in result
            # Year should be replaced
            assert not any(str(year) in result for year in range(2000, 2030))
    
    def test_compute_normalized_hash(self):
        """Test that normalized hashes match for licenses differing only in years."""
        from spdx_license_builder.deduplication import compute_normalized_hash
        
        license1 = """Apache License
Copyright (c) 2020-2023, NVIDIA CORPORATION.
Licensed under the Apache License..."""
        
        license2 = """Apache License
Copyright (c) 2022-2024, NVIDIA CORPORATION.
Licensed under the Apache License..."""
        
        # Hashes should match after normalization
        hash1 = compute_normalized_hash(license1)
        hash2 = compute_normalized_hash(license2)
        
        assert hash1 == hash2
    
    def test_group_licenses_with_year_normalization(self, tmp_path):
        """Test grouping licenses with year normalization enabled."""
        from spdx_license_builder.deduplication import group_licenses_with_deduplication
        import hashlib
        
        license_template = """Apache License
Copyright (c) {year}, NVIDIA CORPORATION.
Licensed under the Apache License, Version 2.0..."""
        
        license1 = license_template.format(year="2020-2023")
        license2 = license_template.format(year="2022-2024")
        
        # Create content map with two licenses differing only in years
        content_map = {
            hashlib.sha256(license1.encode()).hexdigest(): {
                'content': license1,
                'filenames': {'LICENSE'},
                'paths': {'/path1/LICENSE': 'path1/LICENSE'}
            },
            hashlib.sha256(license2.encode()).hexdigest(): {
                'content': license2,
                'filenames': {'LICENSE'},
                'paths': {'/path2/LICENSE': 'path2/LICENSE'}
            }
        }
        
        # With year normalization, should be deduplicated
        result = group_licenses_with_deduplication(
            content_map,
            use_year_normalization=True,
            deduplicate_rapids=False,
            handle_cccl=False
        )
        
        # Should be merged into one
        assert len(result) == 1
        
        # Should have both paths
        for info in result.values():
            assert len(info['paths']) == 2
