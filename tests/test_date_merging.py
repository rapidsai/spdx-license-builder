#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for date range merging functionality."""

from spdx_license_builder.utility import merge_date_ranges


class TestDateRangeMerging:
    """Test the merge_date_ranges function."""

    def test_merge_continuous_single_years(self):
        """Test merging continuous single years."""
        assert merge_date_ranges(["2023", "2024"]) == "2023-2024"
        assert merge_date_ranges(["2020", "2021", "2022"]) == "2020-2022"

    def test_merge_overlapping_ranges(self):
        """Test merging overlapping date ranges."""
        assert merge_date_ranges(["2023-2024", "2024-2025"]) == "2023-2025"
        assert merge_date_ranges(["2020-2022", "2021-2024"]) == "2020-2024"

    def test_preserve_gaps(self):
        """Test that gaps are preserved."""
        assert merge_date_ranges(["2000-2010", "2012-2025"]) == "2000-2010, 2012-2025"
        assert merge_date_ranges(["2020", "2022", "2024"]) == "2020, 2022, 2024"

    def test_single_year(self):
        """Test single year."""
        assert merge_date_ranges(["2023"]) == "2023"

    def test_single_range(self):
        """Test single range."""
        assert merge_date_ranges(["2023-2025"]) == "2023-2025"

    def test_empty_list(self):
        """Test empty list."""
        assert merge_date_ranges([]) == ""

    def test_mixed_continuous_and_gaps(self):
        """Test mixed continuous and gaps."""
        # 2020-2021 (continuous), gap, 2023-2025 (continuous)
        assert merge_date_ranges(["2020", "2021", "2023", "2024-2025"]) == "2020-2021, 2023-2025"

    def test_unordered_input(self):
        """Test that unordered input is sorted correctly."""
        assert merge_date_ranges(["2025", "2023", "2024"]) == "2023-2025"
        assert merge_date_ranges(["2025-2026", "2020-2021", "2023-2024"]) == "2020-2021, 2023-2026"

    def test_duplicate_years(self):
        """Test handling of duplicate years."""
        assert merge_date_ranges(["2023", "2023", "2024"]) == "2023-2024"
        assert merge_date_ranges(["2023-2024", "2023-2025"]) == "2023-2025"

    def test_adjacent_ranges(self):
        """Test ranges that touch but don't overlap."""
        assert merge_date_ranges(["2020-2022", "2023-2025"]) == "2020-2025"

    def test_invalid_input(self):
        """Test handling of invalid input."""
        # Empty strings should be skipped
        result = merge_date_ranges(["2023", "", "2024"])
        assert result == "2023-2024"

    def test_non_numeric_input(self):
        """Test handling of non-numeric input."""
        # Should skip invalid entries
        result = merge_date_ranges(["invalid", "2023", "2024"])
        assert "2023-2024" in result
