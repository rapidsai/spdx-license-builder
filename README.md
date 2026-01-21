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

# Extract all license information (outputs to stdout)
license-builder /path/to/project

# Save to file
license-builder /path/to/project --output-json LICENSE.json --output-txt LICENSE.txt
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

When a LICENSE file is recognized, it's automatically grouped with SPDX entries of the same license type for unified reporting.

## **Output**

You can generate up to **two output files** in one run:

1. **User-Friendly** (`--output-txt`): Text format with NVIDIA Apache-2.0 header, then third-party licenses with NVIDIA copyrights filtered
2. **Machine-Friendly** (`--output-json`): **JSON format** with complete listing of all licenses explicitly, including all NVIDIA copyrights

```bash
# Generate both outputs
license-builder /path/to/project --output-json LICENSE_FULL.json --output-txt LICENSE.txt
```

**User-Friendly Format (`--output-txt`, Text):**
- Starts with NVIDIA Copyright and Apache-2.0 license, then shows other third
  party licenses below.
- Uses indentation to group hierarchically: license type, then copyright, then
  files that have that copyright group
- Intended to highlight third-party licenses. NVIDIA copyrights filtered from
  this view. Read this as "everything but the NVIDIA licensed content." The
  top-level Apache2 license implicitly applies to any unlisted file.
- Does not list files that have only an NVIDIA copyright entry

**Machine-Friendly Format (`--output-json`, JSON):**
- All copyrights included (NVIDIA + third-party)
- All files that include copyright information are included
- Machine-parsable for automation and compliance tools

---

### Output Examples

Both outputs produce a **unified license-centric format** that groups all information by license identifier, organizing data from both SPDX headers and LICENSE files. Beneath the license identifier header, files are grouped by their copyright statements, showing all file locations that share the same copyright holder(s) and year range.

#### JSON Output Format

Export license information in JSON format for programmatic processing:

```bash
# Output to file
license-builder /path/to/project --output-json licenses.json
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

#### Text Output Format

##### Example 1: License from SPDX Headers Only

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

##### Example 2: License from SPDX Headers + LICENSE Files

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

##### Example 3: Detected License from LICENSE File

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

##### Example 4: Unrecognized LICENSE Files

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

##### Example 5: Aggregate License Files

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

## Advanced Options

**Custom License References**

The tool supports custom license references (e.g., `LicenseRef-NvidiaProprietary`) that are not part of the standard SPDX license list. These are automatically fetched from configured URLs and cached locally.

```bash
# Update custom licenses from their source URLs
license-builder-update-custom-licenses

# Or use the Python module directly
python -m spdx_license_builder.update_custom_licenses
```

Custom licenses are configured in `src/spdx_license_builder/custom_licenses/LICENSE_URLS.json`. See the [Custom Licenses README](src/spdx_license_builder/custom_licenses/README.md) for details on adding new custom licenses.

**Currently Supported Custom Licenses:**
- `LicenseRef-NvidiaProprietary` - NVIDIA Software License Agreement

**License Exceptions**

The tool supports SPDX license exceptions that modify base licenses using the `WITH` keyword (e.g., `Apache-2.0 WITH LLVM-exception`). Exceptions are automatically combined with their base license text.

```bash
# Example: A file with Apache-2.0 WITH LLVM-exception
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
```

**Supported License Exceptions:**
- `LLVM-exception` - LLVM exception to Apache 2.0 (see [SPDX LLVM-exception](https://spdx.org/licenses/LLVM-exception.html))

The license builder automatically:
1. Recognizes the `WITH` keyword in SPDX identifiers
2. Fetches the base license (e.g., Apache-2.0)
3. Appends the exception text
4. Combines them in the output with a clear separator

---

## Development

### Quick Start

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks (automatically runs checks on commit)
make pre-commit-install

# Run all CI checks locally
make ci-check
```

### Available Make Targets

```bash
make help              # Show all available commands
make lint              # Run ruff linter with auto-fix
make format            # Format code with ruff
make format-check      # Check formatting without modifying files
make test              # Run tests
make test-cov          # Run tests with coverage report
make ci-check          # Run the same checks as CI
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed development guidelines.

---

## License

SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.

SPDX-License-Identifier: Apache-2.0
