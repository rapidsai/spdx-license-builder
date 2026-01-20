# License Builder

Extract and manage license information from projects using SPDX headers and LICENSE files.

## Quick Start

```bash
# Install
pip install git+https://github.com/rapidsai/spdx-license-builder.git

# OR from clone (dev install)
git clone https://github.com/rapidsai/spdx-license-builder
cd spdx-license-builder
pip install -e .

# Extract all license information
license-builder /path/to/project --output LICENSE
```

---

## Overview

The `license-builder` tool extracts license information using two complementary methods:

### 1. **SPDX Copyright Extraction**

Scans source files for SPDX headers to find `SPDX-FileCopyrightText` and
`SPDX-License-Identifier` tags in third-party code.

### 2. **LICENSE File Copying**

Finds standalone LICENSE files in dependencies:
- Searches for common license file patterns (LICENSE, COPYING, COPYRIGHT, NOTICE)
- Includes build directories where dependencies are typically located
- Reads full license text from each file
- **Automatically detects** license type from content and groups with SPDX entries

#### Supported License Detection

The tool automatically recognizes these common licenses from LICENSE file content:
- **Apache-2.0** - Apache License 2.0
- **MIT** - MIT License
- **BSD-2-Clause**, **BSD-3-Clause** - BSD Licenses
- **GPL-2.0-only**, **GPL-3.0-only** - GNU General Public License
- **LGPL-2.1-only**, **LGPL-3.0-only** - GNU Lesser General Public License
- **MPL-2.0** - Mozilla Public License
- **ISC** - ISC License
- **NCSA** - University of Illinois/NCSA License
- **BSL-1.0** - Boost Software License
- **Unlicense** - Public domain dedication
- **Composite license from `<path>`** - Aggregate files containing 2+ distinct licenses (each gets a unique identifier based on its file path)

When a LICENSE file is recognized, it's automatically grouped with SPDX entries of the same license type for unified reporting.

---

## Usage

### Basic Commands

```bash
# Basic usage
license-builder /path/to/project --output LICENSE

# Multiple projects
license-builder /path/to/project1 /path/to/project2 --output LICENSE
```

### Excluding Directories

By default, these directories are automatically excluded: `.git`, `.github`, `dist`, `_build`, `node_modules`, `venv`, `.venv`

You can add additional directories to exclude:

```bash
# Exclude build directories
license-builder /path/to/project --exclude-dirs build _skbuild

# Exclude multiple custom directories
license-builder /path/to/project --exclude-dirs build _skbuild .tox __pycache__
```

### Performance: Parallel Processing

Parallel processing is **enabled by default** for **2-4x faster scanning**:

```bash
# Default: parallel processing enabled
license-builder /path/to/project --output LICENSE

# Specify number of worker threads for very large projects
license-builder /path/to/project --max-workers 8 --output LICENSE

# Disable if needed (automatically disabled when debugging)
license-builder /path/to/project --no-parallel --output LICENSE

# Output in JSON format for programmatic use
license-builder /path/to/project --json --output licenses.json

# Filter out NVIDIA copyrights (for third-party-only reports)
license-builder /path/to/project --exclude-nvidia --output LICENSE
```

---

## Output Format

The tool produces a **unified license-centric format** that groups all information by license identifier, organizing data from both SPDX headers and LICENSE files. Beneath the license identifier header, files are grouped by their copyright statements, showing all file locations that share the same copyright holder and year range.

### JSON Output Format

Export license information in JSON format for programmatic processing:

```bash
# Output to file
license-builder /path/to/project --json --output licenses.json

# Output to stdout
license-builder /path/to/project --json
```

**JSON Structure:**

```json
{
  "licenses": [
    {
      "license_id": "Apache-2.0",
      "spdx_files": [
        {
          "filename": "example.cpp",
          "paths": [{"project": "myproject", "path": "src/example.cpp"}],
          "copyrights": [{"year_range": "2023-2024", "owner": "Example Corp"}]
        }
      ],
      "license_files": [
        {
          "project": "myproject",
          "path": "third_party/lib/LICENSE",
          "copyrights": [{"year_range": "2020-2023", "owner": "Library Authors"}]
        }
      ],
      "license_text": "Apache License\nVersion 2.0...",
      "in_project_license": true,
      "validation_warnings": []
    }
  ],
  "summary": {
    "total_licenses": 3,
    "license_ids": ["Apache-2.0", "MIT", "BSD-3-Clause"]
  }
}
```

