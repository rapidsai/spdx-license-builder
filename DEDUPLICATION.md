# License Deduplication Features

This document describes the advanced license deduplication features implemented in SPDX License Builder.

## Overview

The tool now includes intelligent deduplication logic to reduce redundant license output, particularly useful for projects with many RAPIDS/NVIDIA dependencies or CCCL components.

## Features

### 1. RAPIDS/NVIDIA Project Detection

**What it does:**
- Automatically detects RAPIDS projects (raft, cudf, cuco, cuml, etc.)
- Deduplicates Apache-2.0 licenses from RAPIDS projects
- Reduces output from multiple identical RAPIDS licenses to a single entry

**Why it's useful:**
- RAPIDS projects all use Apache-2.0 with NVIDIA copyright
- Without deduplication, you get the same license repeated for each RAPIDS dependency
- With deduplication, you get one consolidated entry listing all RAPIDS projects

**Example:**
```bash
# Before: 5 separate Apache-2.0 licenses for raft, cudf, cuco, cuml, cuspatial
# After: 1 Apache-2.0 license listing all 5 projects together
```

**Usage:**
```bash
# Enabled by default
license-builder copy /path/to/project

# Disable if needed
license-builder copy /path/to/project --no-deduplicate-rapids
```

### 2. CCCL Special Handling

**What it does:**
- Detects CCCL (CUDA C++ Core Libraries) structure
- Identifies root LICENSE vs component licenses (thrust, cub, libcudacxx)
- Skips component licenses when root LICENSE exists
- Prevents duplicate CCCL license output

**Why it's useful:**
- CCCL has a root LICENSE that combines all sub-component licenses
- Each sub-component (thrust, cub, libcudacxx) also has its own LICENSE file
- The root LICENSE is a superset of all component licenses
- Without handling, you get the same license text repeated 4 times

**Example:**
```bash
# Before: 4 licenses (CCCL root + thrust + cub + libcudacxx)
# After: 1 license (CCCL root only)
```

**Usage:**
```bash
# Enabled by default
license-builder copy /path/to/project

# Disable if needed
license-builder copy /path/to/project --no-handle-cccl
```

### 3. Copyright Year Normalization

**What it does:**
- Normalizes copyright year ranges in license text
- Replaces specific years (2020-2023, 2022-2024) with placeholders (YYYY)
- Enables deduplication of licenses that differ only in copyright years

**Why it's useful:**
- Projects like cuco and raft have identical Apache-2.0 licenses
- They differ only in copyright years (e.g., "2020-2023" vs "2022-2024")
- Without normalization, these are treated as different licenses
- With normalization, they're recognized as the same license

**Example:**
```bash
# Before:
# - Apache-2.0 with "Copyright (c) 2020-2023, NVIDIA"
# - Apache-2.0 with "Copyright (c) 2022-2024, NVIDIA"
# (Two separate entries)

# After:
# - Apache-2.0 with both projects listed together
# (One entry with both copyright years shown)
```

**Usage:**
```bash
# Enabled by default
license-builder copy /path/to/project

# Disable if needed
license-builder copy /path/to/project --no-normalize-years
```

## Command-Line Options

All deduplication features are **enabled by default** for the best experience.

### Enable/Disable Options

```bash
# All features enabled (default)
license-builder copy /path/to/project

# Disable specific features
license-builder copy /path/to/project --no-deduplicate-rapids
license-builder copy /path/to/project --no-handle-cccl
license-builder copy /path/to/project --no-normalize-years

# Disable all deduplication
license-builder copy /path/to/project \
  --no-deduplicate-rapids \
  --no-handle-cccl \
  --no-normalize-years
```

### Legacy Command

The deduplication features also work with the legacy command:

```bash
find-and-copy-license-files /path/to/project --deduplicate-rapids
```

## Implementation Details

### Project Detection

The tool uses path-based heuristics to detect project types:

- **RAPIDS projects:** Looks for project names in path (raft, cudf, cuco, etc.)
- **CCCL components:** Detects thrust, cub, libcudacxx in paths
- **CCCL root:** Identifies CCCL root LICENSE vs component licenses

