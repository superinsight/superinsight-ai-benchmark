#!/usr/bin/env python3
"""
Extract a section from a report JSON file and save as markdown.

Usage:
    # List all sections in a report
    python extract_section.py report.json --list
    
    # Extract a specific section
    python extract_section.py report.json "Claim Information"
    
    # Extract and save to specific file
    python extract_section.py report.json "Claim Information" -o output.md
    
    # Extract from S3 (requires boto3)
    python extract_section.py s3://bucket/report.json "Claim Information"
"""

import json
import sys
import os
from pathlib import Path

# Add src to path for S3 utils
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import click
    from rich.console import Console
    from rich.table import Table
except ImportError:
    # Fallback without rich
    click = None
    Console = None


def is_s3_path(path: str) -> bool:
    """Check if path is an S3 URI."""
    return path.startswith('s3://')


def read_json_file(path: str) -> dict:
    """Read JSON from local path or S3."""
    if is_s3_path(path):
        try:
            from src.utils.s3_utils import S3Client, S3Path
            s3_client = S3Client()
            s3_path = S3Path.parse(path)
            print(f"📥 Downloading from S3: {path}")
            return s3_client.read_json(s3_path.bucket, s3_path.key)
        except ImportError:
            print("Error: boto3 required for S3 support. Run: pip install boto3")
            sys.exit(1)
    else:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)


def list_sections(data: dict) -> None:
    """List all sections in the report."""
    sections = list(data.keys())
    
    if Console:
        console = Console()
        table = Table(title=f"📋 Found {len(sections)} sections")
        table.add_column("#", style="cyan", justify="right")
        table.add_column("Section Name", style="white")
        table.add_column("Draft Size", justify="right", style="dim")
        
        for i, section_name in enumerate(sections, 1):
            section_data = data[section_name]
            draft = section_data.get('draft', '')
            size = f"{len(draft):,} chars" if draft else "(empty)"
            table.add_row(str(i), section_name, size)
        
        console.print(table)
    else:
        print(f"\nFound {len(sections)} sections:\n")
        for i, section_name in enumerate(sections, 1):
            section_data = data[section_name]
            draft = section_data.get('draft', '')
            size = f"{len(draft):,} chars" if draft else "(empty)"
            print(f"  {i}. [{section_name}] - {size}")


def extract_section(data: dict, section_name: str) -> str:
    """Extract draft content from a section."""
    # Try exact match first
    if section_name in data:
        return data[section_name].get('draft', '')
    
    # Try case-insensitive match
    for key in data.keys():
        if key.lower() == section_name.lower():
            return data[key].get('draft', '')
    
    # Try numeric index
    if section_name.isdigit():
        idx = int(section_name) - 1
        sections = list(data.keys())
        if 0 <= idx < len(sections):
            return data[sections[idx]].get('draft', '')
    
    return None


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    # Parse arguments
    json_path = sys.argv[1]
    
    # Check for --list flag
    if '--list' in sys.argv or '-l' in sys.argv:
        data = read_json_file(json_path)
        list_sections(data)
        return
    
    # Need section name
    if len(sys.argv) < 3:
        print("Error: Please provide a section name or use --list to see available sections")
        print(f"\nUsage: {sys.argv[0]} <report.json> <section_name> [-o output.md]")
        sys.exit(1)
    
    section_name = sys.argv[2]
    
    # Check for output file option
    output_file = None
    if '-o' in sys.argv:
        try:
            output_file = sys.argv[sys.argv.index('-o') + 1]
        except IndexError:
            print("Error: -o requires a file path")
            sys.exit(1)
    
    # Read JSON
    print(f"📂 Loading: {json_path}")
    data = read_json_file(json_path)
    
    # Extract section
    content = extract_section(data, section_name)
    
    if content is None:
        print(f"\n❌ Section '{section_name}' not found.")
        print("\nAvailable sections:")
        for i, key in enumerate(data.keys(), 1):
            print(f"  {i}. {key}")
        sys.exit(1)
    
    if not content:
        print(f"\n⚠️  Section '{section_name}' exists but has no draft content.")
        sys.exit(1)
    
    # Output
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Saved to: {output_file}")
        print(f"   Size: {len(content):,} chars")
    else:
        # Print to stdout
        print(content)


if __name__ == '__main__':
    main()
