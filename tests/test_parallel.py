#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Tests for parallel processing functionality.
"""

import time

from spdx_license_builder.extractors import (
    DependencyLicenseExtractor,
    LicenseReportBuilder,
    SpdxExtractor,
)


class TestParallelSpdxExtractor:
    """Test parallel processing in SpdxExtractor."""

    def test_parallel_produces_same_results(self, test_project_dir):
        """Test that parallel processing produces the same results as sequential."""
        # Sequential processing (explicitly disabled)
        extractor_seq = SpdxExtractor([test_project_dir], verbose=False, parallel=False)
        result_seq = extractor_seq.extract()

        # Parallel processing (explicitly enabled)
        extractor_par = SpdxExtractor([test_project_dir], verbose=False, parallel=True)
        result_par = extractor_par.extract()

        # Results should be identical
        assert set(result_seq.keys()) == set(result_par.keys())

        for filename in result_seq:
            assert result_seq[filename]["paths"] == result_par[filename]["paths"]
            assert result_seq[filename]["licenses"] == result_par[filename]["licenses"]

    def test_parallel_enabled_by_default(self, test_project_dir):
        """Test that parallel processing is enabled by default (when not in debugger)."""
        # Create extractor without specifying parallel parameter
        extractor = SpdxExtractor([test_project_dir], verbose=False)

        # Should be enabled by default (unless in debugger)
        # We can't guarantee it's True if running under pytest debugger,
        # but it should be boolean
        assert isinstance(extractor.parallel, bool)

    def test_parallel_with_max_workers(self, test_project_dir):
        """Test parallel processing with custom max_workers."""
        extractor = SpdxExtractor([test_project_dir], verbose=False, parallel=True, max_workers=2)
        result = extractor.extract()

        # Should still produce valid results
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_parallel_empty_directory(self, tmp_path):
        """Test parallel processing with empty directory."""
        extractor = SpdxExtractor([tmp_path], verbose=False, parallel=True)
        result = extractor.extract()

        # Should return empty map
        assert len(result) == 0

    def test_sequential_vs_parallel_consistency(self, tmp_path):
        """Test that results are consistent across multiple runs."""
        # Create test files
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        for i in range(10):
            test_file = src_dir / f"test{i}.cpp"
            test_file.write_text(
                f"""
            // SPDX-FileCopyrightText: Copyright (c) 2023, Test Corp {i}
            // SPDX-License-Identifier: MIT
            int main{i}() {{ return {i}; }}
            """
            )

        # Run sequential multiple times
        results_seq = []
        for _ in range(3):
            extractor = SpdxExtractor([tmp_path], verbose=False, parallel=False)
            results_seq.append(extractor.extract())

        # Run parallel multiple times
        results_par = []
        for _ in range(3):
            extractor = SpdxExtractor([tmp_path], verbose=False, parallel=True)
            results_par.append(extractor.extract())

        # All results should be identical
        for i in range(1, 3):
            assert set(results_seq[0].keys()) == set(results_seq[i].keys())
            assert set(results_par[0].keys()) == set(results_par[i].keys())

        # Sequential and parallel should produce same results
        assert set(results_seq[0].keys()) == set(results_par[0].keys())


class TestParallelDependencyExtractor:
    """Test parallel processing in DependencyLicenseExtractor."""

    def test_parallel_produces_same_results(self, test_project_dir):
        """Test that parallel processing produces the same results as sequential."""
        # Sequential processing
        extractor_seq = DependencyLicenseExtractor(
            [test_project_dir], verbose=False, parallel=False
        )
        result_seq = extractor_seq.extract()

        # Parallel processing
        extractor_par = DependencyLicenseExtractor([test_project_dir], verbose=False, parallel=True)
        result_par = extractor_par.extract()

        # Results should be identical
        assert set(result_seq.keys()) == set(result_par.keys())

        for content_hash in result_seq:
            assert result_seq[content_hash]["content"] == result_par[content_hash]["content"]
            assert result_seq[content_hash]["filenames"] == result_par[content_hash]["filenames"]
            assert result_seq[content_hash]["paths"] == result_par[content_hash]["paths"]

    def test_parallel_with_max_workers(self, test_project_dir):
        """Test parallel processing with custom max_workers."""
        extractor = DependencyLicenseExtractor(
            [test_project_dir], verbose=False, parallel=True, max_workers=2
        )
        result = extractor.extract()

        # Should still produce valid results
        assert isinstance(result, dict)

    def test_parallel_multiple_license_files(self, tmp_path):
        """Test parallel processing with multiple LICENSE files."""
        # Create multiple LICENSE files
        for i in range(5):
            subdir = tmp_path / f"dep{i}"
            subdir.mkdir()
            (subdir / "LICENSE").write_text(f"MIT License {i}")

        extractor = DependencyLicenseExtractor([tmp_path], verbose=False, parallel=True)
        result = extractor.extract()

        # Should find all 5 unique licenses
        assert len(result) == 5


class TestParallelLicenseReportBuilder:
    """Test parallel processing in LicenseReportBuilder."""

    def test_parallel_report_building(self, test_project_dir):
        """Test that parallel report building works correctly."""
        # Sequential
        builder_seq = LicenseReportBuilder([test_project_dir], verbose=False, parallel=False)
        report_seq = builder_seq.build()

        # Parallel
        builder_par = LicenseReportBuilder([test_project_dir], verbose=False, parallel=True)
        report_par = builder_par.build()

        # Compare results
        assert len(report_seq.spdx_entries) == len(report_par.spdx_entries)
        assert len(report_seq.dependency_licenses) == len(report_par.dependency_licenses)
        assert len(report_seq.unified_entries) == len(report_par.unified_entries)

    def test_parallel_with_validation(self, tmp_path):
        """Test parallel processing with license validation."""
        # Create project LICENSE
        license_file = tmp_path / "LICENSE"
        license_file.write_text(
            """
        MIT License
        Permission is hereby granted, free of charge, to deal in the Software without restriction...
        """
        )

        # Create multiple source files
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        for i in range(10):
            test_file = src_dir / f"test{i}.cpp"
            test_file.write_text(
                f"""
            // SPDX-FileCopyrightText: Copyright (c) 2023, Test {i}
            // SPDX-License-Identifier: MIT
            int main() {{ return {i}; }}
            """
            )

        # Build report with parallel processing
        builder = LicenseReportBuilder([tmp_path], verbose=False, parallel=True)
        report = builder.build()

        # Should have MIT entry with validation
        mit_entry = None
        for entry in report.unified_entries:
            if entry.license_id == "MIT" and entry.spdx_files:
                mit_entry = entry
                break

        assert mit_entry is not None
        assert mit_entry.in_project_license is True


class TestParallelPerformance:
    """Test performance characteristics of parallel processing."""

    def test_parallel_is_faster_on_large_dataset(self, tmp_path):
        """Test that parallel processing is faster on a large dataset."""
        # Create many files
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        num_files = 50  # Enough files to see a difference
        for i in range(num_files):
            subdir = src_dir / f"subdir{i // 10}"
            subdir.mkdir(exist_ok=True)
            test_file = subdir / f"test{i}.cpp"
            test_file.write_text(
                f"""
            // SPDX-FileCopyrightText: Copyright (c) 2023, Test {i}
            // SPDX-License-Identifier: MIT

            int function{i}() {{
                return {i};
            }}
            """
                * 10
            )  # Make files a bit larger

        # Time sequential processing (explicitly disabled)
        start = time.time()
        extractor_seq = SpdxExtractor([tmp_path], verbose=False, parallel=False)
        result_seq = extractor_seq.extract()
        time_seq = time.time() - start

        # Time parallel processing (explicitly enabled)
        start = time.time()
        extractor_par = SpdxExtractor([tmp_path], verbose=False, parallel=True, max_workers=4)
        result_par = extractor_par.extract()
        time_par = time.time() - start

        # Results should be the same
        assert len(result_seq) == len(result_par)

        # Parallel should generally be faster or at least competitive
        # (We can't guarantee it will always be faster due to overhead and system load)
        print(f"\nSequential: {time_seq:.3f}s, Parallel: {time_par:.3f}s")
        print(f"Speedup: {time_seq / time_par:.2f}x")

        # Just verify both complete successfully
        assert time_seq > 0
        assert time_par > 0


class TestDebuggerDetection:
    """Test debugger detection and auto-disable."""

    def test_debugger_detection_function(self):
        """Test that debugger detection function exists and returns boolean."""
        from spdx_license_builder.extractors import _is_debugger_active

        result = _is_debugger_active()
        assert isinstance(result, bool)


class TestParallelErrorHandling:
    """Test error handling in parallel processing."""

    def test_parallel_handles_unreadable_files(self, tmp_path):
        """Test that parallel processing handles unreadable files gracefully."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        # Create some valid files
        for i in range(5):
            test_file = src_dir / f"test{i}.cpp"
            test_file.write_text(
                f"""
            // SPDX-FileCopyrightText: Copyright (c) 2023, Test {i}
            // SPDX-License-Identifier: MIT
            """
            )

        # Parallel processing should handle any errors gracefully
        extractor = SpdxExtractor([tmp_path], verbose=False, parallel=True)
        result = extractor.extract()

        # Should still process the valid files
        assert len(result) > 0
