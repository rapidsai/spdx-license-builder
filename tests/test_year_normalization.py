#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Tests for copyright year normalization.

These tests verify that year normalization correctly:
1. Deduplicates licenses from the same holder with different year ranges
2. Keeps licenses from different holders separate
"""

from spdx_license_builder.deduplication import compute_normalized_hash, normalize_copyright_years


class TestYearNormalization:
    """Test year normalization behavior."""

    def test_same_holder_different_years_should_match(self):
        """
        Licenses from the same holder with different year ranges should deduplicate.

        This is the primary purpose of year normalization - to treat "2020-2023"
        and "2022-2024" as equivalent when they're from the same copyright holder.
        """
        license1 = """Apache License
Version 2.0, January 2004

Copyright (c) 2020-2023, NVIDIA CORPORATION.

Licensed under the Apache License, Version 2.0 (the "License");"""

        license2 = """Apache License
Version 2.0, January 2004

Copyright (c) 2022-2024, NVIDIA CORPORATION.

Licensed under the Apache License, Version 2.0 (the "License");"""

        hash1 = compute_normalized_hash(license1)
        hash2 = compute_normalized_hash(license2)

        # Should match - same holder, only years differ
        assert hash1 == hash2, "Licenses from same holder with different years should deduplicate"

    def test_different_holders_should_not_match(self):
        """
        Licenses from different copyright holders should NOT deduplicate.

        This is critical - year normalization must preserve copyright holder
        information to avoid incorrectly merging licenses.
        """
        license1 = """Apache License
Version 2.0, January 2004

Copyright (c) 2020-2023, Company A.

Licensed under the Apache License, Version 2.0 (the "License");"""

        license2 = """Apache License
Version 2.0, January 2004

Copyright (c) 2022-2024, Company B.

Licensed under the Apache License, Version 2.0 (the "License");"""

        hash1 = compute_normalized_hash(license1)
        hash2 = compute_normalized_hash(license2)

        # Should NOT match - different copyright holders
        assert hash1 != hash2, "Licenses from different holders should NOT deduplicate"

    def test_copyright_holder_name_preserved(self):
        """Verify that copyright holder names are preserved in normalized text."""
        text = "Copyright (c) 2020-2023, NVIDIA CORPORATION."

        normalized = normalize_copyright_years(text)

        # The holder name should still be in the normalized text
        assert "NVIDIA CORPORATION" in normalized, "Copyright holder name must be preserved"

    def test_various_year_formats_normalized(self):
        """Test that various year formats are normalized to consistent placeholders."""
        test_cases = [
            ("Copyright (c) 2020-2023, Owner", "Copyright (c) YYYY, Owner"),
            ("Copyright 2020-2023 Owner", "Copyright YYYY Owner"),
            ("Copyright (c) 2020, 2021, 2022, Owner", "Copyright (c) YYYY, Owner"),
        ]

        for original, expected in test_cases:
            normalized = normalize_copyright_years(original)
            assert (
                expected in normalized or "YYYY" in normalized
            ), f"Year format in '{original}' should be normalized"

    def test_same_holder_same_years_exact_match(self):
        """Identical licenses should have identical hashes."""
        license1 = "Copyright (c) 2020-2023, NVIDIA CORPORATION. Apache 2.0..."
        license2 = "Copyright (c) 2020-2023, NVIDIA CORPORATION. Apache 2.0..."

        hash1 = compute_normalized_hash(license1)
        hash2 = compute_normalized_hash(license2)

        assert hash1 == hash2, "Identical licenses should have identical hashes"
