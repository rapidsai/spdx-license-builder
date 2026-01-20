#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""
Tests for utility functions.
"""

from spdx_license_builder.extractors import SpdxExtractor
from spdx_license_builder.utility import (
    detect_license_type,
    extract_copyright_from_license_text,
    get_license_text,
    get_project_relative_path,
)


class TestGetLicenseText:
    """Test the get_license_text function."""

    def test_get_common_license(self, tmp_path):
        """Test fetching a license from common_licenses directory."""
        # Create a mock license file
        common_licenses = tmp_path / "common_licenses"
        common_licenses.mkdir()

        license_file = common_licenses / "Apache-2.0.txt"
        license_text = "Apache License 2.0 - Full Text"
        license_file.write_text(license_text)

        result = get_license_text("Apache-2.0", tmp_path)
        assert result == license_text

    def test_get_infrequent_license(self, tmp_path):
        """Test fetching a license from infrequent_licenses directory."""
        common_licenses = tmp_path / "common_licenses"
        common_licenses.mkdir()

        infrequent_licenses = tmp_path / "infrequent_licenses"
        infrequent_licenses.mkdir()

        license_file = infrequent_licenses / "ISC.txt"
        license_text = "ISC License - Full Text"
        license_file.write_text(license_text)

        result = get_license_text("ISC", tmp_path)
        assert result == license_text

    def test_common_license_priority(self, tmp_path):
        """Test that common_licenses is checked before infrequent_licenses."""
        common_licenses = tmp_path / "common_licenses"
        common_licenses.mkdir()

        infrequent_licenses = tmp_path / "infrequent_licenses"
        infrequent_licenses.mkdir()

        # Create same license in both directories
        common_file = common_licenses / "MIT.txt"
        common_file.write_text("MIT from common")

        infrequent_file = infrequent_licenses / "MIT.txt"
        infrequent_file.write_text("MIT from infrequent")

        result = get_license_text("MIT", tmp_path)
        # Should return from common_licenses
        assert result == "MIT from common"

    def test_license_not_found(self, tmp_path):
        """Test handling of license that doesn't exist locally and can't be fetched."""
        common_licenses = tmp_path / "common_licenses"
        common_licenses.mkdir()

        # Try to get a license that doesn't exist
        # This will try to fetch from SPDX API, which should fail for invalid license
        result = get_license_text("INVALID-LICENSE-ID-12345", tmp_path)
        assert result is None

    def test_clean_license_type(self, tmp_path):
        """Test that license type is cleaned (trailing whitespace, comment markers)."""
        common_licenses = tmp_path / "common_licenses"
        common_licenses.mkdir()

        license_file = common_licenses / "BSD-3-Clause.txt"
        license_text = "BSD 3-Clause License"
        license_file.write_text(license_text)

        # Test with trailing comment markers and whitespace
        result = get_license_text("BSD-3-Clause  */  ", tmp_path)
        assert result == license_text


class TestCopyrightParsing:
    """Test copyright information extraction."""

    def test_parse_simple_copyright(self):
        """Test parsing of simple copyright line."""
        line = "Copyright (c) 2020 Example Corporation"
        result = SpdxExtractor._extract_copyright_info(line)

        assert result is not None
        years, owner = result
        assert years == "2020"
        assert owner == "Example Corporation"

    def test_parse_copyright_with_range(self):
        """Test parsing copyright with year range."""
        line = "Copyright (c) 2014-2022 Frank Example"
        result = SpdxExtractor._extract_copyright_info(line)

        assert result is not None
        years, owner = result
        assert years == "2014-2022"
        assert owner == "Frank Example"

    def test_parse_copyright_no_year(self):
        """Test parsing copyright without year."""
        line = "Copyright (c) Facebook, Inc. and its affiliates"
        result = SpdxExtractor._extract_copyright_info(line)

        assert result is not None
        years, owner = result
        assert years == ""
        assert owner == "Facebook, Inc. and its affiliates"

    def test_parse_copyright_with_parentheses_no_c(self):
        """Test parsing copyright with parentheses but no 'c'."""
        line = "Copyright (2019) Sandia Corporation"
        result = SpdxExtractor._extract_copyright_info(line)

        assert result is not None
        years, owner = result
        assert years == "2019"
        assert owner == "Sandia Corporation"

    def test_parse_copyright_all_rights_reserved(self):
        """Test that 'All rights reserved' is stripped."""
        line = "Copyright (c) 2020 Example Corp. All rights reserved."
        result = SpdxExtractor._extract_copyright_info(line)

        assert result is not None
        years, owner = result
        assert years == "2020"
        assert owner == "Example Corp"
        assert "All rights reserved" not in owner


class TestLicenseComponentParsing:
    """Test parsing of compound license identifiers."""

    def test_parse_single_license(self):
        """Test parsing single license identifier."""
        result = SpdxExtractor._parse_license_components("Apache-2.0")
        assert result == ["Apache-2.0"]

    def test_parse_license_with_and(self):
        """Test parsing license with AND operator."""
        result = SpdxExtractor._parse_license_components("Apache-2.0 AND MIT")
        assert len(result) == 2
        assert "Apache-2.0" in result
        assert "MIT" in result

    def test_parse_license_with_or(self):
        """Test parsing license with OR operator."""
        result = SpdxExtractor._parse_license_components("MIT OR Apache-2.0")
        assert len(result) == 2
        assert "MIT" in result
        assert "Apache-2.0" in result

    def test_parse_license_with_with(self):
        """Test parsing license with WITH operator."""
        result = SpdxExtractor._parse_license_components("Apache-2.0 WITH LLVM-exception")
        assert len(result) == 2
        assert "Apache-2.0" in result
        assert "LLVM-exception" in result

    def test_parse_complex_license(self):
        """Test parsing complex compound license."""
        result = SpdxExtractor._parse_license_components("Apache-2.0 AND MIT OR BSD-3-Clause")
        assert len(result) == 3
        assert "Apache-2.0" in result
        assert "MIT" in result
        assert "BSD-3-Clause" in result


class TestLicenseDetection:
    """Test automatic license type detection from content."""

    def test_detect_apache_2_0(self):
        """Test detection of Apache-2.0 license."""
        license_text = """
        Apache License
        Version 2.0, January 2004
        http://www.apache.org/licenses/

        TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION
        """
        result = detect_license_type(license_text)
        assert result == "Apache-2.0"

    def test_detect_mit(self):
        """Test detection of MIT license."""
        license_text = """
        MIT License

        Copyright (c) 2020 Example

        Permission is hereby granted, free of charge, to any person obtaining
        a copy of this software and associated documentation files (the
        "Software"), to deal in the Software without restriction, including
        without limitation the rights to use, copy, modify, merge, publish,
        distribute, sublicense, and/or sell copies of the Software.
        """
        result = detect_license_type(license_text)
        assert result == "MIT"

    def test_detect_bsd_3_clause(self):
        """Test detection of BSD-3-Clause license."""
        license_text = """
        Copyright (c) Example Corporation.

        Redistribution and use in source and binary forms, with or without
        modification, are permitted provided that the following conditions are met:

        1. Redistributions of source code must retain the above copyright notice...
        2. Redistributions in binary form must reproduce...
        3. Neither the name of the copyright holder nor the names of its
           contributors may be used to endorse or promote products derived from
           this software without specific prior written permission.
        """
        result = detect_license_type(license_text)
        assert result == "BSD-3-Clause"

    def test_detect_bsd_2_clause(self):
        """Test detection of BSD-2-Clause license."""
        license_text = """
        Copyright (c) Example Corporation.

        Redistribution and use in source and binary forms, with or without
        modification, are permitted provided that the following conditions are met:

        1. Redistributions of source code must retain...
        2. Redistributions in binary form must reproduce the above copyright
           notice, this list of conditions...
        """
        result = detect_license_type(license_text)
        assert result == "BSD-2-Clause"

    def test_detect_gpl_3_0(self):
        """Test detection of GPL-3.0 license."""
        license_text = """
        GNU GENERAL PUBLIC LICENSE
        Version 3, 29 June 2007

        Copyright (C) 2007 Free Software Foundation, Inc.
        """
        result = detect_license_type(license_text)
        assert result == "GPL-3.0-only"

    def test_detect_lgpl_2_1(self):
        """Test detection of LGPL-2.1 license."""
        license_text = """
        GNU LESSER GENERAL PUBLIC LICENSE
        Version 2.1, February 1999

        Copyright (C) 1991, 1999 Free Software Foundation, Inc.
        """
        result = detect_license_type(license_text)
        assert result == "LGPL-2.1-only"

    def test_detect_mpl_2_0(self):
        """Test detection of MPL-2.0 license."""
        license_text = """
        Mozilla Public License Version 2.0
        ==================================

        1. Definitions
        """
        result = detect_license_type(license_text)
        assert result == "MPL-2.0"

    def test_detect_isc(self):
        """Test detection of ISC license."""
        license_text = """
        Copyright (c) Example

        Permission to use, copy, modify, and/or distribute this software for any
        purpose with or without fee is hereby granted, provided that the above
        copyright notice and this permission notice appear in all copies.
        """
        result = detect_license_type(license_text)
        assert result == "ISC"

    def test_detect_unlicense(self):
        """Test detection of Unlicense."""
        license_text = """
        This is free and unencumbered software released into the public domain.

        Anyone is free to copy, modify, publish...
        """
        result = detect_license_type(license_text)
        assert result == "Unlicense"

    def test_detect_boost(self):
        """Test detection of Boost Software License."""
        license_text = """
        Boost Software License - Version 1.0 - August 17th, 2003

        Permission is hereby granted...
        """
        result = detect_license_type(license_text)
        assert result == "BSL-1.0"

    def test_unrecognized_license(self):
        """Test that unrecognized licenses return None."""
        license_text = """
        This is a custom proprietary license that doesn't match
        any known patterns. All rights reserved by Custom Corp.
        """
        result = detect_license_type(license_text)
        assert result is None

    def test_empty_content(self):
        """Test handling of empty license content."""
        result = detect_license_type("")
        assert result is None

    def test_whitespace_normalization(self):
        """Test that detection works with various whitespace."""
        license_text = """
        Apache    License


        Version   2.0,    January    2004
        http://www.apache.org/licenses/
        """
        result = detect_license_type(license_text)
        assert result == "Apache-2.0"


class TestGetProjectRelativePath:
    """Test get_project_relative_path function."""

    def test_simple_path_with_project_root(self, tmp_path):
        """Test simple file path with explicit project root."""
        project_root = tmp_path / "myproject"
        project_root.mkdir()
        file_path = project_root / "src" / "main.cpp"
        file_path.parent.mkdir()
        file_path.touch()

        project_name, rel_path = get_project_relative_path(str(file_path), str(project_root))
        assert project_name == "myproject"
        assert rel_path == "src/main.cpp"

    def test_path_with_c_directory(self, tmp_path):
        """Test path containing /c/ directory."""
        project_root = tmp_path / "build"
        project_root.mkdir()
        c_dir = project_root / "mylib-src" / "c" / "src"
        c_dir.mkdir(parents=True)
        file_path = c_dir / "main.c"
        file_path.touch()

        project_name, rel_path = get_project_relative_path(str(file_path))
        assert project_name == "mylib"
        assert "c/src/main.c" in rel_path

    def test_path_with_cpp_directory(self, tmp_path):
        """Test path containing /cpp/ directory."""
        project_root = tmp_path / "build"
        project_root.mkdir()
        cpp_dir = project_root / "mylib-src" / "cpp" / "include"
        cpp_dir.mkdir(parents=True)
        file_path = cpp_dir / "header.h"
        file_path.touch()

        project_name, rel_path = get_project_relative_path(str(file_path))
        assert project_name == "mylib"
        assert "cpp/include/header.h" in rel_path

    def test_path_without_project_markers(self, tmp_path):
        """Test path without c/cpp or -src markers (line 246 fallback)."""
        # Create a path with no project markers - just a regular nested path
        file_path = tmp_path / "some" / "random" / "path" / "file.txt"
        file_path.parent.mkdir(parents=True)
        file_path.touch()

        project_name, rel_path = get_project_relative_path(str(file_path))
        # When no project markers are found, returns (None, filename)
        assert project_name is None
        assert rel_path == "file.txt"

    def test_path_outside_project_root(self, tmp_path):
        """Test file path outside of project_root (hits line 241-243 ValueError catch)."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        # File is outside the project root
        outside_file = tmp_path / "outside" / "file.txt"
        outside_file.parent.mkdir()
        outside_file.touch()

        project_name, rel_path = get_project_relative_path(str(outside_file), str(project_root))
        # Should fall back to (None, filename) when path is outside project_root
        assert project_name is None
        assert rel_path == "file.txt"

    def test_path_is_just_filename(self, tmp_path):
        """Test when remaining parts result in just a filename (hits line 229)."""
        # Create a structure where after removing parts, only filename remains
        project_root = tmp_path / "build"
        project_root.mkdir()
        src_dir = project_root / "mylib-src"
        src_dir.mkdir()
        file_path = src_dir / "LICENSE"
        file_path.touch()

        project_name, rel_path = get_project_relative_path(str(file_path))
        assert project_name == "mylib"
        # Should return just the filename when no path parts remain
        assert rel_path == "LICENSE"


