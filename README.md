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

### 1. **SPDX Copyright Extraction**

Scans source files for SPDX headers to find third-party code:
- Parses `SPDX-FileCopyrightText` and `SPDX-License-Identifier` tags

### 2. **LICENSE File Copying**

Finds standalone LICENSE files in dependencies:
- Searches for common license file patterns (LICENSE, COPYING, COPYRIGHT, NOTICE)
- Includes build directories where dependencies are typically located
- Reads full license text from each file

**Note:** By default, copyright year ranges are normalized for better deduplication (e.g., "2020-2023" and "2022-2024" from the same holder are treated as equivalent). Use `--no-normalize-years` to disable this.

---

## Usage

### Basic Commands

```bash
# Run both modes (recommended - complete license information)
license-builder /path/to/project --output LICENSE

# Multiple projects
license-builder /path/to/project1 /path/to/project2 --output LICENSE
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
  --deduplicate-rapids \\
  --deduplicate-hierarchical \\
  --output LICENSE
```

---

## Output Format

The tool produces a **unified license-centric format** that groups all information by license identifier, organizing data from both SPDX headers (extract mode) and LICENSE files (copy mode):

### Example 1: License from SPDX Headers Only

When code includes SPDX tags, copyright info is extracted:

```
================================================================================
License: Apache-2.0 AND MIT
================================================================================

Files with SPDX headers:

  Copyright (c) 2019-2023, Facebook, Inc. and its affiliates
    cudf: cpp/include/cudf/detail/utilities/Select.cuh
    cuml: cpp/src/neighbors/Select.cuh
    raft: cpp/include/raft/neighbors/detail/faiss_select/Select.cuh

Full License Text:

  --- Apache-2.0 ---

  Apache License
  Version 2.0, January 2004
  http://www.apache.org/licenses/

  TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

  1. Definitions...
  (full Apache 2.0 license text)

  --- MIT ---

  MIT License

  Permission is hereby granted, free of charge...
  (full MIT license text)
```

### Example 2: License from SPDX Headers + LICENSE Files

When the same license identifier appears in both sources, they are unified:

```
================================================================================
License: BSD-3-Clause
================================================================================

Files with SPDX headers:

  Copyright (c) 2020-2023, Example Corporation
    myproject: cpp/include/bsd_file.h

LICENSE files:

  Copyright (c) 2018-2022, Some BSD Library Contributors
    myproject: cpp/third_party/some_bsd_lib/LICENSE

  Copyright (c) 2015-2023, Another BSD Project
    myproject: build/_deps/another_bsd_lib/COPYING

Full License Text:

  Copyright (c) <year> <owner>.

  Redistribution and use in source and binary forms, with or without
  modification, are permitted provided that the following conditions
  are met...
  (full BSD-3-Clause license text)
```

### Example 3: Detected License from LICENSE File

When LICENSE files contain recognizable license text, they are automatically classified and grouped with SPDX entries of the same type:

```
================================================================================
License: MIT
================================================================================

Files with SPDX headers:

  Copyright (c) 2023, My Company
    myproject: cpp/src/utils.cpp

LICENSE files:

  Copyright (c) 2012 - present, Victor Zverovich
    myproject: cpp/third_party/fmt/LICENSE

  Copyright (c) 2016 - 2024, Gabi Melman
    myproject: build/_deps/spdlog/LICENSE

Full License Text:

  MIT License

  Permission is hereby granted, free of charge, to any person obtaining
  a copy of this software and associated documentation files (the
  "Software"), to deal in the Software without restriction, including
  without limitation the rights to use, copy, modify, merge, publish,
  distribute, sublicense, and/or sell copies of the Software...
  (full MIT license text)
```

### Example 4: Unrecognized LICENSE Files

For LICENSE files with unrecognizable or custom licenses, each is kept separate:

```
================================================================================
License: Unrecognized license: cpp/third_party/custom_lib/LICENSE
================================================================================

LICENSE files:

  Copyright (c) 2024, Custom Corp. All rights reserved.
    myproject: cpp/third_party/custom_lib/LICENSE

Full License Text:

  Custom License Agreement

  Copyright (c) 2024, Custom Corp. All rights reserved.

  This software is provided under the following terms...
  (full custom license text)
```

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
