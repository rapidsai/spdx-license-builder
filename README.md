# License Builder

Extract and manage license information from projects using SPDX headers and LICENSE files.

## Quick Start

```bash
# Install
pip install spdx-license-builder

# Extract all license information
license-builder /path/to/project --output LICENSE
```

---

## Overview

The `license-builder` tool extracts license information using two complementary methods:

**Note:** By default, copyright year ranges are normalized for better deduplication (e.g., "2020-2023" and "2022-2024" from the same holder are treated as equivalent). Use `--no-normalize-years` to disable this.

### 1. **SPDX Copyright Extraction**

Scans source files for SPDX headers to find third-party code:
- Parses `SPDX-FileCopyrightText` and `SPDX-License-Identifier` tags
- Extracts non-NVIDIA third-party copyright information
- Groups files by copyright holder and license type
- Optionally includes full license texts

### 2. **LICENSE File Copying**

Finds standalone LICENSE files in dependencies:
- Searches for LICENSE files in project directories
- Reads full license text from each file
- Automatically deduplicates identical licenses
- Shows all locations sharing the same license

**By default, both modes run** to provide complete license coverage. Use `--no-extract` or `--no-copy` to disable one.

---

## Usage

### Basic Commands

```bash
# Run both modes (recommended - complete license information)
license-builder /path/to/project --output LICENSE

# SPDX entries only (skip LICENSE file search)
license-builder /path/to/project --no-copy

# LICENSE files only (skip SPDX header scanning)
license-builder /path/to/project --no-extract

# Multiple projects
license-builder /path/to/project1 /path/to/project2 --output LICENSE

# With full license texts for SPDX (extract) entries
license-builder /path/to/project --with-licenses --output LICENSE
```

### Advanced Options

```bash
# Deduplicate RAPIDS project licenses
license-builder /path/to/project --deduplicate-rapids

# Prefer parent directory licenses over child licenses
license-builder /path/to/project --deduplicate-hierarchical

# Disable year normalization (enabled by default)
license-builder /path/to/project --no-normalize-years

# Combine all features
license-builder /path/to/project \\
  --with-licenses \\
  --deduplicate-rapids \\
  --deduplicate-hierarchical \\
  --output LICENSE
```

---

## Output Format

When running both modes (default), the output contains two sections:

### Section 1: SPDX Copyright Entries

Files with third-party code identified by SPDX headers:

```
================================================================================
SECTION 1: Third-Party Code in Source Files (SPDX Entries)
================================================================================

The following files contain third-party code with SPDX copyright headers.

--------------------------------------------------------------------------------
File: Select.cuh
--------------------------------------------------------------------------------

  Locations:
    cudf: cpp/include/cudf/detail/utilities/Select.cuh
    cuml: cpp/src/neighbors/Select.cuh
    raft: cpp/include/raft/neighbors/detail/faiss_select/Select.cuh

  License: Apache-2.0 AND MIT

    Copyright (c) Facebook, Inc. and its affiliates

--------------------------------------------------------------------------------
File: bsd_file.h
--------------------------------------------------------------------------------

  Locations:
    project: cpp/include/bsd_file.h

  License: BSD-3-Clause

    Copyright (c) 2020-2023 Example Corporation
```

**Key features:**
- Files grouped by filename across projects
- Shows all locations where the file appears
- Lists copyright holders and license types
- Optionally includes full license texts (with `--with-licenses`)

### Section 2: Dependency LICENSE Files

Standalone LICENSE files found in dependencies:

```
================================================================================
SECTION 2: Dependency LICENSE Files
================================================================================

The following LICENSE files were found in dependency directories.

--------------------------------------------------------------------------------
  Locations:
    project: cpp/third_party/fmt/LICENSE

  License Text:

    Copyright (c) 2012 - present, Victor Zverovich

    Permission is hereby granted, free of charge, to any person obtaining
    a copy of this software and associated documentation files (the
    "Software"), to deal in the Software without restriction, including
    without limitation the rights to use, copy, modify, merge, publish,
    distribute, sublicense, and/or sell copies of the Software, and to
    permit persons to whom the Software is furnished to do so, subject to
    the following conditions:

    The above copyright notice and this permission notice shall be
    included in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
    LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
    OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
    WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

--------------------------------------------------------------------------------
```

## When to Use Each Mode

| Mode | Use Case | Command |
|------|----------|---------|
| **Both (default)** | Complete license report for distributions | `license-builder /path/to/project` |
| **SPDX only** | Analyze in-tree third-party code | `license-builder /path/to/project --no-copy` |
| **LICENSE only** | Check vendored dependencies | `license-builder /path/to/project --no-extract` |

---

## Installation

```bash
pip install git+https://github.com/rapidsai/spdx-license-builder.git

# OR from clone (dev install)
git clone https://github.com/rapidsai/spdx-license-builder
cd spdx-license-builder
pip install -e .
```

---

## Python API

```python
from pathlib import Path
from spdx_license_builder import LicenseReportBuilder

# Build complete report
builder = LicenseReportBuilder(
    project_paths=[Path("/path/to/project")],
    with_licenses=True,
    deduplicate_rapids=True,
    verbose=True,
)

report = builder.build()

# Write to file
with open("LICENSE", "w") as f:
    report.write(f)

# Access data programmatically
for entry in report.spdx_entries:
    print(f"File: {entry.filename}")
    for license_type, copyrights in entry.licenses.items():
        print(f"  {license_type}: {len(copyrights)} copyright(s)")

for dep_license in report.dependency_licenses:
    print(f"Locations: {dep_license.locations}")
```

---

## License

SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.

SPDX-License-Identifier: Apache-2.0