class TestAggregateLicenseDetection:
    """Test detection of aggregate license files containing multiple licenses."""

    def test_single_license_apache(self):
        """Test that single license files are still detected correctly."""
        license_text = """
        Apache License
        Version 2.0, January 2004
        http://www.apache.org/licenses/

        TERMS AND CONDITIONS...
        """
        result = detect_license_type(license_text)
        assert result == "Apache-2.0"

    def test_single_license_mit(self):
        """Test that single MIT license is detected correctly."""
        license_text = """
        MIT License

        Permission is hereby granted, free of charge, to any person obtaining
        a copy of this software to deal in the Software without restriction...
        """
        result = detect_license_type(license_text)
        assert result == "MIT"

    def test_aggregate_apache_and_mit(self):
        """Test detection of aggregate file with Apache and MIT."""
        license_text = """
        ==============================================================================
        Apache License
        Version 2.0, January 2004
        http://www.apache.org/licenses/

        TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

        1. Definitions...

        ==============================================================================
        MIT License

        Permission is hereby granted, free of charge, to any person obtaining
        a copy of this software to deal in the Software without restriction...
        """
        result = detect_license_type(license_text)
        assert result == "Multiple-Licenses"

    def test_aggregate_apache_mit_bsd(self):
        """Test detection of aggregate file with 3+ licenses (like CCCL)."""
        license_text = """
        ==============================================================================
        Apache License
        Version 2.0, January 2004
        http://www.apache.org/licenses/

        TERMS AND CONDITIONS...

        ==============================================================================
        MIT License

        Permission is hereby granted, free of charge, to any person obtaining
        a copy of this software to deal in the Software without restriction...

        ==============================================================================
        BSD-3-Clause

        Redistribution and use in source and binary forms, with or without
        modification, are permitted provided that neither the name of the
        copyright holder may be used to endorse or promote products...
        """
        result = detect_license_type(license_text)
        assert result == "Multiple-Licenses"

    def test_aggregate_with_boost(self):
        """Test aggregate detection with Boost Software License."""
        license_text = """
        Apache License
        Version 2.0, January 2004

        TERMS AND CONDITIONS...

        ================================================================================
        Boost Software License - Version 1.0 - August 17th, 2003

        Permission is hereby granted, free of charge...
        """
        result = detect_license_type(license_text)
        assert result == "Multiple-Licenses"

    def test_aggregate_apache_with_llvm_exceptions(self):
        """Test CCCL-style file with Apache + LLVM exceptions + other licenses."""
        license_text = """
        ==============================================================================
        Thrust is under the Apache Licence v2.0, with some specific exceptions
        libcu++ is under the Apache License v2.0 with LLVM Exceptions:
        ==============================================================================
        Apache License
        Version 2.0, January 2004
        http://www.apache.org/licenses/

        TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

        ---- LLVM Exceptions to the Apache 2.0 License ----

        ==============================================================================
        University of Illinois/NCSA
        Open Source License

        Permission is hereby granted, free of charge...

        ==============================================================================
        MIT License

        Permission is hereby granted, free of charge, to any person obtaining
        a copy of this software to deal in the Software without restriction...

        ==============================================================================
        Boost Software License - Version 1.0

        Permission is hereby granted...

        ==============================================================================
        BSD-3-Clause

        Redistribution and use in source and binary forms, with or without
        modification, are permitted provided that neither the name may be used
        to endorse or promote products...
        """
        result = detect_license_type(license_text)
        assert result == "Multiple-Licenses"

    def test_bsd_variants_not_double_counted(self):
        """Test that BSD-2 and BSD-3 together count as aggregate."""
        license_text = """
        BSD-3-Clause License

        Redistribution and use in source and binary forms, with or without
        modification, are permitted provided that:
        - Redistributions in binary form must reproduce the above copyright
        - Neither the name of the copyright holder may be used to endorse or promote

        MIT License

        Permission is hereby granted, free of charge, to any person obtaining
        a copy of this software to deal in the Software without restriction...
        """
        result = detect_license_type(license_text)
        assert result == "Multiple-Licenses"