**Key Features:**
- **Separated Copyright and Path Information**: Copyrights are in dedicated lists
- **Validation Status**: Includes `in_project_license` and `validation_warnings`
- **Full License Texts**: Complete license text for each license
- **Summary Statistics**: Overview of total licenses and IDs

### Text Output Format

### Example 1: License from SPDX Headers Only

When code includes SPDX tags, copyright info is extracted and grouped by copyright holder:

```
================================================================================
License: Apache-2.0 AND MIT
================================================================================

Files with SPDX headers:

  Copyright (c) 2019-2023, Facebook, Inc. and its affiliates
    cudf: cpp/include/cudf/detail/utilities/Select.cuh
    cuml: cpp/src/neighbors/Select.cuh
    raft: cpp/include/raft/neighbors/detail/faiss_select/Select.cuh

  Copyright (c) 2017-2022, Facebook, Inc. and its affiliates
    cudf: cpp/include/cudf/detail/utilities/WarpSelect.cuh
    raft: cpp/include/raft/neighbors/detail/faiss_select/WarpSelect.cuh

  Copyright (c) 2020-2024, Meta Platforms, Inc.
    cuml: cpp/src/distance/kernels/BlockSelect.cuh

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

When the same license identifier appears in both sources, they are unified and
grouped by copyright (which may include more than one copyright line):

```
================================================================================
License: BSD-3-Clause
================================================================================

Files with SPDX headers:

  Copyright (c) 2020-2023, Example Corporation
    myproject: cpp/include/bsd_file.h
    myproject: cpp/include/utilities/bsd_helper.h

  Copyright (c) 2021, Other Developer
    myproject: cpp/src/bsd_module.cpp

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
    myproject: cpp/src/helpers.cpp

  Copyright (c) 2022-2024, Third Party Contributor
    myproject: cpp/include/contrib/module.h

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

### Example 5: Aggregate License Files

Aggregate LICENSE files containing multiple distinct licenses (like [NVIDIA CCCL](https://github.com/NVIDIA/cccl/blob/main/LICENSE)) are **automatically decomposed** into their constituent licenses:

```
================================================================================
License: Apache-2.0
================================================================================

LICENSE files:

  Copyright (c) 2010-2023, NVIDIA CORPORATION
    myproject: cpp/third_party/cccl/LICENSE

Full License Text:

                                Apache License
                           Version 2.0, January 2004
  ...

================================================================================
License: MIT
================================================================================

LICENSE files:

  Copyright (c) 2009-2014, MIT contributors
    myproject: cpp/third_party/cccl/LICENSE

Full License Text:

  Permission is hereby granted, free of charge...
  ...

================================================================================
License: BSD-3-Clause
================================================================================

LICENSE files:

  Copyright (c) 2009-2019, by the contributors listed in CREDITS.TXT
    myproject: cpp/third_party/cccl/LICENSE

Full License Text:

  Redistribution and use in source and binary forms...
  ...
```

**Note:** The tool extracts each individual license from aggregate LICENSE files and associates the file with each constituent license. This enables proper validation when source files declare specific licenses (e.g., `SPDX-License-Identifier: MIT`) that are part of an aggregate LICENSE.

---

## Python API

```python
from pathlib import Path
from spdx_license_builder import LicenseReportBuilder

# Build complete report
builder = LicenseReportBuilder(
    project_paths=[Path("/path/to/project")],
    with_licenses=True,
    verbose=True,
)

report = builder.build()

# Write to file
with open("LICENSE", "w") as f:
    report.write(f)

# Exclude additional directories
builder = LicenseReportBuilder(
    project_paths=[Path("/path/to/project")],
    with_licenses=True,
    additional_exclude_dirs=("build", "_skbuild"),  # Add to default exclusions
    verbose=True,
)

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
