# License Builder Tools

This repository contains tools for extracting and managing license information from RAPIDS projects.

## Overview

There are two main scripts with different purposes:

### 1. `extract_licenses_via_spdx.py` - SPDX Copyright Extractor

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
```bash
./extract_licenses_via_spdx.py [PROJECT_PATH...] [--with-licenses]
```

**Examples:**
```bash
# Scan a single project
./extract_licenses_via_spdx.py /path/to/project

# Add full license texts and output to a file
./extract_licenses_via_spdx.py /path/to/project --with-licenses > third_party_licenses.txt
```

---

### 2. `find_and_copy_license_files.py` - LICENSE File Extractor

Finds all LICENSE files in project directories and outputs their full contents in a formatted report.

**What it does:**
- Searches for all files starting with "LICENSE" in `c/` and `cpp/` directories
- Identifies which project each LICENSE file belongs to
- Reads the full license text from each file
- Shows all locations that share the same license text together
- Outputs formatted report with full license texts

**Usage:**
```bash
./find_and_copy_license_files.py [PROJECT_PATH...]
```

**Examples:**
```bash
# Extract LICENSE files from a single project
./find_and_copy_license_files.py /path/to/project

# Extract from multiple projects and combine results
./find_and_copy_license_files.py /path/to/project1 /path/to/project2

# Redirect output to a file
./find_and_copy_license_files.py /path/to/project > all_licenses.txt
```

**Output:** Formatted text report to stdout containing:
- File locations organized by project
- Full license text from each LICENSE file


---

## License

SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: Apache-2.0

