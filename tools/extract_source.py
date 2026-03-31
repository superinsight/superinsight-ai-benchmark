#!/usr/bin/env python3
"""
Extract source text from items.json for hallucination checking.

The items.json format is: {"items": {"corpuses": ["text1", "text2", ...]}}

Usage:
    # Extract and save to file
    python extract_source.py "items.json" -o source.txt
    
    # Print to stdout
    python extract_source.py "items.json"
    
    # Show stats without extracting
    python extract_source.py "items.json" --stats
    
    # Custom separator
    python extract_source.py "items.json" -o source.txt --separator "\\n---PAGE---\\n"
"""

import json
import sys
from pathlib import Path

try:
    from rich.console import Console
    from rich.table import Table
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


def is_s3_path(path: str) -> bool:
    """Check if path is an S3 URI."""
    return path.startswith('s3://')


def read_json_file(path: str) -> dict:
    """Read JSON from local path or S3."""
    if is_s3_path(path):
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from src.utils.s3_utils import S3Client, S3Path
            s3_client = S3Client()
            s3_path = S3Path.parse(path)
            print(f"📥 Downloading from S3: {path}", file=sys.stderr)
            return s3_client.read_json(s3_path.bucket, s3_path.key)
        except ImportError:
            print("Error: boto3 required for S3 support. Run: pip install boto3", file=sys.stderr)
            sys.exit(1)
    else:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)


def show_stats(corpuses: list) -> None:
    """Show statistics about the corpuses."""
    if not corpuses:
        print("No corpuses found.")
        return
    
    total_chars = sum(len(c) for c in corpuses)
    total_lines = sum(c.count('\n') for c in corpuses)
    
    if HAS_RICH:
        console = Console()
        table = Table(title="📊 Source Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right", style="white")
        
        table.add_row("Total Corpuses", str(len(corpuses)))
        table.add_row("Total Characters", f"{total_chars:,}")
        table.add_row("Total Lines", f"{total_lines:,}")
        table.add_row("Average Corpus Size", f"{total_chars // len(corpuses):,} chars")
        
        # Show first few corpus sizes
        console.print(table)
        
        if len(corpuses) <= 10:
            detail_table = Table(title="📄 Corpus Details")
            detail_table.add_column("#", style="dim", justify="right")
            detail_table.add_column("Size", justify="right")
            detail_table.add_column("Preview", style="dim", max_width=60)
            
            for i, corpus in enumerate(corpuses, 1):
                preview = corpus[:80].replace('\n', ' ').strip()
                if len(corpus) > 80:
                    preview += "..."
                detail_table.add_row(str(i), f"{len(corpus):,} chars", preview)
            
            console.print(detail_table)
    else:
        print(f"\n📊 Source Statistics:")
        print(f"  Total Corpuses: {len(corpuses)}")
        print(f"  Total Characters: {total_chars:,}")
        print(f"  Total Lines: {total_lines:,}")
        print(f"  Average Corpus Size: {total_chars // len(corpuses):,} chars")


def extract_corpuses(data: dict) -> list:
    """Extract corpuses from items.json format."""
    # Standard format: {"items": {"corpuses": [...]}}
    if 'items' in data and 'corpuses' in data['items']:
        return data['items']['corpuses']
    
    # Alternative: {"corpuses": [...]}
    if 'corpuses' in data:
        return data['corpuses']
    
    # Alternative: direct list
    if isinstance(data, list):
        return data
    
    return []


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    json_path = sys.argv[1]
    
    # Parse options
    output_file = None
    show_stats_only = False
    separator = "\n\n---\n\n"
    
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] in ('-o', '--output'):
            output_file = args[i + 1]
            i += 2
        elif args[i] in ('--stats', '-s'):
            show_stats_only = True
            i += 1
        elif args[i] == '--separator':
            separator = args[i + 1].encode().decode('unicode_escape')
            i += 2
        else:
            i += 1
    
    # Read JSON
    print(f"📂 Loading: {json_path}", file=sys.stderr)
    data = read_json_file(json_path)
    
    # Extract corpuses
    corpuses = extract_corpuses(data)
    
    if not corpuses:
        print("❌ No corpuses found in the JSON file.", file=sys.stderr)
        print("   Expected format: {\"items\": {\"corpuses\": [...]}}", file=sys.stderr)
        sys.exit(1)
    
    print(f"✅ Found {len(corpuses)} corpus(es)", file=sys.stderr)
    
    # Show stats only
    if show_stats_only:
        show_stats(corpuses)
        return
    
    # Combine corpuses
    combined = separator.join(corpuses)
    total_chars = len(combined)
    
    # Output
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(combined)
        print(f"✅ Saved to: {output_file}", file=sys.stderr)
        print(f"   Total size: {total_chars:,} chars", file=sys.stderr)
    else:
        # Print to stdout
        print(combined)


if __name__ == '__main__':
    main()
