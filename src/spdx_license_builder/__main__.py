#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Main entry point when running as: python -m spdx_license_builder
"""

from .cli import main

if __name__ == "__main__":
    main()
