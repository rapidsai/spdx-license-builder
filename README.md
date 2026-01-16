# License Builder Tools

This repository contains tools for extracting and managing license information from RAPIDS projects.

## Overview

The `license-builder` tool provides two main commands:

### 1. `license-builder extract` - SPDX Copyright Extractor

Extracts third-party copyright and license information from source code files by parsing SPDX headers.
Since RAPIDS build directories are under `cpp/` this can be used to extract dependencies SPDX copyright details as well/

**What it does:**
- Scans source files in `c/` and `cpp/` directories for SPDX copyright tags (`SPDX-FileCopyrightText` and `SPDX-License-Identifier`)
- Extracts non-NVIDIA third-party copyright information
- Optionally includes full license texts (fetched from local cache or SPDX API)


### License Caching

License texts are cached in two locations:

- **Bundled licenses** - Common licenses (Apache-2.0, MIT, BSD-3-Clause) are bundled with the package
- **`infrequent_licenses/`** - Dynamically fetched licenses (auto-created in current directory)

When a license is not found in the bundled cache, it's automatically fetched from `http://spdx.org/licenses/[licenseID].json` and cached in `infrequent_licenses/` for future use.

---


**Usage:**

After installation, use the unified command-line tool:
```bash
license-builder extract [PROJECT_PATH...] [--with-licenses]
```

**Examples:**
```bash
# Scan a single project
license-builder extract /path/to/project

# Add full license texts and write to a file
license-builder extract /path/to/project --with-licenses --output third_party_licenses.txt

# Scan multiple projects
license-builder extract /path/to/project1 /path/to/project2 --with-licenses
```

**Alternative usage:**
```bash
# Run as Python module
python -m spdx_license_builder extract /path/to/project --with-licenses
```

**Example output:**
```
================================================================================
Non-NVIDIA Third-Party Licenses for specific files
================================================================================

Files are listed with their associated licenses and copyright holders.

================================================================================
File: another_facebook_file.cuh
================================================================================

  Locations:
    test_project: cpp/include/another_facebook_file.cuh

  License: Apache-2.0 AND MIT

    Copyright (c) Facebook, Inc. and its affiliates


================================================================================
File: bsd_file.h
================================================================================

  Locations:
    test_project: cpp/include/bsd_file.h

  License: BSD-3-Clause

    Copyright (c) 2020-2023 Example Corporation
```

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