class TestCopyrightExtractionFromLicense:
    """Test extracting copyright statements from LICENSE file content."""

    def test_extract_mit_copyright(self):
        """Test extracting copyright from MIT license."""
        license_text = """MIT License

Copyright (c) 2012 - present, Victor Zverovich

Permission is hereby granted, free of charge..."""

        copyrights = extract_copyright_from_license_text(license_text)
        assert len(copyrights) == 1
        year_range, owner = copyrights[0]
        assert year_range == "2012 - present"
        assert owner == "Victor Zverovich"

    def test_extract_apache_copyright(self):
        """Test extracting copyright from Apache license."""
        license_text = """Apache License
Version 2.0, January 2004
http://www.apache.org/licenses/

Copyright (c) 2020-2023, NVIDIA CORPORATION.

Licensed under the Apache License..."""

        copyrights = extract_copyright_from_license_text(license_text)
        assert len(copyrights) == 1
        year_range, owner = copyrights[0]
        assert year_range == "2020-2023"
        assert "NVIDIA CORPORATION" in owner

    def test_extract_multiple_copyrights(self):
        """Test extracting multiple copyright statements."""
        license_text = """License Agreement

Copyright (c) 2015, First Company
Copyright (c) 2018-2020, Second Company

All rights reserved..."""

        copyrights = extract_copyright_from_license_text(license_text)
        assert len(copyrights) == 2
        year1, owner1 = copyrights[0]
        assert year1 == "2015"
        assert "First Company" in owner1
        year2, owner2 = copyrights[1]
        assert year2 == "2018-2020"
        assert "Second Company" in owner2

    def test_extract_copyright_no_year(self):
        """Test extracting copyright without year."""
        license_text = """Custom License

Copyright (c) Example Corporation

Terms and conditions..."""

        copyrights = extract_copyright_from_license_text(license_text)
        assert len(copyrights) == 1
        year_range, owner = copyrights[0]
        assert year_range == ""
        assert owner == "Example Corporation"

    def test_extract_copyright_no_parens(self):
        """Test extracting copyright without parentheses."""
        license_text = """License

Copyright 2019-2023 Test Company Inc.

Permission is hereby granted..."""

        copyrights = extract_copyright_from_license_text(license_text)
        assert len(copyrights) == 1
        year_range, owner = copyrights[0]
        assert year_range == "2019-2023"
        assert owner == "Test Company Inc."

    def test_extract_copyright_all_rights_reserved(self):
        """Test that 'All rights reserved' is properly handled."""
        license_text = """License

Copyright (c) 2024, Custom Corp. All rights reserved.

Terms..."""

        copyrights = extract_copyright_from_license_text(license_text)
        assert len(copyrights) == 1
        year_range, owner = copyrights[0]
        assert year_range == "2024"
        # "All rights reserved" should be stripped
        assert "All rights reserved" not in owner
        assert "Custom Corp" in owner

    def test_no_copyright_found(self):
        """Test handling license with no copyright statement."""
        license_text = """Public Domain

This software has been released to the public domain.
No copyright claimed."""

        copyrights = extract_copyright_from_license_text(license_text)
        assert len(copyrights) == 0

    def test_copyright_beyond_first_20_lines(self):
        """Test that copyright beyond first 20 lines is not extracted."""
        lines = ["Line " + str(i) for i in range(25)]
        lines[22] = "Copyright (c) 2024, Far Down Company"
        license_text = "\n".join(lines)

        copyrights = extract_copyright_from_license_text(license_text)
        # Should not find it since it's beyond line 20
        assert len(copyrights) == 0

    def test_copyright_invalid_year_format_rejected(self):
        """Test that invalid year formats are rejected (tests validate_years on line 83)."""
        # This tests the validate_years check that rejects non-digit year strings
        license_text = """
Copyright January 2024, Some Company

Permission is hereby granted..."""

        copyrights = extract_copyright_from_license_text(license_text)
        # Should reject "January" as it's not a valid year format
        assert len(copyrights) == 0

    def test_copyright_mixed_valid_invalid(self):
        """Test file with both valid and invalid copyright formats."""
        license_text = """
Copyright (c) 2020-2023, Valid Company

Copyright Invalid Format Here, Bad Company

Copyright 2024, Another Valid Company

Permission is hereby granted..."""

        copyrights = extract_copyright_from_license_text(license_text)
        # Should find only the valid ones
        assert len(copyrights) == 2
        assert ("2020-2023", "Valid Company") in copyrights
        assert ("2024", "Another Valid Company") in copyrights

    def test_copyright_year_with_text_rejected(self):
        """Test that years mixed with non-digit text are rejected."""
        license_text = """
Copyright Year2024, Some Company
Copyright 2024Year, Another Company

Permission is hereby granted..."""

        copyrights = extract_copyright_from_license_text(license_text)
        # These should be rejected as invalid year formats
        assert len(copyrights) == 0
