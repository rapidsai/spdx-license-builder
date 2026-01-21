# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION.
# SPDX-License-Identifier: Apache-2.0
#

"""
Caching system for license extraction to speed up subsequent runs.

Caches file extraction results based on file modification times.
Only re-scans files that have changed since the last run.
"""

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Set
from dataclasses import dataclass, asdict


@dataclass
class CacheEntry:
    """Cache entry for a single file's extraction results."""
    
    file_path: str
    mtime: float
    size: int
    data: Dict[str, Any]
    
    def is_valid(self, current_mtime: float, current_size: int) -> bool:
        """Check if cache entry is still valid based on file metadata."""
        return self.mtime == current_mtime and self.size == current_size


class ExtractionCache:
    """
    Cache for license extraction results.
    
    Stores extraction results per file along with modification times.
    Only re-extracts files that have changed.
    """
    
    def __init__(self, cache_dir: Optional[Path] = None, enabled: bool = True):
        """
        Initialize the extraction cache.
        
        Args:
            cache_dir: Directory to store cache files. If None, uses ~/.cache/spdx-license-builder
            enabled: Whether caching is enabled
        """
        self.enabled = enabled
        
        if cache_dir is None:
            # Use user's cache directory
            if os.name == 'nt':  # Windows
                cache_base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
            else:  # Unix-like
                cache_base = Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache'))
            
            self.cache_dir = cache_base / 'spdx-license-builder'
        else:
            self.cache_dir = Path(cache_dir)
        
        if self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.cache_file = self.cache_dir / 'extraction_cache.json'
        self.cache_data: Dict[str, CacheEntry] = {}
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'invalidated': 0,
        }
        
        if self.enabled:
            self._load_cache()
    
    def _get_cache_key(self, file_path: str, project_root: Optional[str] = None) -> str:
        """
        Generate a cache key for a file.
        
        Uses relative path if project_root is provided, otherwise absolute path.
        """
        if project_root:
            try:
                rel_path = Path(file_path).relative_to(project_root)
                return f"{project_root}::{rel_path}"
            except ValueError:
                pass
        
        return str(Path(file_path).resolve())
    
    def _load_cache(self) -> None:
        """Load cache from disk."""
        if not self.cache_file.exists():
            return
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert dict entries to CacheEntry objects
            for key, entry_dict in data.items():
                self.cache_data[key] = CacheEntry(**entry_dict)
                
        except (OSError, json.JSONDecodeError, TypeError) as e:
            print(f"Warning: Could not load cache from {self.cache_file}: {e}", file=sys.stderr)
            self.cache_data = {}
    
    def save(self) -> None:
        """Save cache to disk."""
        if not self.enabled:
            return
        
        try:
            # Convert CacheEntry objects to dicts
            data = {key: asdict(entry) for key, entry in self.cache_data.items()}
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                
        except (OSError, TypeError) as e:
            print(f"Warning: Could not save cache to {self.cache_file}: {e}", file=sys.stderr)
    
    def get(self, file_path: str, project_root: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get cached extraction results for a file.
        
        Returns None if file is not in cache or cache is invalid.
        
        Args:
            file_path: Path to the file
            project_root: Optional project root for relative path caching
            
        Returns:
            Cached data if valid, None otherwise
        """
        if not self.enabled:
            return None
        
        cache_key = self._get_cache_key(file_path, project_root)
        
        if cache_key not in self.cache_data:
            self.stats['misses'] += 1
            return None
        
        # Check if file still exists
        path = Path(file_path)
        if not path.exists():
            self.stats['invalidated'] += 1
            del self.cache_data[cache_key]
            return None
        
        # Get current file metadata
        try:
            stat = path.stat()
            current_mtime = stat.st_mtime
            current_size = stat.st_size
        except OSError:
            self.stats['invalidated'] += 1
            del self.cache_data[cache_key]
            return None
        
        # Check if cache entry is still valid
        entry = self.cache_data[cache_key]
        if entry.is_valid(current_mtime, current_size):
            self.stats['hits'] += 1
            return entry.data
        else:
            self.stats['invalidated'] += 1
            del self.cache_data[cache_key]
            return None
    
    def set(self, file_path: str, data: Dict[str, Any], project_root: Optional[str] = None) -> None:
        """
        Store extraction results in cache.
        
        Args:
            file_path: Path to the file
            data: Extraction results to cache
            project_root: Optional project root for relative path caching
        """
        if not self.enabled:
            return
        
        cache_key = self._get_cache_key(file_path, project_root)
        
        try:
            path = Path(file_path)
            stat = path.stat()
            
            self.cache_data[cache_key] = CacheEntry(
                file_path=file_path,
                mtime=stat.st_mtime,
                size=stat.st_size,
                data=data
            )
        except OSError as e:
            print(f"Warning: Could not cache {file_path}: {e}", file=sys.stderr)
    
    def clear(self) -> None:
        """Clear all cached data."""
        self.cache_data.clear()
        if self.enabled and self.cache_file.exists():
            try:
                self.cache_file.unlink()
            except OSError as e:
                print(f"Warning: Could not delete cache file {self.cache_file}: {e}", file=sys.stderr)
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        total = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total * 100) if total > 0 else 0
        
        return {
            **self.stats,
            'total_requests': total,
            'hit_rate_percent': round(hit_rate, 1),
            'cached_files': len(self.cache_data),
        }
    
    def print_stats(self) -> None:
        """Print cache statistics to stderr."""
        if not self.enabled:
            return
        
        stats = self.get_stats()
        
        if stats['total_requests'] > 0:
            print(f"\nCache Statistics:", file=sys.stderr)
            print(f"  Hits: {stats['hits']}", file=sys.stderr)
            print(f"  Misses: {stats['misses']}", file=sys.stderr)
            print(f"  Invalidated: {stats['invalidated']}", file=sys.stderr)
            print(f"  Hit Rate: {stats['hit_rate_percent']}%", file=sys.stderr)
            print(f"  Cached Files: {stats['cached_files']}", file=sys.stderr)


def get_project_cache_key(project_paths: list) -> str:
    """
    Generate a unique cache key for a set of project paths.
    
    Used for caching project-level data like dependency licenses.
    """
    # Sort paths for consistent key generation
    sorted_paths = sorted(str(Path(p).resolve()) for p in project_paths)
    combined = '|'.join(sorted_paths)
    
    # Use hash for shorter key
    return hashlib.sha256(combined.encode()).hexdigest()[:16]
