# License Exceptions

This directory contains SPDX license exceptions. License exceptions are modifications or clarifications to base licenses, used with the `WITH` keyword in SPDX expressions.

## SPDX Exception Syntax

License exceptions are used with the `WITH` keyword:
- `Apache-2.0 WITH LLVM-exception`
- `GPL-2.0-only WITH Classpath-exception-2.0`

The exception modifies the base license, not acts as a separate license.

## Supported Exceptions

### LLVM-exception

**Full Name:** LLVM Exception  
**Used With:** Apache-2.0  
**Source:** https://spdx.org/licenses/LLVM-exception.html  
**Description:** Allows embedding compiled portions in Object form without complying with certain Apache 2.0 requirements, and provides additional flexibility when combining with GPLv2 software.

## How Exceptions Work

When the license builder encounters `License WITH Exception`:

1. Fetches the base license text (e.g., Apache-2.0)
2. Appends the exception text to the license
3. The combined text represents the complete license terms

This ensures users see both the base license and the exception that modifies it.

## Adding New Exceptions

To add a new SPDX license exception:

1. Find the exception at https://spdx.org/licenses/exceptions-index.html
2. Create a `.txt` file with the exception identifier as the filename
3. Copy the exception text (not including any base license)
4. The exception will automatically be applied when found in SPDX expressions

## Common Exceptions

- **LLVM-exception** - Used with Apache-2.0 in LLVM projects
- **Classpath-exception-2.0** - Used with GPL in Java projects
- **GCC-exception-3.1** - Used with GPL in GCC
- **Font-exception-2.0** - Used with GPL for font embedding

For a complete list, see https://spdx.org/licenses/exceptions-index.html
