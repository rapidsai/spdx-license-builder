# Tests for SPDX License Builder

This directory contains the test suite for the SPDX License Builder tools.

## Test Structure

- `test_utility.py` - Tests for utility functions (copyright parsing, path detection, license fetching)
- `test_extract_spdx.py` - Tests for SPDX extraction functionality
- `test_copy_licenses.py` - Tests for LICENSE file copying functionality
- `test_cli.py` - Tests for the unified CLI interface
- `conftest.py` - Shared pytest fixtures and configuration
- `fixtures/` - Test data and sample files

## Running Tests

### Run all tests

```bash
pytest
```

### Run specific test file

```bash
pytest tests/test_utility.py
pytest tests/test_extract_spdx.py
pytest tests/test_copy_licenses.py
pytest tests/test_cli.py
```

### Run specific test class or function

```bash
pytest tests/test_utility.py::TestGetProjectRelativePath
pytest tests/test_utility.py::TestGetProjectRelativePath::test_c_directory_heuristic
```

### Run with verbose output

```bash
pytest -v
```

### Run with coverage

```bash
pytest --cov=spdx_license_builder --cov-report=html
```

## Test Coverage

The test suite covers:

### Core Functionality

1. **Copyright Parsing**
   - Simple copyright lines
   - Copyright with year ranges
   - Copyright without years
   - Multiple copyright holders
   - Handling of "All rights reserved"

2. **License Identification**
   - Single licenses
   - Compound licenses (AND/OR/WITH operators)
   - License text fetching from cache
   - License text fetching from SPDX API

3. **Project Path Detection**
   - Heuristics for c/cpp directories
   - Heuristics for -src suffixes
   - Priority handling (src > cpp)
   - Fallback for unknown paths

### SPDX Extraction (extract mode)

1. **File Scanning**
   - Finding SPDX headers in source files
   - Extracting copyright information
   - Associating copyrights with licenses
   - Filtering out NVIDIA copyrights

2. **Grouping and Organization**
   - Grouping files by license and copyright
   - Multiple files with same license
   - Multiple copyrights in single file
   - Directory exclusion (test, benchmark)

### LICENSE File Copying (copy mode)

1. **File Discovery**
   - Finding LICENSE files in dependencies
   - Supporting various LICENSE file names
   - Directory exclusion rules

2. **Deduplication**
   - Hash-based content comparison
   - Grouping identical licenses
   - Tracking multiple locations for same license
   - Handling license variants

### CLI Interface

1. **Unified Command**
   - Main command help
   - Version display
   - Subcommand routing

2. **Subcommands**
   - extract subcommand functionality
   - copy subcommand functionality
   - Help for each subcommand

3. **Legacy Commands**
   - Backward compatibility
   - extract-licenses-via-spdx
   - find-and-copy-license-files

4. **Error Handling**
   - Invalid project paths
   - Missing subcommands
   - Multiple project paths

## Test Fixtures

The `fixtures/` directory contains sample test data:

- `test_project/` - A sample project structure with:
  - C/C++ source files with SPDX headers
  - Third-party dependencies with LICENSE files
  - Mix of NVIDIA and non-NVIDIA copyrights
  - Various license types (MIT, Apache-2.0, BSD-3-Clause)

## Future Test Enhancements

Tests marked with `pytest.skip()` indicate future enhancements:

1. **Year Normalization**
   - Normalize copyright years for better deduplication
   - Handle year ranges (2020-2023 vs 2022-2024)

2. **RAPIDS/NVIDIA Detection**
   - Identify RAPIDS projects automatically
   - Deduplicate RAPIDS Apache 2.0 licenses

3. **CCCL Special Handling**
   - Detect CCCL root vs sub-component licenses
   - Avoid duplicating CCCL licenses

## Writing New Tests

When adding new tests:

1. Use pytest fixtures from `conftest.py`
2. Create test data in `fixtures/` if needed
3. Follow the existing test structure
4. Add docstrings to explain what each test verifies
5. Use descriptive test names (test_what_is_being_tested)
6. Test both success and failure cases
7. Test edge cases and error conditions

## Dependencies

Tests require:
- `pytest` - Test framework
- `pytest-cov` - Coverage reporting (optional)

Install with:
```bash
pip install -e ".[dev]"
```

## Continuous Integration

Tests should be run on:
- Python 3.8, 3.9, 3.10, 3.11, 3.12
- Multiple operating systems (Linux, macOS, Windows)
- Before merging pull requests
