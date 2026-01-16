#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Main entry point when running as: python -m spdx_license_builder
"""

import sys

def main():
    print("SPDX License Builder Tools")
    print("=" * 60)
    print()
    print("Unified CLI (recommended):")
    print("  license-builder extract      - Extract SPDX copyright entries")
    print("  license-builder copy         - Find and extract LICENSE files")
    print()
    print("Legacy commands (still supported):")
    print("  extract-licenses-via-spdx    - Extract SPDX copyright entries")
    print("  find-and-copy-license-files  - Find and extract LICENSE files")
    print()
    print("For help:")
    print("  license-builder --help")
    print("  license-builder extract --help")
    print("  license-builder copy --help")
    print()
    print("Or run as modules:")
    print("  python -m spdx_license_builder.extract_licenses_via_spdx")
    print("  python -m spdx_license_builder.find_and_copy_license_files")

if __name__ == "__main__":
    main()
