#!/usr/bin/env python3
"""
Benchmark CLI - Evaluate research pipeline outputs.

Usage:
    # Basic evaluation with local files
    python main.py --output output.md --instruction instruction.txt

    # With S3 paths
    python main.py --output s3://bucket/path/output.md --metadata s3://bucket/path/metadata.json

    # With MESSAGE_BODY (like research pipeline)
    export MESSAGE_BODY='{"research_id":"xxx","output_s3_bucket":"bucket","output_s3_key":"path/output.md"}'
    python main.py

    # Deep hallucination check with source
    python main.py --output s3://bucket/output.md --metadata s3://bucket/metadata.json \
                   --source s3://bucket/source.txt --deep-check
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Load .env file
from dotenv import load_dotenv
load_dotenv(override=True)


# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    import click
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
except ImportError:
    print("Missing dependencies. Run: pip install click rich")
    sys.exit(1)

from src.contracts import BenchmarkContract, V1Parser, V2Parser, get_backend
from src.scoring import ScoringCalculator, ScoreWeights, create_report
from src.utils import MarkdownParser, TraceWriter
from src.utils.s3_utils import (
    S3Client,
    S3Path,
    BenchmarkContext,
    read_file_or_s3,
    read_json_or_s3,
    is_s3_path,
)


console = Console()


def load_from_message_body() -> Optional[BenchmarkContext]:
    """Load context from MESSAGE_BODY environment variable."""
    message_body = os.getenv('MESSAGE_BODY')
    if not message_body:
        return None

    try:
        return BenchmarkContext.from_message_body(message_body)
    except (json.JSONDecodeError, ValueError) as e:
        console.print(f"[red]Error parsing MESSAGE_BODY: {e}[/red]")
        return None


def read_file_content(path: str, s3_client: Optional[S3Client] = None) -> str:
    """Read file from local path or S3."""
    if is_s3_path(path):
        if s3_client is None:
            s3_client = S3Client()
        s3_path = S3Path.parse(path)
        console.print(f"   📥 Downloading from S3: {path}")
        return s3_client.read_text(s3_path.bucket, s3_path.key)
    else:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()


def read_json_content(path: str, s3_client: Optional[S3Client] = None) -> dict:
    """Read JSON from local path or S3."""
    if is_s3_path(path):
        if s3_client is None:
            s3_client = S3Client()
        s3_path = S3Path.parse(path)
        console.print(f"   📥 Downloading from S3: {path}")
        return s3_client.read_json(s3_path.bucket, s3_path.key)
    else:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)


@click.command()
@click.option('--output', '-o', type=str, envvar='BENCHMARK_OUTPUT', help='Path to output.md (local or s3://)')
@click.option('--instruction', '-i', type=str, envvar='BENCHMARK_INSTRUCTION', help='Path to instruction text (local or s3://)')
@click.option('--source', '-s', type=str, envvar='BENCHMARK_SOURCE', help='Path to source.txt for hallucination checking (local or s3://)')
@click.option('--contract', '-c', type=str, envvar='BENCHMARK_CONTRACT', help='Path to pre-defined contract JSON (local or s3://)')
@click.option('--export-contract', type=click.Path(), help='Export parsed contract to this local path')
@click.option('--config', type=click.Path(exists=True), envvar='BENCHMARK_CONFIG', help='Path to multi-section report config JSON')
@click.option('--compare', 'compare_config', type=click.Path(exists=True), help='Path to model comparison config JSON')
@click.option('--mode', type=click.Choice(['v1', 'v2']), default='v1', help='Pipeline mode')
@click.option('--quick', is_flag=True, help='Quick mode (skip detailed errors)')
@click.option('--output-format', type=click.Choice(['json', 'report']), default='report', help='Output format')
@click.option('--metadata', type=str, envvar='BENCHMARK_METADATA', help='Path to metadata.json (local or s3://)')
@click.option('--deep-check/--no-deep-check', default=None, envvar='DEEP_CHECK', help='Enable/disable LLM-based checks (--compare defaults to on)')
@click.option('--max-claims', type=int, default=50, envvar='MAX_CLAIMS', help='Max claims to verify with LLM judge (default: 50)')
@click.option('--batch-size', type=int, default=10, envvar='BATCH_SIZE', help='Claims per API call for hallucination check (default: 10, set 1 for single mode)')
@click.option('--max-workers', type=int, default=5, envvar='MAX_WORKERS', help='Max concurrent API calls (default: 5, use with --deep-check)')
@click.option('--no-parallel', is_flag=True, help='Disable parallel processing (sequential batches)')
@click.option('--llm-backend', type=click.Choice(['gemini', 'nebius']), default='gemini', envvar='LLM_BACKEND',
              help='LLM backend for rule extraction (default: gemini)')
@click.option('--no-llm', is_flag=True, help='Disable LLM for rule extraction (regex only, faster but less accurate)')
@click.option('--parser', 'parser_version', type=click.Choice(['v1', 'v2', 'auto']), default='auto', envvar='PARSER_VERSION',
              help='Parser version: v1 (regex+LLM), v2 (structured instruction), auto (detect)')
@click.option('--trace-dir', type=str, envvar='TRACE_DIR', help='Directory to save trace files (claims, verdicts, results)')
@click.option('--trace-base-dir', type=str, envvar='TRACE_BASE_DIR', help='Base directory for traces; traces saved to {base}/{research_id}/')
@click.option('--research-id', type=str, envvar='RESEARCH_ID', help='Research ID for organizing traces (auto-detected from MESSAGE_BODY if not provided)')
@click.option('--golden', type=click.Path(exists=True), help='Path to golden.json for Precision/Recall evaluation')
def main(
    output: Optional[str],
    instruction: Optional[str],
    source: Optional[str],
    contract: Optional[str],
    export_contract: Optional[str],
    config: Optional[str],
    compare_config: Optional[str],
    mode: str,
    quick: bool,
    output_format: str,
    metadata: Optional[str],
    deep_check: bool,
    max_claims: int,
    batch_size: int,
    max_workers: int,
    no_parallel: bool,
    llm_backend: str,
    no_llm: bool,
    parser_version: str,
    trace_dir: Optional[str],
    trace_base_dir: Optional[str],
    research_id: Optional[str],
    golden: Optional[str],
):
    """
    Benchmark research pipeline outputs.

    Evaluates output quality across deterministic dimensions:
    - Formatting (structure, headers, dates)
    - Completeness (entry count, date coverage)
    - Traceability (source references per entry)

    Supports local files and S3 paths (s3://bucket/key).
    Can also read from MESSAGE_BODY environment variable.

    For multi-section reports, use --config with a JSON configuration file.

    Use --trace-dir to save detailed trace files including claims, verdicts, and results.
    """
    console.print(Panel.fit(
        "[bold blue]Research Pipeline Benchmark[/bold blue]",
        subtitle="v1.0.0"
    ))

    # Handle golden evaluation mode
    if golden and output:
        _run_golden_evaluation(golden, output)
        return
    elif golden and compare_config:
        _run_golden_comparison(golden, compare_config)
        return

    # Handle model comparison mode
    # --compare defaults to deep_check=True unless explicitly --no-deep-check
    if compare_config:
        compare_deep = deep_check if deep_check is not None else True
        _run_model_comparison(compare_config, quick, output_format, deep_check=compare_deep)
        return

    # Handle multi-section config mode
    if config:
        _run_multi_section(config, llm_backend, no_llm, deep_check, max_claims, batch_size, max_workers, not no_parallel, quick, output_format)
        return

    # Check for MESSAGE_BODY first
    context = load_from_message_body()
    if context:
        console.print(f"📋 Loaded context from MESSAGE_BODY")
        console.print(f"   Research ID: {context.research_id}")
        output = context.get_output_uri()
        source = context.get_source_uri() if context.source_s3_key else source
        metadata = context.get_metadata_uri()
        deep_check = context.deep_check or deep_check or False
        max_claims = context.max_claims or max_claims
        # Auto-set research_id from context if not provided
        if not research_id:
            research_id = context.research_id

    # Resolve trace directory
    # Priority: --trace-dir > --trace-base-dir/{research_id}
    effective_trace_dir = trace_dir
    if not effective_trace_dir and trace_base_dir:
        if research_id:
            effective_trace_dir = os.path.join(trace_base_dir, research_id)
            console.print(f"📁 Trace directory: {effective_trace_dir}")
        else:
            console.print("[yellow]Warning: --trace-base-dir provided but no research_id found. Use --research-id or MESSAGE_BODY.[/yellow]")

    # Initialize S3 client if needed
    s3_client = None
    if any(is_s3_path(p) for p in [output, instruction, source, contract, metadata] if p):
        console.print("☁️  S3 mode enabled")
        s3_client = S3Client()

    # Load or generate contract
    contract_obj = None

    if contract:
        console.print(f"📄 Loading contract from: {contract}")
        contract_text = read_file_content(contract, s3_client)
        contract_obj = BenchmarkContract.from_json(contract_text)
    elif instruction:
        console.print(f"📝 Parsing instruction from: {instruction}")
        instruction_text = read_file_content(instruction, s3_client)

        use_v2 = (
            parser_version == "v2"
            or (parser_version == "auto" and "PRIORITY 0" in instruction_text)
        )

        if use_v2:
            console.print(f"   🔧 Using V2 parser (deterministic)")
            parser = V2Parser()
            contract_obj = parser.parse(instruction_text)
        else:
            backend = None if no_llm else get_backend(llm_backend)
            parser = V1Parser(backend=backend, use_llm=not no_llm)
            if not no_llm:
                console.print(f"   🤖 Using LLM backend: [cyan]{llm_backend}[/cyan]")
            contract_obj = parser.parse(instruction_text)

        console.print(f"   Section: [cyan]{contract_obj.section_name}[/cyan]")
        console.print(f"   Required fields: {len(contract_obj.required_fields)}")
        if contract_obj.forbidden_words:
            console.print(f"   Forbidden words: {contract_obj.forbidden_words}")
        if contract_obj.source_citation_limit is not None:
            console.print(f"   Source limit: {contract_obj.source_citation_limit}")
        if contract_obj.chronological_order:
            console.print(f"   Chronological: {contract_obj.chronological_direction}")
    elif metadata:
        console.print(f"📄 Loading instruction from metadata: {metadata}")
        meta = read_json_content(metadata, s3_client)

        instruction_text = meta.get('question', '')
        if not instruction_text:
            console.print("[red]Error: No 'question' field in metadata[/red]")
            sys.exit(1)

        # Initialize parser with backend options
        backend = None if no_llm else get_backend(llm_backend)
        parser = V1Parser(backend=backend, use_llm=not no_llm)
        if not no_llm:
            console.print(f"   🤖 Using LLM backend: [cyan]{llm_backend}[/cyan]")
        contract_obj = parser.parse(instruction_text)
        console.print(f"   Section: [cyan]{contract_obj.section_name}[/cyan]")
    else:
        console.print("[red]Error: Must provide --instruction, --contract, --metadata, or MESSAGE_BODY[/red]")
        sys.exit(1)

    # Export contract if requested
    if export_contract:
        console.print(f"💾 Exporting contract to: {export_contract}")
        with open(export_contract, 'w') as f:
            f.write(contract_obj.to_json())
        console.print("[green]✓ Contract exported[/green]")

        if not output:
            return

    # Evaluate output
    if not output:
        console.print("[yellow]No output file specified. Use --output to evaluate.[/yellow]")
        return

    console.print(f"\n📊 Evaluating output: {output}")
    output_md = read_file_content(output, s3_client)

    # Load source if provided
    source_text = None
    if source:
        console.print(f"📚 Loading source: {source}")
        source_text = read_file_content(source, s3_client)
        console.print(f"   Source size: {len(source_text):,} chars")

    # Check deep_check requirements
    if deep_check and not source:
        console.print("[red]Error: --deep-check requires --source to be provided[/red]")
        sys.exit(1)

    if deep_check:
        api_calls = (max_claims + batch_size - 1) // batch_size
        parallel = not no_parallel
        mode_str = f"parallel, {max_workers} workers" if parallel else "sequential"
        console.print(f"🔬 Deep hallucination check enabled (max {max_claims} claims, ~{api_calls} API calls, {mode_str})")

    # Determine if V2 scoring should be used
    has_v2_rules = bool(
        contract_obj.forbidden_words
        or contract_obj.source_citation_limit is not None
        or contract_obj.chronological_order
    )

    # Calculate scores
    calculator = ScoringCalculator(contract_obj)
    result = calculator.calculate(
        output_md,
        source_text,
        skip_llm_judge=not deep_check,
        max_claims=max_claims,
        batch_size=batch_size,
        max_workers=max_workers,
        parallel=not no_parallel,
        verbose=not quick,
        use_v2_scoring=has_v2_rules,
    )

    # Output results
    if output_format == 'json':
        report = create_report(output_md, contract_obj, mode)
        console.print(report.to_json())
    else:
        _print_report(result, quick)

    # Save trace if directory specified
    if effective_trace_dir:
        console.print(f"\n💾 Saving trace to: {effective_trace_dir}")
        trace_writer = TraceWriter(effective_trace_dir)

        # Set metadata
        trace_writer.set_metadata(
            research_id=research_id or "",
            output_file=output or "",
            instruction_file=instruction or metadata or "",
            source_file=source or "",
            llm_backend=llm_backend,
            deep_check=deep_check,
            max_claims=max_claims,
            batch_size=batch_size,
        )

        # Set contract
        trace_writer.set_contract(contract_obj.to_dict())

        # Set benchmark result
        trace_writer.set_benchmark_result(result.to_dict())

        # Set trace data if available (from deep check)
        if result.trace:
            trace_writer.set_claims(result.trace.claims)
            trace_writer.set_verdicts(result.trace.verdicts)
            if result.trace.hallucination_result:
                trace_writer.set_hallucination_result(result.trace.hallucination_result)

        # Set completeness details if available
        if result.completeness_details:
            trace_writer.set_completeness_details(result.completeness_details.to_dict())

        # Write all files
        trace_writer.write_all()
        console.print(f"[green]✓ Trace files saved:[/green]")
        console.print(f"   • metadata.json")
        console.print(f"   • contract.json")
        console.print(f"   • benchmark_result.json")
        if result.trace:
            console.print(f"   • claims.json ({len(result.trace.claims)} claims)")
            console.print(f"   • verdicts.json ({len(result.trace.verdicts)} verdicts)")
            console.print(f"   • hallucination_details.json")
        if result.completeness_details:
            console.print(f"   • completeness_details.json")


def _print_report(result, quick: bool = False):
    """Print formatted benchmark report."""

    # Score summary table
    table = Table(title="📈 Benchmark Scores")
    table.add_column("Dimension", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Status", justify="center")

    def score_status(score):
        if score >= 0.9:
            return "[green]✓ Excellent[/green]"
        elif score >= 0.7:
            return "[yellow]○ Good[/yellow]"
        elif score >= 0.5:
            return "[orange1]△ Fair[/orange1]"
        else:
            return "[red]✗ Poor[/red]"

    table.add_row("Formatting", f"{result.formatting_score:.2%}", score_status(result.formatting_score))
    table.add_row("Completeness", f"{result.completeness_score:.2%}", score_status(result.completeness_score))
    table.add_row("Traceability", f"{result.hallucination_score:.2%}", score_status(result.hallucination_score))

    if result.forbidden_words_violations or result.forbidden_words_score < 1.0:
        table.add_row("Forbidden Words", f"{result.forbidden_words_score:.2%}", score_status(result.forbidden_words_score))
    if result.source_limit_violations or result.source_limit_score < 1.0:
        table.add_row("Source Limit", f"{result.source_limit_score:.2%}", score_status(result.source_limit_score))
    if result.chronological_violations or result.chronological_score < 1.0:
        table.add_row("Chronological", f"{result.chronological_score:.2%}", score_status(result.chronological_score))

    table.add_row("[bold]Total[/bold]", f"[bold]{result.total_score:.2%}[/bold]", score_status(result.total_score))

    console.print(table)

    # Stats
    console.print(f"\n📊 Statistics:")
    console.print(f"   Total entries: {result.total_entries}")
    console.print(f"   Entries with citations: {result.entries_with_citations}")
    console.print(f"   Total citations: {result.total_citations}")

    if not quick:
        # Detailed errors
        if result.formatting_errors:
            console.print(f"\n[yellow]⚠ Formatting Errors ({len(result.formatting_errors)}):[/yellow]")
            for error in result.formatting_errors[:10]:
                line_info = f" (line {error.line})" if error.line else ""
                console.print(f"   [{error.code}]{line_info} {error.message}")
            if len(result.formatting_errors) > 10:
                console.print(f"   ... and {len(result.formatting_errors) - 10} more")

        if result.coverage_violations:
            console.print(f"\n[yellow]⚠ Coverage Violations ({len(result.coverage_violations)}):[/yellow]")
            for violation in result.coverage_violations[:10]:
                console.print(f"   [{violation.code}] {violation.field} in {violation.section}")
            if len(result.coverage_violations) > 10:
                console.print(f"   ... and {len(result.coverage_violations) - 10} more")

        if result.unsupported_claims:
            console.print(f"\n[red]⚠ Unsupported Claims ({len(result.unsupported_claims)}):[/red]")
            for claim in result.unsupported_claims[:10]:
                console.print(f"   [{claim.verdict}] {claim.claim[:60]}...")
                if claim.reason:
                    console.print(f"      Reason: {claim.reason[:80]}...")
            if len(result.unsupported_claims) > 10:
                console.print(f"   ... and {len(result.unsupported_claims) - 10} more")

        if result.forbidden_words_violations:
            console.print(f"\n[yellow]⚠ Forbidden Words ({len(result.forbidden_words_violations)}):[/yellow]")
            for error in result.forbidden_words_violations[:10]:
                line_info = f" (line {error.line})" if error.line else ""
                console.print(f"   {line_info} {error.message}")
            if len(result.forbidden_words_violations) > 10:
                console.print(f"   ... and {len(result.forbidden_words_violations) - 10} more")

        if result.source_limit_violations:
            console.print(f"\n[yellow]⚠ Source Limit Violations ({len(result.source_limit_violations)}):[/yellow]")
            for error in result.source_limit_violations[:10]:
                line_info = f" (line {error.line})" if error.line else ""
                console.print(f"   {line_info} {error.message}")

        if result.chronological_violations:
            console.print(f"\n[yellow]⚠ Chronological Order ({len(result.chronological_violations)}):[/yellow]")
            for error in result.chronological_violations[:10]:
                console.print(f"   {error.message}")

    # Final verdict
    if result.total_score >= 0.8:
        console.print(f"\n[green]✓ PASS - Output meets quality standards[/green]")
    elif result.total_score >= 0.6:
        console.print(f"\n[yellow]○ ACCEPTABLE - Output has minor issues[/yellow]")
    else:
        console.print(f"\n[red]✗ FAIL - Output needs improvement[/red]")


def _run_multi_section(
    config_path: str,
    llm_backend: str,
    no_llm: bool,
    deep_check: bool,
    max_claims: int,
    batch_size: int,
    max_workers: int,
    parallel: bool,
    quick: bool,
    output_format: str,
):
    """Run multi-section report evaluation."""
    from src.scoring import MultiSectionEvaluator, ReportConfig

    console.print(f"📁 Loading multi-section config: {config_path}")

    # Load config
    config = ReportConfig.from_json_file(config_path)

    # Override settings from CLI
    if deep_check:
        config.deep_check = True
    if max_claims:
        config.max_claims = max_claims
    if batch_size:
        config.batch_size = batch_size
    if max_workers:
        config.max_workers = max_workers
    config.parallel = parallel

    console.print(f"   Report: [cyan]{config.report_name}[/cyan]")
    console.print(f"   Sections: {len(config.sections)}")

    if config.deep_check:
        api_calls = len(config.sections) * ((config.max_claims + config.batch_size - 1) // config.batch_size)
        mode_str = f"parallel, {config.max_workers} workers" if config.parallel else "sequential"
        console.print(f"   Deep check: enabled (~{api_calls} API calls, {mode_str})")

    # Initialize backend
    backend = None
    if not no_llm:
        backend = get_backend(llm_backend)
        console.print(f"   🤖 LLM backend: [cyan]{llm_backend}[/cyan]")

    # Run evaluation
    evaluator = MultiSectionEvaluator(config, llm_backend=backend, use_llm=not no_llm)
    report = evaluator.evaluate(verbose=not quick)

    # Output results
    if output_format == 'json':
        console.print(report.to_json())
    else:
        _print_multi_section_report(report, quick)


def _print_multi_section_report(report, quick: bool = False):
    """Print formatted multi-section benchmark report."""

    # Section scores table
    table = Table(title=f"📊 Multi-Section Report Scores")
    table.add_column("Section", style="cyan", max_width=30)
    table.add_column("Format", justify="right")
    table.add_column("Complete", justify="right")
    table.add_column("Trace", justify="right")
    table.add_column("Total", justify="right")
    table.add_column("Status", justify="center")

    def score_status(score):
        if score >= 0.9:
            return "[green]✓[/green]"
        elif score >= 0.7:
            return "[yellow]○[/yellow]"
        elif score >= 0.5:
            return "[orange1]△[/orange1]"
        else:
            return "[red]✗[/red]"

    def format_score(score):
        if score >= 0.9:
            return f"[green]{score:.1%}[/green]"
        elif score >= 0.7:
            return f"[yellow]{score:.1%}[/yellow]"
        elif score >= 0.5:
            return f"[orange1]{score:.1%}[/orange1]"
        else:
            return f"[red]{score:.1%}[/red]"

    # Add section rows
    for section in report.sections:
        table.add_row(
            section.section_name[:30],
            format_score(section.formatting_score),
            format_score(section.completeness_score),
            format_score(section.hallucination_score),
            f"[bold]{section.total_score:.1%}[/bold]",
            score_status(section.total_score),
        )

    # Add separator and overall
    table.add_row("─" * 25, "─" * 6, "─" * 6, "─" * 6, "─" * 6, "─" * 3)

    # Compute averages
    if report.sections:
        avg_format = sum(s.formatting_score for s in report.sections) / len(report.sections)
        avg_complete = sum(s.completeness_score for s in report.sections) / len(report.sections)
        avg_halluc = sum(s.hallucination_score for s in report.sections) / len(report.sections)
    else:
        avg_format = avg_complete = avg_halluc = 0.0

    table.add_row(
        "[bold]Overall[/bold]",
        format_score(avg_format),
        format_score(avg_complete),
        format_score(avg_halluc),
        f"[bold]{report.overall_score:.1%}[/bold]",
        score_status(report.overall_score),
    )

    console.print(table)

    # Summary stats
    console.print(f"\n📈 Summary:")
    console.print(f"   Total sections: {report.total_sections}")
    console.print(f"   Formatting errors: {report.formatting_errors_count}")
    console.print(f"   Coverage violations: {report.coverage_violations_count}")
    console.print(f"   Unsupported claims: {report.unsupported_claims_count}")

    if not quick:
        # Per-section details
        for section in report.sections:
            if section.formatting_errors or section.coverage_violations or section.unsupported_claims:
                console.print(f"\n[cyan]📄 {section.section_name}[/cyan]")

                if section.formatting_errors:
                    console.print(f"   [yellow]Format errors: {len(section.formatting_errors)}[/yellow]")
                    for error in section.formatting_errors[:3]:
                        console.print(f"      • {error.message[:60]}")

                if section.coverage_violations:
                    console.print(f"   [yellow]Coverage violations: {len(section.coverage_violations)}[/yellow]")
                    for v in section.coverage_violations[:3]:
                        console.print(f"      • {v.field}")

                if section.unsupported_claims:
                    console.print(f"   [red]Unsupported claims: {len(section.unsupported_claims)}[/red]")
                    for c in section.unsupported_claims[:3]:
                        console.print(f"      • {c.claim[:50]}...")

    # Final verdict
    if report.overall_score >= 0.8:
        console.print(f"\n[green]✓ PASS - Report meets quality standards[/green]")
    elif report.overall_score >= 0.6:
        console.print(f"\n[yellow]○ ACCEPTABLE - Report has minor issues[/yellow]")
    else:
        console.print(f"\n[red]✗ FAIL - Report needs improvement[/red]")


def _run_model_comparison(config_path: str, quick: bool, output_format: str, deep_check: bool = False):
    """Run model comparison benchmark."""
    from src.scoring.model_comparison import ModelComparisonRunner, ComparisonConfig

    console.print(f"🔄 Loading comparison config: {config_path}")
    config = ComparisonConfig.from_json_file(config_path)

    console.print(f"   Name: [cyan]{config.comparison_name}[/cyan]")
    console.print(f"   Models: {len(config.models)}")
    for m in config.models:
        console.print(f"     • {m.name} ({m.provider}/{m.model_id})")
    console.print(f"   Parser: {config.parser}")
    if deep_check:
        console.print(f"   🔬 Deep check: enabled (LLM accuracy + pairwise)")

    runner = ModelComparisonRunner(config)
    report = runner.run(verbose=not quick, deep_check=deep_check)

    if output_format == "json":
        console.print(report.to_json())
    else:
        _print_comparison_report(report, quick)

    # Save JSON report alongside config
    report_path = config_path.replace(".json", "_results.json")
    if report_path == config_path:
        report_path = config_path + ".results.json"
    with open(report_path, "w") as f:
        f.write(report.to_json())
    console.print(f"\n💾 Results saved to: {report_path}")


def _print_comparison_report(report, quick: bool = False):
    """Print formatted model comparison report."""

    console.print(f"\n")

    def format_score(score):
        if score >= 0.9:
            return f"[green]{score:.1%}[/green]"
        elif score >= 0.7:
            return f"[yellow]{score:.1%}[/yellow]"
        elif score >= 0.5:
            return f"[orange1]{score:.1%}[/orange1]"
        else:
            return f"[red]{score:.1%}[/red]"

    ranking = report._compute_ranking()
    rank_map = {r["name"]: r["rank"] for r in ranking}

    # Scores table
    table = Table(title=f"🏆 Model Comparison: {report.comparison_name}")
    table.add_column("Model", style="cyan", min_width=18)
    table.add_column("Format", justify="right")
    table.add_column("Compl", justify="right")
    table.add_column("Trace", justify="right")
    table.add_column("Chrono", justify="right")
    table.add_column("Clinical", justify="right")
    table.add_column("DateCov", justify="right")
    table.add_column("Total", justify="right", style="bold")
    table.add_column("#", justify="center")

    for result in sorted(report.results, key=lambda r: rank_map.get(r.name, 999)):
        if result.error:
            table.add_row(result.name, "[red]ERR[/red]", "", "", "", "", "", "", "")
            continue
        sr = result.section_result
        if sr is None:
            table.add_row(result.name, "[dim]N/A[/dim]", "", "", "", "", "", "", "")
            continue

        rank = rank_map.get(result.name, "-")
        rank_str = f"[bold green]{rank}[/bold green]" if rank == 1 else str(rank)

        has_entries = sr.clinical_coverage_score > 0 or sr.completeness_score > 0
        trace_str = format_score(sr.hallucination_score) if has_entries else "[dim]N/A[/dim]"
        chrono_str = format_score(sr.chronological_score) if has_entries else "[dim]N/A[/dim]"

        table.add_row(
            result.name,
            format_score(sr.formatting_score),
            format_score(sr.completeness_score),
            trace_str,
            chrono_str,
            format_score(sr.clinical_coverage_score),
            format_score(sr.date_coverage_score),
            format_score(sr.total_score),
            rank_str,
        )

    console.print(table)

    # Stats table
    has_entry_stats = any(r.json_stats or r.parsed_entries for r in report.results)
    if has_entry_stats:
        stats_table = Table(title="📊 Extraction Stats")
        stats_table.add_column("Model", style="cyan", min_width=18)
        stats_table.add_column("Incl", justify="right")
        stats_table.add_column("Excl", justify="right")
        stats_table.add_column("Dups", justify="right")
        stats_table.add_column("DateErr", justify="right")
        stats_table.add_column("ProvErr", justify="right")
        stats_table.add_column("EncDates", justify="right")
        stats_table.add_column("Missed", justify="right")
        stats_table.add_column("EntRatio", justify="right")

        for result in sorted(report.results, key=lambda r: rank_map.get(r.name, 999)):
            s = result.json_stats or {}
            if not s and not result.parsed_entries:
                continue
            sr = result.section_result
            dc = sr.date_coverage_stats if sr else {}
            ratio = s.get("entry_count_ratio")
            ratio_str = f"{ratio:.2f}" if ratio is not None else "-"
            enc_dates = dc.get("consensus_encounter_dates", dc.get("source_dates_found", "-"))
            stats_table.add_row(
                result.name,
                str(s.get("included_entries", 0)),
                str(s.get("excluded_entries", 0)),
                f"[red]{s.get('duplicate_entries', 0)}[/red]" if s.get("duplicate_entries", 0) else "0",
                f"[red]{s.get('date_errors', 0)}[/red]" if s.get("date_errors", 0) else "0",
                f"[red]{s.get('provider_errors', 0)}[/red]" if s.get("provider_errors", 0) else "0",
                str(enc_dates),
                f"[red]{dc.get('missed', 0)}[/red]" if dc.get("missed", 0) else "0",
                ratio_str,
            )

        console.print(stats_table)

    # Detailed errors
    if not quick:
        for result in report.results:
            if result.error:
                console.print(f"\n[red]❌ {result.name}: {result.error}[/red]")
                continue

            all_errors = result.json_schema_errors or []
            sr = result.section_result
            if sr:
                all_errors = all_errors or sr.formatting_errors

            if not all_errors:
                continue

            console.print(f"\n[cyan]📄 {result.name} ({len(all_errors)} issues)[/cyan]")
            for e in all_errors[:8]:
                console.print(f"   • {e.message[:100]}")
            if len(all_errors) > 8:
                console.print(f"   ... and {len(all_errors) - 8} more")

    # Accuracy results (from deep check)
    has_accuracy = any(r.accuracy_result for r in report.results)
    if has_accuracy:
        console.print(f"\n")
        acc_table = Table(title="🔬 Extraction Accuracy (LLM Judge)")
        acc_table.add_column("Model", style="cyan", min_width=18)
        acc_table.add_column("Checked", justify="right")
        acc_table.add_column("Accurate", justify="right")
        acc_table.add_column("Minor", justify="right")
        acc_table.add_column("Major", justify="right")
        acc_table.add_column("Fabricated", justify="right")
        acc_table.add_column("Score", justify="right", style="bold")

        for result in sorted(report.results, key=lambda r: rank_map.get(r.name, 999)):
            acc = result.accuracy_result
            if not acc:
                continue
            acc_table.add_row(
                result.name,
                str(acc.get("total_checked", 0)),
                f"[green]{acc.get('accurate_count', 0)}[/green]",
                f"[yellow]{acc.get('minor_errors_count', 0)}[/yellow]",
                f"[red]{acc.get('major_errors_count', 0)}[/red]",
                f"[red]{acc.get('hallucinated_count', 0)}[/red]",
                format_score(acc.get("average_score", 0)),
            )

        console.print(acc_table)

    # Pairwise results
    if report.pairwise:
        console.print(f"\n")
        pw = report.pairwise
        pw_table = Table(title="⚔️ Pairwise Comparison (LLM Judge)")
        pw_table.add_column("Match", style="cyan")
        pw_table.add_column("Winner", style="bold")
        pw_table.add_column("Dimensions", style="dim")

        for comp in pw.get("comparisons", []):
            winner = comp.get("winner", "tie")
            dims = comp.get("dimensions", {})
            dim_str = "  ".join(f"{k}={v}" for k, v in dims.items()) if dims else ""
            pw_table.add_row(
                f"{comp['model_a']} vs {comp['model_b']}",
                f"[green]{winner}[/green]" if winner != "tie" else "[dim]tie[/dim]",
                dim_str,
            )

        console.print(pw_table)

        # Print reasoning for each comparison
        for comp in pw.get("comparisons", []):
            reasoning = comp.get("reasoning", "")
            if reasoning:
                console.print(f"\n   [dim]{comp['model_a']} vs {comp['model_b']}:[/dim]")
                console.print(f"   {reasoning[:300]}")

        elo = pw.get("elo_scores", {})
        if elo:
            console.print(f"\n📈 Elo Ratings:")
            for name, score in sorted(elo.items(), key=lambda x: -x[1]):
                console.print(f"   {name}: {score:.0f}")

    # Winner announcement
    if ranking:
        winner = ranking[0]
        console.print(f"\n[bold green]🏆 Winner: {winner['name']} (Total: {winner['total_score']:.2%})[/bold green]")


def _run_golden_evaluation(golden_path: str, output_path: str):
    """Evaluate a single model output against a golden dataset."""
    from synthesize_golden import evaluate_against_golden

    console.print(f"🎯 Golden Dataset Evaluation")
    console.print(f"   Golden: {golden_path}")
    console.print(f"   Output: {output_path}")

    output_md = Path(output_path).read_text(encoding="utf-8")
    result = evaluate_against_golden(golden_path, output_md)

    table = Table(title="Precision / Recall / F1")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    def _color(val):
        if val >= 0.9: return f"[green]{val:.1%}[/green]"
        elif val >= 0.7: return f"[yellow]{val:.1%}[/yellow]"
        else: return f"[red]{val:.1%}[/red]"

    table.add_row("Precision", _color(result["precision"]))
    table.add_row("Recall", _color(result["recall"]))
    table.add_row("F1 Score", _color(result["f1"]))
    table.add_row("False Inclusion Rate", _color(result["false_inclusion_rate"]))
    table.add_row("", "")
    table.add_row("True Positives", str(result["true_positives"]))
    table.add_row("False Positives", str(result["false_positives"]))
    table.add_row("False Negatives (missed)", str(result["false_negatives"]))
    table.add_row("False Inclusions (noise)", str(result["false_inclusions"]))
    table.add_row("", "")
    table.add_row("Golden entries", str(result["total_golden"]))
    table.add_row("Noise entries", str(result["total_noise"]))
    table.add_row("Model entries", str(result["total_model_entries"]))
    console.print(table)

    if result["missed_entries"]:
        console.print(f"\n[red]Missed entries ({len(result['missed_entries'])}):[/red]")
        for m in result["missed_entries"]:
            console.print(f"  ✗ {m['date']} | {m['facility']}")

    if result["extra_entries"]:
        console.print(f"\n[yellow]Extra entries ({len(result['extra_entries'])}):[/yellow]")
        for e in result["extra_entries"]:
            console.print(f"  ? {e['date']} | {e['facility']}")


def _run_golden_comparison(golden_path: str, compare_config_path: str):
    """Evaluate all models in a comparison config against a golden dataset."""
    from synthesize_golden import evaluate_against_golden

    with open(compare_config_path) as f:
        config = json.load(f)

    console.print(f"🎯 Golden Dataset Comparison")
    console.print(f"   Golden: {golden_path}")
    console.print(f"   Config: {compare_config_path}")

    table = Table(title="Golden Evaluation: Precision / Recall / F1")
    table.add_column("Model", style="cyan")
    table.add_column("Precision", justify="right")
    table.add_column("Recall", justify="right")
    table.add_column("F1", justify="right")
    table.add_column("False Incl.", justify="right")
    table.add_column("TP", justify="right")
    table.add_column("FP", justify="right")
    table.add_column("FN", justify="right")
    table.add_column("Entries", justify="right")

    def _color(val):
        if val >= 0.9: return f"[green]{val:.1%}[/green]"
        elif val >= 0.7: return f"[yellow]{val:.1%}[/yellow]"
        else: return f"[red]{val:.1%}[/red]"

    results = {}
    for model in config.get("models", []):
        name = model["name"]
        output_dir = model.get("output_dir", "")
        output_path = os.path.join(output_dir, "output.md")

        if not os.path.exists(output_path):
            console.print(f"  [dim]Skipping {name}: output not found[/dim]")
            continue

        output_md = Path(output_path).read_text(encoding="utf-8")
        result = evaluate_against_golden(golden_path, output_md)
        results[name] = result

        table.add_row(
            name,
            _color(result["precision"]),
            _color(result["recall"]),
            _color(result["f1"]),
            _color(result["false_inclusion_rate"]),
            str(result["true_positives"]),
            str(result["false_positives"]),
            str(result["false_negatives"]),
            str(result["total_model_entries"]),
        )

    console.print(table)

    # Save results
    results_path = compare_config_path.replace(".json", "_golden_results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    console.print(f"\n💾 Golden results saved to: {results_path}")


if __name__ == '__main__':
    main()
