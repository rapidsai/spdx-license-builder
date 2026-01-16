# License Builder Tools

This repository contains tools for extracting and managing license information from RAPIDS projects.

## Overview

The `license-builder` tool provides three main commands:

### 1. `license-builder all` - Complete License Report (Recommended)

**NEW!** Combines both SPDX extraction and LICENSE file collection into a single comprehensive report.

**What it does:**
- Runs both `extract` and `copy` commands
- Combines output into a single well-formatted license report
- Ideal for generating complete LICENSE files for distributions

**Usage:**
```bash
# Generate complete license report
license-builder all /path/to/project --output LICENSE

# Multiple projects with all features enabled (default)
license-builder all /path/to/project1 /path/to/project2 --output LICENSE
```

**Replaces legacy workflow:**
```bash
# OLD (manual concatenation):
license-builder extract . --with-licenses > SPDX_FRAGMENT
license-builder copy . > DEP_LICENSES
cat LICENSE SPDX_FRAGMENT DEP_LICENSES > FINAL_LICENSE

# NEW (single command):
license-builder all . --output FINAL_LICENSE
```

---

### 2. `license-builder extract` - SPDX Copyright Extractor

Extracts third-party copyright and license information from source code files by parsing SPDX headers.

**What it does:**
- Scans entire project directory for SPDX copyright tags (`SPDX-FileCopyrightText` and `SPDX-License-Identifier`)
- Extracts non-NVIDIA third-party copyright information
- Optionally includes full license texts (fetched from local cache or SPDX API)
- Excludes common non-source directories (build/, test/, .git/, etc.)


### License Caching

License texts are cached in two locations:

- **Bundled licenses** - Common licenses (Apache-2.0, MIT, BSD-3-Clause) are bundled with the package
- **`infrequent_licenses/`** - Dynamically fetched licenses (auto-created in current directory)

When a license is not found in the bundled cache, it's automatically fetched from `http://spdx.org/licenses/[licenseID].json` and cached in `infrequent_licenses/` for future use.

---


**Usage:**

After installation, use the unified command-line tool:
```bash
# Recommended: Complete license report
license-builder all [PROJECT_PATH...] --output LICENSE

# Or use individual commands:
license-builder extract [PROJECT_PATH...] [--with-licenses]
license-builder copy [PROJECT_PATH...]
```

**Examples:**
```bash
# Generate complete license report (recommended)
license-builder all /path/to/project --output LICENSE

# Extract only SPDX copyright entries
license-builder extract /path/to/project --with-licenses --output third_party.txt

# Extract only LICENSE files
license-builder copy /path/to/project --output dependencies.txt

# Scan multiple projects
license-builder all /path/to/project1 /path/to/project2 --output LICENSE
```

**Alternative usage:**
```bash
# Run as Python module
python -m spdx_license_builder all /path/to/project --output LICENSE
python -m spdx_license_builder extract /path/to/project --with-licenses
python -m spdx_license_builder copy /path/to/project
```

**Example output:**
```
================================================================================
Non-NVIDIA Third-Party Licenses for specific files
================================================================================

Files are listed with their associated licenses and copyright holders.

================================================================================
File: Select.cuh
================================================================================

  Locations:
    cudf: cpp/include/cudf/detail/utilities/Select.cuh
    cuml: cpp/src/neighbors/Select.cuh
    raft: cpp/include/raft/neighbors/detail/faiss_select/Select.cuh

  License: Apache-2.0 AND MIT

    Copyright (c) 2019-2024 Facebook, Inc. and its affiliates


================================================================================
File: bsd_file.h
================================================================================

  Locations:
    project: cpp/include/bsd_file.h

  License: BSD-3-Clause

    Copyright (c) 2020-2023 Example Corporation
```

*Note: Files with the same name from multiple projects are grouped together. Copyright dates are merged to show the full range (earliest-latest).*

---

### 2. `license-builder copy` - LICENSE File Extractor

Finds all LICENSE files in project directories and outputs their full contents in a formatted report.

**What it does:**
- Searches for all files starting with "LICENSE" in `c/` and `cpp/` directories
- Identifies which project each LICENSE file belongs to
- Reads the full license text from each file
- Shows all locations that share the same license text together
- Outputs formatted report with full license texts

**Usage:**

After installation, use the unified command-line tool:
```bash
license-builder copy [PROJECT_PATH...]
```

**Examples:**
```bash
# Extract LICENSE files from a single project
license-builder copy /path/to/project

# Extract from multiple projects and combine results
license-builder copy /path/to/project1 /path/to/project2

# Redirect output to a file
license-builder copy /path/to/project --output all_licenses.txt
```

**Alternative usage:**
```bash
# Run as Python module
python -m spdx_license_builder copy /path/to/project
```

**Example output:**
```
================================================================================
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

================================================================================
```

**Output format:**
- File locations organized by project
- Full license text from each LICENSE file
- Automatic deduplication (identical licenses shown once with all locations)


---

## License

SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: Apache-2.0