### Normalization Algorithm

Year normalization uses regex patterns to replace:
- Year ranges: `2020-2023` → `YYYY-YYYY`
- Multiple years: `2020, 2021, 2022` → `YYYY`
- Single years: `2020` → `YYYY`
- Various copyright formats: `Copyright (c)`, `Copyright (C)`, `Copyright`

### Deduplication Process

1. **Extract licenses** from project directories
2. **Apply CCCL filtering** - Remove component licenses if root exists
3. **Apply RAPIDS deduplication** - Merge RAPIDS Apache-2.0 licenses
4. **Apply year normalization** - Group licenses with normalized years
5. **Output results** - Show deduplicated licenses with all paths

## Supported Projects

### RAPIDS Projects (Auto-detected)
- cudf, cuml, cugraph, cuspatial
- cuxfilter, cucim, raft, cuco
- cupy, rmm, kvikio, ucx-py

### NVIDIA Projects (Auto-detected)
- cccl, cutlass, thrust, cub, libcudacxx
- All RAPIDS projects

### CCCL Components
- thrust
- cub
- libcudacxx

## Testing

All deduplication features are thoroughly tested:

- 21 tests in `tests/test_deduplication.py`
- 7 integration tests in `tests/test_copy_licenses.py`
- 82 total tests, all passing

Run tests:
```bash
pytest tests/test_deduplication.py -v
pytest tests/test_copy_licenses.py::TestRapidsNvidiaDeduplication -v
pytest tests/test_copy_licenses.py::TestLicenseYearNormalization -v
```

## API Usage

You can also use the deduplication functions programmatically:

```python
from spdx_license_builder.deduplication import (
    is_rapids_project,
    is_cccl_component,
    normalize_copyright_years,
    group_licenses_with_deduplication,
)

# Check if a path is a RAPIDS project
if is_rapids_project("/path/to/raft/LICENSE"):
    print("This is a RAPIDS project")

# Normalize copyright years
normalized = normalize_copyright_years("Copyright (c) 2020-2023, NVIDIA")
# Result: "Copyright (c) YYYY, NVIDIA"

# Apply deduplication to license map
deduplicated = group_licenses_with_deduplication(
    content_map,
    use_year_normalization=True,
    deduplicate_rapids=True,
    handle_cccl=True
)
```

## Benefits

### Before Deduplication

A typical RAPIDS project might output:
- 5+ identical Apache-2.0 licenses (one per RAPIDS dependency)
- 4 CCCL licenses (root + 3 components)
- Multiple licenses differing only in years
- **Total: 15-20 redundant license entries**

### After Deduplication

The same project outputs:
- 1 Apache-2.0 license (all RAPIDS projects consolidated)
- 1 CCCL license (root only, components skipped)
- Licenses grouped by normalized content
- **Total: 3-5 unique license entries**

**Result: 70-80% reduction in redundant license output**

## Future Enhancements

Potential future improvements:
- Configurable project lists (custom RAPIDS-like projects)
- More sophisticated year normalization (preserve original years in output)
- License template matching (detect variations of standard licenses)
- Automatic detection of other project ecosystems

## Troubleshooting

### Issue: Licenses not being deduplicated

**Solution:** Check that paths contain recognizable project names:
```bash
# Good: /path/to/raft/LICENSE (will be detected)
# Bad: /path/to/my-raft-fork/LICENSE (won't be detected)
```

### Issue: Want to see all licenses without deduplication

**Solution:** Disable all deduplication features:
```bash
license-builder copy /path/to/project \
  --no-deduplicate-rapids \
  --no-handle-cccl \
  --no-normalize-years
```

### Issue: CCCL components not being skipped

**Solution:** Ensure the CCCL root LICENSE is present in the project. Components are only skipped when the root exists.

## See Also

- `README.md` - General usage documentation
- `tests/test_deduplication.py` - Deduplication test suite
- `src/spdx_license_builder/deduplication.py` - Implementation
