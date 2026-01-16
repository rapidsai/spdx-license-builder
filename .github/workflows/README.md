# GitHub Actions Workflows

This directory contains CI/CD workflows for the SPDX License Builder project.

## Workflows

### 1. Tests (`tests.yml`)

Runs the test suite on pull requests and pushes to main/master branches.

**Matrix Testing:**
- **Python versions:** 3.8, 3.9, 3.10, 3.11, 3.12
- **Operating systems:** Ubuntu (Linux), macOS, Windows
- **Total combinations:** 15 (5 Python versions × 3 OSes)

**Steps:**
1. Checkout code
2. Set up Python environment
3. Install package with dev dependencies
4. Run test suite with pytest
5. Generate coverage report (Ubuntu + Python 3.12 only)
6. Upload coverage to Codecov (optional)

**Triggers:**
- Push to main/master
- Pull requests to main/master

### 2. Lint (`tests.yml` - lint job)

Checks code quality and formatting.

**Checks:**
- Code formatting with Black
- Linting with Flake8
- Runs on Ubuntu with Python 3.12

**Triggers:**
- Same as tests workflow

### 3. Build (`build.yml`)

Builds distribution packages and tests installation.

**Build Job:**
- Builds wheel and source distribution
- Verifies wheel contents
- Uploads artifacts

**Install Test Job:**
- Tests installation from wheel
- Verifies CLI commands work
- Tests Python imports
- Runs on Ubuntu, macOS, Windows with Python 3.8 and 3.12

**Triggers:**
- Push to main/master
- Pull requests to main/master
- Release events (for future PyPI publishing)

## Status Badges

Add these badges to your README.md:

```markdown
![Tests](https://github.com/msarahan/spdx-license-builder/workflows/Tests/badge.svg)
![Build](https://github.com/msarahan/spdx-license-builder/workflows/Build/badge.svg)
```

## Local Testing

Before pushing, you can run the same checks locally:

```bash
# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=spdx_license_builder --cov-report=term-missing

# Check formatting
black --check src/ tests/

# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Build package
python -m build
```

## Requirements

All required tools are included in the dev dependencies:
- pytest
- pytest-cov
- black
- flake8
- build (for package building)

Install with:
```bash
pip install -e ".[dev]"
```

## Future Enhancements

Potential additions:
- Coverage threshold enforcement
- Automatic PyPI publishing on releases
- Documentation building and deployment
- Security scanning (e.g., Dependabot, CodeQL)
- Performance benchmarking
