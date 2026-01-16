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

License texts are cached in two directories:

- **`common_licenses/`** - Frequently used licenses (commited into the project)
- **`infrequent_licenses/`** - Dynamically fetched licenses (auto-created, checked second)

When a license is not found locally, it's automatically fetched from `http://spdx.org/licenses/[licenseID].json` and cached in `infrequent_licenses/`.

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

**Output:** Formatted text report to stdout containing:
- File locations organized by project
- Full license text from each LICENSE file


---

## License

SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: Apache-2.0
