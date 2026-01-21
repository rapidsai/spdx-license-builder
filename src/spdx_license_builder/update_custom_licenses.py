#!/usr/bin/env python3
"""
Script to update custom license texts from their source URLs.

This script fetches license text from configured URLs and caches them locally
in the custom_licenses directory.
"""

import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import html.parser


class NvidiaLicenseHTMLParser(html.parser.HTMLParser):
    """Parse NVIDIA license HTML to extract only the license content."""
    
    def __init__(self):
        super().__init__()
        self.text_content = []
        self.skip_tags = {'script', 'style', 'nav', 'header', 'footer', 'button'}
        self.current_tag = None
        self.capturing = False
        self.found_title = False
        self.last_line = ""
        
    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
            
    def handle_endtag(self, tag):
        self.current_tag = None
        
    def handle_data(self, data):
        if self.current_tag in self.skip_tags:
            return
            
        text = data.strip()
        if not text:
            return
            
        # Start capturing when we find "Download PDF" followed by the license title
        # This indicates we've passed the navigation and are in the license content
        if not self.capturing:
            if "Download PDF" in text:
                # Next substantive line should be the title
                self.found_title = True
            elif self.found_title and "NVIDIA Software License Agreement" == text:
                self.capturing = True
                self.text_content.append(text)
                return
            self.last_line = text
            return
            
        # Stop capturing at footer markers
        if self.capturing and any(marker in text for marker in [
            "Company Information",
            "About Us",
            "News and Events",
            "Popular Links",
            "Follow NVIDIA",
            "Copyright ©",
            "(v. October",  # Version marker at end
            "(v. January",
            "(v. February",
            "(v. March",
            "(v. April",
            "(v. May",
            "(v. June",
            "(v. July",
            "(v. August",
            "(v. September",
            "(v. November",
            "(v. December"
        ]):
            self.capturing = False
            return
            
        # Capture license content
        if self.capturing:
            self.text_content.append(text)
                
    def get_text(self) -> str:
        return '\n'.join(self.text_content)


class LicenseHTMLParser(html.parser.HTMLParser):
    """Generic HTML parser to extract license text content."""
    
    def __init__(self):
        super().__init__()
        self.in_content = False
        self.text_content = []
        self.skip_tags = {'script', 'style', 'nav', 'header', 'footer'}
        self.current_tag = None
        
    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        if tag not in self.skip_tags:
            self.in_content = True
            
    def handle_endtag(self, tag):
        self.current_tag = None
        
    def handle_data(self, data):
        if self.in_content and self.current_tag not in self.skip_tags:
            text = data.strip()
            if text:
                self.text_content.append(text)
                
    def get_text(self) -> str:
        return '\n'.join(self.text_content)


def fetch_license_from_url(url: str, license_id: str) -> Optional[str]:
    """
    Fetch license text from a URL.
    
    Args:
        url: The URL to fetch the license from
        license_id: The license identifier (for context)
        
    Returns:
        The license text, or None if fetching failed
    """
    try:
        print(f"Fetching {license_id} from {url}...")
        
        # Set user agent to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=30) as response:
            html_content = response.read().decode('utf-8')
            
        # Parse HTML to extract text content
        # Use NVIDIA-specific parser for NVIDIA URLs
        if 'nvidia.com' in url.lower():
            parser = NvidiaLicenseHTMLParser()
        else:
            parser = LicenseHTMLParser()
        parser.feed(html_content)
        license_text = parser.get_text()
        
        if not license_text or len(license_text) < 100:
            print(f"Warning: Fetched content seems too short ({len(license_text)} chars)", file=sys.stderr)
            return None
            
        # Add header with source URL and fetch date
        header = f"""# {license_id}
# Fetched from: {url}
# Date: {datetime.now().isoformat()}
# 
# This license text was automatically fetched from the above URL.
# To update, run: python -m spdx_license_builder.update_custom_licenses

{'=' * 80}

"""
        return header + license_text
        
    except urllib.error.URLError as e:
        print(f"Error fetching license from {url}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Unexpected error fetching {license_id}: {e}", file=sys.stderr)
        return None


def update_custom_licenses(base_path: Optional[Path] = None) -> Dict[str, bool]:
    """
    Update all custom licenses from their configured URLs.
    
    Args:
        base_path: Base path to the spdx_license_builder package. 
                   If None, uses the script's parent directory.
                   
    Returns:
        Dictionary mapping license IDs to success status
    """
    if base_path is None:
        base_path = Path(__file__).parent
        
    custom_licenses_dir = base_path / "custom_licenses"
    config_path = custom_licenses_dir / "LICENSE_URLS.json"
    
    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}", file=sys.stderr)
        return {}
        
    # Load configuration
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    results = {}
    
    for license_id, license_info in config.items():
        url = license_info.get('url')
        if not url:
            print(f"Warning: No URL configured for {license_id}", file=sys.stderr)
            results[license_id] = False
            continue
            
        # Fetch license text
        license_text = fetch_license_from_url(url, license_id)
        
        if license_text:
            # Save to file
            output_path = custom_licenses_dir / f"{license_id}.txt"
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(license_text)
                print(f"✓ Updated {license_id} -> {output_path}")
                
                # Update last_updated timestamp in config
                license_info['last_updated'] = datetime.now().isoformat()
                results[license_id] = True
                
            except OSError as e:
                print(f"Error writing {output_path}: {e}", file=sys.stderr)
                results[license_id] = False
        else:
            results[license_id] = False
            
    # Save updated config with timestamps
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
    except OSError as e:
        print(f"Warning: Could not update config file: {e}", file=sys.stderr)
        
    return results


def main():
    """Main entry point for the script."""
    print("Updating custom licenses...")
    print("=" * 80)
    
    results = update_custom_licenses()
    
    print("=" * 80)
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    print(f"\nCompleted: {success_count}/{total_count} licenses updated successfully")
    
    if success_count < total_count:
        sys.exit(1)


if __name__ == "__main__":
    main()
