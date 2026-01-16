#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Pytest configuration and shared fixtures.
"""

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir():
    """Return the path to the test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def test_project_dir(fixtures_dir):
    """Return the path to the test project fixture."""
    return fixtures_dir / "test_project"


@pytest.fixture
def sample_spdx_file(tmp_path):
    """Create a sample file with SPDX headers."""
    test_file = tmp_path / "sample.cpp"
    test_file.write_text(
        """
// SPDX-FileCopyrightText: Copyright (c) 2020 Example Corporation
// SPDX-License-Identifier: MIT

#include <iostream>

int main() {
    std::cout << "Hello, World!" << std::endl;
    return 0;
}
"""
    )
    return test_file


@pytest.fixture
def sample_license_file(tmp_path):
    """Create a sample LICENSE file."""
    license_file = tmp_path / "LICENSE"
    license_file.write_text(
        """MIT License

Copyright (c) 2020 Example Corporation

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
    )
    return license_file


@pytest.fixture
def multi_copyright_file(tmp_path):
    """Create a file with multiple copyright holders."""
    test_file = tmp_path / "multi.cpp"
    test_file.write_text(
        """
// SPDX-FileCopyrightText: Copyright (c) 2019 Company A
// SPDX-FileCopyrightText: Copyright (c) 2020 Company B
// SPDX-FileCopyrightText: Copyright (c) 2021 Company C
// SPDX-License-Identifier: Apache-2.0

void example_function() {
    // Implementation
}
"""
    )
    return test_file


@pytest.fixture
def compound_license_file(tmp_path):
    """Create a file with compound license (AND/OR)."""
    test_file = tmp_path / "compound.cuh"
    test_file.write_text(
        """
// SPDX-FileCopyrightText: Copyright (c) Facebook, Inc. and its affiliates
// SPDX-License-Identifier: Apache-2.0 AND MIT

#ifndef COMPOUND_CUH
#define COMPOUND_CUH

// Dual licensed code

#endif
"""
    )
    return test_file


@pytest.fixture
def nvidia_file(tmp_path):
    """Create a file with NVIDIA copyright (should be ignored)."""
    test_file = tmp_path / "nvidia.cu"
    test_file.write_text(
        """
// SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

__global__ void kernel() {
    // NVIDIA code
}
"""
    )
    return test_file


@pytest.fixture
def common_licenses_dir(tmp_path):
    """Create a common_licenses directory with sample licenses."""
    licenses_dir = tmp_path / "common_licenses"
    licenses_dir.mkdir()

    # Create some common license files
    (licenses_dir / "Apache-2.0.txt").write_text("Apache License 2.0 Full Text...")
    (licenses_dir / "MIT.txt").write_text("MIT License Full Text...")
    (licenses_dir / "BSD-3-Clause.txt").write_text("BSD 3-Clause License Full Text...")

    return licenses_dir
