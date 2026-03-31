#!/usr/bin/env python3
"""
Quick test script for benchmarking research v1 outputs.

Usage:
    # Test with specific research result
    python test_v1.py --research-id c21c9534-54e0-4842-87c7-24cfd0c9065e
    
    # Test with custom output file
    python test_v1.py --output /path/to/output.md --metadata /path/to/metadata.json
"""

import json
import sys
from pathlib import Path

# Add benchmark root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.contracts import V1Parser, BenchmarkContract
from src.scoring import ScoringCalculator, create_report
from src.utils import MarkdownParser
from src.validators import CitationValidator


def run_research_result(research_id: str, results_dir: str = None):
    """
    Test a research v1 result by ID.
    
    Args:
        research_id: The research ID (UUID)
        results_dir: Optional custom results directory
    """
    # Default results directory
    if results_dir is None:
        results_dir = Path(__file__).parent.parent / "research" / "results"
    else:
        results_dir = Path(results_dir)
    
    result_path = results_dir / research_id
    
    if not result_path.exists():
        print(f"❌ Result not found: {result_path}")
        return None
    
    # Load files
    output_path = result_path / "output.md"
    metadata_path = result_path / "metadata.json"
    
    if not output_path.exists():
        print(f"❌ output.md not found in {result_path}")
        return None
    
    if not metadata_path.exists():
        print(f"❌ metadata.json not found in {result_path}")
        return None
    
    print(f"📂 Loading result: {research_id}")
    
    with open(output_path, 'r') as f:
        output_md = f.read()
    
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    # Parse instruction from metadata
    instruction = metadata.get('question', '')
    if not instruction:
        print("❌ No 'question' field in metadata")
        return None
    
    print(f"📝 Section: {metadata.get('section_name', 'Unknown')}")
    print(f"📊 Processing time: {metadata.get('processing_time', 0):.2f}s")
    
    # Generate contract from instruction
    parser = V1Parser()
    contract = parser.parse(instruction)
    
    print(f"📋 Contract generated:")
    print(f"   Expected sections: {len(contract.expected_sections)}")
    print(f"   Date format: {contract.date_format}")
    
    # Calculate scores
    calculator = ScoringCalculator(contract)
    result = calculator.calculate(output_md, skip_llm_judge=True)
    
    # Print results
    print("\n" + "="*60)
    print("📈 BENCHMARK RESULTS")
    print("="*60)
    
    print(f"\n{'Dimension':<20} {'Score':>10} {'Status':>15}")
    print("-"*45)
    
    def status(score):
        if score >= 0.9: return "✓ Excellent"
        elif score >= 0.7: return "○ Good"
        elif score >= 0.5: return "△ Fair"
        else: return "✗ Poor"
    
    print(f"{'Formatting':<20} {result.formatting_score:>10.2%} {status(result.formatting_score):>15}")
    print(f"{'Completeness':<20} {result.completeness_score:>10.2%} {status(result.completeness_score):>15}")
    print(f"{'Hallucination':<20} {result.hallucination_score:>10.2%} {status(result.hallucination_score):>15}")
    print("-"*45)
    print(f"{'TOTAL':<20} {result.total_score:>10.2%} {status(result.total_score):>15}")
    
    # Stats
    print(f"\n📊 Statistics:")
    print(f"   Total entries: {result.total_entries}")
    print(f"   Entries with citations: {result.entries_with_citations}")
    print(f"   Total citations: {result.total_citations}")
    
    # Compare with metadata
    if 'metadata' in metadata:
        meta_stats = metadata['metadata']
        print(f"\n📄 From metadata.json:")
        print(f"   Initial refs: {meta_stats.get('initial_refs', 'N/A')}")
        print(f"   Final refs: {meta_stats.get('final_refs', 'N/A')}")
        print(f"   Preservation rate: {metadata.get('final_preservation_rate', 0):.2%}")
    
    # Validation reports from metadata
    if 'validation_reports' in metadata:
        print(f"\n📋 Validation from pipeline:")
        for report in metadata['validation_reports']:
            print(f"   {report['stage']}: {report['preservation_rate']:.2%} ({report['status']})")
    
    # Errors summary
    if result.formatting_errors:
        print(f"\n⚠ Formatting errors: {len(result.formatting_errors)}")
        for error in result.formatting_errors[:5]:
            print(f"   [{error.code}] {error.message[:60]}...")
    
    if result.coverage_violations:
        print(f"\n⚠ Coverage violations: {len(result.coverage_violations)}")
        for violation in result.coverage_violations[:5]:
            print(f"   [{violation.code}] {violation.field}")
    
    # Final verdict
    print("\n" + "="*60)
    if result.total_score >= 0.8:
        print("✓ PASS - Output meets quality standards")
    elif result.total_score >= 0.6:
        print("○ ACCEPTABLE - Output has minor issues")
    else:
        print("✗ FAIL - Output needs improvement")
    print("="*60)
    
    return result


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test research v1 outputs')
    parser.add_argument('--research-id', '-r', help='Research result ID to test')
    parser.add_argument('--output', '-o', help='Path to output.md')
    parser.add_argument('--metadata', '-m', help='Path to metadata.json')
    parser.add_argument('--results-dir', help='Custom results directory')
    
    args = parser.parse_args()
    
    if args.research_id:
        run_research_result(args.research_id, args.results_dir)
    elif args.output and args.metadata:
        # Custom test
        with open(args.output, 'r') as f:
            output_md = f.read()
        with open(args.metadata, 'r') as f:
            metadata = json.load(f)
        
        instruction = metadata.get('question', '')
        parser = V1Parser()
        contract = parser.parse(instruction)
        
        calculator = ScoringCalculator(contract)
        result = calculator.calculate(output_md)
        
        print(f"Total score: {result.total_score:.2%}")
    else:
        # Default: test the known result
        print("Testing default research result...")
        run_research_result("c21c9534-54e0-4842-87c7-24cfd0c9065e")


if __name__ == '__main__':
    main()
