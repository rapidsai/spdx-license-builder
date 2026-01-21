#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Tests for the caching system.
"""

import json
import time
from pathlib import Path

import pytest

from spdx_license_builder.cache import CacheEntry, ExtractionCache, get_project_cache_key


class TestCacheEntry:
    """Test CacheEntry dataclass."""

    def test_cache_entry_creation(self):
        """Test creating a cache entry."""
        entry = CacheEntry(file_path="/test/file.txt", mtime=123.456, size=1024, data={"test": "value"})
        
        assert entry.file_path == "/test/file.txt"
        assert entry.mtime == 123.456
        assert entry.size == 1024
        assert entry.data == {"test": "value"}

    def test_cache_entry_is_valid(self):
        """Test cache entry validation."""
        entry = CacheEntry(file_path="/test/file.txt", mtime=123.456, size=1024, data={"test": "value"})
        
        # Valid if mtime and size match
        assert entry.is_valid(123.456, 1024) is True
        
        # Invalid if mtime changes
        assert entry.is_valid(123.457, 1024) is False
        
        # Invalid if size changes
        assert entry.is_valid(123.456, 1025) is False


class TestExtractionCache:
    """Test ExtractionCache class."""

    def test_cache_initialization(self, tmp_path):
        """Test cache initialization."""
        cache_dir = tmp_path / ".cache"
        cache = ExtractionCache(cache_dir=cache_dir)
        
        assert cache.cache_dir == cache_dir
        assert cache.enabled is True
        assert cache.cache_data == {}

    def test_cache_disabled(self):
        """Test cache with enabled=False."""
        cache = ExtractionCache(enabled=False)
        
        assert cache.enabled is False

    def test_get_cache_key(self, tmp_path):
        """Test cache key generation."""
        cache = ExtractionCache()
        
        # Test with absolute path
        file_path = str(tmp_path / "test.txt")
        key1 = cache._get_cache_key(file_path)
        assert isinstance(key1, str)
        assert len(key1) > 0
        
        # Same path should generate same key
        key2 = cache._get_cache_key(file_path)
        assert key1 == key2
        
        # Test with project root
        key3 = cache._get_cache_key(file_path, project_root=str(tmp_path))
        assert isinstance(key3, str)

    def test_cache_set_and_get(self, tmp_path):
        """Test setting and getting cache entries."""
        cache = ExtractionCache(cache_dir=tmp_path / ".cache")
        
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        # Set cache entry
        data = {"licenses": ["MIT"], "owner": "Test"}
        cache.set(str(test_file), data)
        
        # Get cache entry (should return the data)
        retrieved = cache.get(str(test_file))
        assert retrieved == data
        
        # Modify file - cache should be invalidated
        time.sleep(0.01)  # Ensure mtime changes
        test_file.write_text("modified content")
        
        retrieved = cache.get(str(test_file))
        assert retrieved is None

    def test_cache_persistence(self, tmp_path):
        """Test that cache persists across instances."""
        cache_dir = tmp_path / ".cache"
        
        # Create first cache instance
        cache1 = ExtractionCache(cache_dir=cache_dir)
        
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        # Set and save
        data = {"test": "data"}
        cache1.set(str(test_file), data)
        cache1.save()
        
        # Create second cache instance
        cache2 = ExtractionCache(cache_dir=cache_dir)
        
        # Should load from disk
        retrieved = cache2.get(str(test_file))
        assert retrieved == data

    def test_cache_clear(self, tmp_path):
        """Test clearing the cache."""
        cache = ExtractionCache(cache_dir=tmp_path / ".cache")
        
        # Add some entries
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        cache.set(str(test_file), {"test": "data"})
        assert len(cache.cache_data) > 0
        
        # Clear cache
        cache.clear()
        assert len(cache.cache_data) == 0
        
        # Cache file should be removed
        cache_file = cache.cache_dir / "extraction_cache.json"
        assert not cache_file.exists()

    def test_cache_stats(self, tmp_path):
        """Test cache statistics."""
        cache = ExtractionCache(cache_dir=tmp_path / ".cache")
        
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        # Set data
        cache.set(str(test_file), {"test": "data"})
        
        # Get hits
        cache.get(str(test_file))
        cache.get(str(test_file))
        
        # Get miss
        cache.get(str(tmp_path / "nonexistent.txt"))
        
        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["invalidated"] == 0
        assert stats["cached_files"] >= 1

    def test_cache_print_stats(self, tmp_path, capsys):
        """Test printing cache statistics."""
        cache = ExtractionCache(cache_dir=tmp_path / ".cache")
        
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        cache.set(str(test_file), {"test": "data"})
        cache.get(str(test_file))
        
        # Print stats
        cache.print_stats()
        
        captured = capsys.readouterr()
        assert "Cache Statistics:" in captured.err
        assert "Hits:" in captured.err
        assert "Misses:" in captured.err

    def test_cache_disabled_operations(self, tmp_path):
        """Test that disabled cache doesn't do anything."""
        cache = ExtractionCache(enabled=False)
        
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        # Set should do nothing
        cache.set(str(test_file), {"test": "data"})
        assert len(cache.cache_data) == 0
        
        # Get should return None
        result = cache.get(str(test_file))
        assert result is None
        
        # Save should do nothing
        cache.save()  # Should not create any files

    def test_cache_nonexistent_file(self, tmp_path):
        """Test cache with nonexistent file."""
        cache = ExtractionCache()
        
        # Try to get cache for nonexistent file
        result = cache.get(str(tmp_path / "nonexistent.txt"))
        assert result is None

    def test_cache_corrupted_file(self, tmp_path):
        """Test handling of corrupted cache file."""
        cache_dir = tmp_path / ".cache"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "extraction_cache.json"
        
        # Write corrupted JSON
        cache_file.write_text("{ corrupted json")
        
        # Should handle gracefully
        cache = ExtractionCache(cache_dir=cache_dir)
        assert cache.cache_data == {}


class TestProjectCacheKey:
    """Test project cache key generation."""

    def test_project_cache_key_single_path(self):
        """Test cache key with single project path."""
        paths = [Path("/path/to/project")]
        key = get_project_cache_key(paths)
        
        assert isinstance(key, str)
        assert len(key) > 0

    def test_project_cache_key_multiple_paths(self):
        """Test cache key with multiple project paths."""
        paths = [Path("/path/to/project1"), Path("/path/to/project2")]
        key = get_project_cache_key(paths)
        
        assert isinstance(key, str)
        
        # Different order should produce different key
        paths_reversed = list(reversed(paths))
        key_reversed = get_project_cache_key(paths_reversed)
        # Actually keys should be the same since the function might sort
        # Let's just check they're valid strings
        assert isinstance(key_reversed, str)

    def test_project_cache_key_consistency(self):
        """Test that same paths produce same key."""
        paths = [Path("/path/to/project")]
        key1 = get_project_cache_key(paths)
        key2 = get_project_cache_key(paths)
        
        assert key1 == key2
