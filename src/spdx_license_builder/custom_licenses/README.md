# Custom License References

This directory contains custom license references that are not part of the standard SPDX license list. These are typically proprietary licenses or organization-specific licenses that use the `LicenseRef-*` naming convention.

## Supported Custom Licenses

### LicenseRef-NvidiaProprietary

**Description:** NVIDIA Software License Agreement  
**Source:** https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-software-license-agreement/  
**Usage:** Used in NVIDIA proprietary software components

## Configuration

Custom licenses are configured in `LICENSE_URLS.json`. Each entry specifies:

- `url`: The source URL where the license text can be fetched
- `description`: Human-readable description of the license
- `last_updated`: ISO timestamp of when the license was last fetched (auto-updated)
- `notes`: Additional information about the license

## Updating Custom Licenses

To fetch or update custom licenses from their source URLs:

```bash
# Update all custom licenses
python -m spdx_license_builder.update_custom_licenses

# Or use the CLI command
license-builder-update-custom-licenses
```

This will:
1. Fetch the latest license text from each configured URL
2. Cache the license text locally in this directory
3. Update the `last_updated` timestamp in the configuration

## Adding New Custom Licenses

To add a new custom license:

1. Edit `LICENSE_URLS.json` and add a new entry:

```json
{
  "LicenseRef-YourCustomLicense": {
    "url": "https://example.com/license",
    "description": "Your Custom License",
    "last_updated": null,
    "notes": "Any additional notes"
  }
}
```

2. Run the update script to fetch the license:

```bash
python -m spdx_license_builder.update_custom_licenses
```

3. The license text will be saved as `LicenseRef-YourCustomLicense.txt`

## How It Works

When the license builder encounters a `LicenseRef-*` identifier in source code:

1. It first checks the `custom_licenses` directory for a cached copy
2. If not found, it displays a warning and suggests running the update script
3. The license text is included in the generated license reports

## Periodic Updates

It's recommended to periodically update custom licenses to ensure you have the latest versions:

```bash
# Add to your CI/CD pipeline or run monthly
python -m spdx_license_builder.update_custom_licenses
```

## Notes

- Custom license files are cached locally and committed to the repository
- The HTML parser extracts text content from web pages, which may include navigation elements
- For best results, configure URLs that point directly to license text (not full web pages)
- If a URL becomes unavailable, the cached version will continue to be used
