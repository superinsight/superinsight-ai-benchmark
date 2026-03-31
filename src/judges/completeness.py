"""
Completeness Judge for verifying output covers all important source content.

This module provides LLM-based verification of whether the output
includes all important information from the source documents.

Environment Variables:
- COMPLETENESS_MAX_SOURCE_CHARS: Max chars for source text (default: 0 = no limit)
- COMPLETENESS_MAX_OUTPUT_CHARS: Max chars for output text (default: 0 = no limit)
"""

import os
import re
import time
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from .base import LLMJudge, JudgeVerdict, Verdict
from ..utils.source_index import SourceIndex

# Rich console for pretty output
console = Console()


# Environment variable configuration (0 = no limit)
COMPLETENESS_MAX_SOURCE_CHARS = int(os.getenv("COMPLETENESS_MAX_SOURCE_CHARS", "0"))
COMPLETENESS_MAX_OUTPUT_CHARS = int(os.getenv("COMPLETENESS_MAX_OUTPUT_CHARS", "0"))


# Prompt for completeness checking
COMPLETENESS_CHECK_PROMPT = """You are a QA reviewer checking if a medical summary is complete.

## Task
Compare the SOURCE TEXT (original medical records) with the OUTPUT (generated summary).
Identify any important information that was MISSED in the output.

## Source Text
{source_text}

## Output Summary
{output_text}

## Instructions
1. Identify all medical visits/events in the SOURCE
2. Check if each visit/event appears in the OUTPUT
3. For each visit, check if important details are included (provider, facility, diagnoses, treatment)
4. Report any missing visits or missing important details

## Response Format
Answer with EXACTLY this format:

Total Events in Source: <number>
Events Covered in Output: <number>
Coverage Rate: <0.0-1.0>

Missing Events:
- <MM/DD/YYYY or description>: <what was missed>

Missing Details:
- <event/visit>: <missing field or information>

Overall Verdict: COMPLETE | MOSTLY_COMPLETE | INCOMPLETE
Confidence: <0.0-1.0>
Summary: <one sentence summary of completeness>"""


# Prompt for quick coverage check (less detailed, cheaper)
QUICK_COVERAGE_PROMPT = """Compare these two texts and rate completeness.

SOURCE (original):
{source_text}

OUTPUT (summary):
{output_text}

Rate how completely the OUTPUT covers the SOURCE content.
Consider: Are all visits/events included? Are key details (dates, providers, diagnoses) preserved?

Answer format:
Coverage: <0.0-1.0>
Missing: <brief list of what's missing, or "None">
Verdict: COMPLETE | MOSTLY_COMPLETE | INCOMPLETE"""


@dataclass
class MissingItem:
    """Represents missing information."""
    item_type: str  # "event" or "detail"
    description: str
    date: Optional[str] = None
    severity: str = "medium"  # "high", "medium", "low"


@dataclass
class CompletenessResult:
    """Result from completeness checking."""
    total_source_events: int = 0
    covered_events: int = 0
    coverage_rate: float = 1.0
    
    missing_events: List[MissingItem] = field(default_factory=list)
    missing_details: List[MissingItem] = field(default_factory=list)
    
    verdict: str = "COMPLETE"  # COMPLETE | MOSTLY_COMPLETE | INCOMPLETE
    confidence: float = 1.0
    summary: str = ""
    
    # Timing
    total_time: float = 0.0
    
    def compute_score(self) -> float:
        """Compute completeness score (0.0 to 1.0)."""
        # Base score from coverage rate
        base_score = self.coverage_rate
        
        # Penalty for missing events (high impact)
        event_penalty = len(self.missing_events) * 0.1
        
        # Penalty for missing details (medium impact)
        detail_penalty = len(self.missing_details) * 0.02
        
        score = base_score - event_penalty - detail_penalty
        return max(0.0, min(1.0, score))
    
    def to_dict(self) -> Dict:
        return {
            "total_source_events": self.total_source_events,
            "covered_events": self.covered_events,
            "coverage_rate": self.coverage_rate,
            "missing_events": [
                {"type": m.item_type, "description": m.description, "date": m.date}
                for m in self.missing_events
            ],
            "missing_details": [
                {"type": m.item_type, "description": m.description}
                for m in self.missing_details
            ],
            "verdict": self.verdict,
            "confidence": self.confidence,
            "summary": self.summary,
            "score": self.compute_score(),
            "total_time": self.total_time,
        }


class CompletenessJudge(LLMJudge):
    """
    LLM-based judge for verifying output completeness.
    
    Uses Gemini to evaluate whether the output includes
    all important information from the source text.
    """
    
    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        temperature: float = 0.1,
        max_source_chars: int = COMPLETENESS_MAX_SOURCE_CHARS,
        max_output_chars: int = COMPLETENESS_MAX_OUTPUT_CHARS,
        quick_mode: bool = False,
    ):
        """
        Initialize Completeness Judge.
        
        Args:
            model: Gemini model name
            temperature: Sampling temperature
            max_source_chars: Max characters to include from source (0 = no limit)
            max_output_chars: Max characters to include from output (0 = no limit)
            quick_mode: If True, use simpler prompt for faster/cheaper evaluation
        """
        super().__init__(model=model, temperature=temperature)
        self.max_source_chars = max_source_chars
        self.max_output_chars = max_output_chars
        self.quick_mode = quick_mode
    
    def check_completeness(
        self,
        output_md: str,
        source_index: SourceIndex,
        verbose: bool = False,
    ) -> CompletenessResult:
        """
        Check if output covers all important source content.
        
        Args:
            output_md: The output markdown to evaluate
            source_index: Indexed source text
            verbose: Print progress
            
        Returns:
            CompletenessResult with coverage analysis
        """
        start_time = time.time()
        result = CompletenessResult()
        
        # Get source text (truncate only if limit > 0)
        source_text = source_index.get_full_text()
        if self.max_source_chars > 0 and len(source_text) > self.max_source_chars:
            source_text = source_text[:self.max_source_chars] + "\n... (truncated)"
            if verbose:
                console.print(f"   [yellow]⚠ Source truncated to {self.max_source_chars:,} chars[/yellow]")
        elif verbose:
            console.print(f"   [dim]Source: {len(source_text):,} chars (full)[/dim]")
        
        # Truncate output only if limit > 0
        output_text = output_md
        if self.max_output_chars > 0 and len(output_text) > self.max_output_chars:
            output_text = output_text[:self.max_output_chars] + "\n... (truncated)"
            if verbose:
                console.print(f"   [yellow]⚠ Output truncated to {self.max_output_chars:,} chars[/yellow]")
        elif verbose:
            console.print(f"   [dim]Output: {len(output_text):,} chars (full)[/dim]")
        
        # Choose prompt based on mode
        if self.quick_mode:
            prompt = QUICK_COVERAGE_PROMPT.format(
                source_text=source_text,
                output_text=output_text,
            )
        else:
            prompt = COMPLETENESS_CHECK_PROMPT.format(
                source_text=source_text,
                output_text=output_text,
            )
        
        try:
            if verbose:
                # Use spinner for LLM call
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    TimeElapsedColumn(),
                    console=console,
                    transient=True,
                ) as progress:
                    progress.add_task("[cyan]🔄 Analyzing completeness with LLM...", total=None)
                    response = self.generate(prompt)
                result = self._parse_response(response)
            else:
                response = self.generate(prompt)
                result = self._parse_response(response)
        except Exception as e:
            if verbose:
                console.print(f"   [red]⚠ LLM error: {e}[/red]")
            result.verdict = "ERROR"
            result.summary = str(e)
        
        result.total_time = time.time() - start_time
        
        if verbose:
            # Display results with rich formatting
            verdict_color = "green" if result.verdict == "COMPLETE" else "yellow" if result.verdict == "MOSTLY_COMPLETE" else "red"
            coverage_color = "green" if result.coverage_rate >= 0.8 else "yellow" if result.coverage_rate >= 0.6 else "red"
            
            console.print(f"   [{verdict_color}]📋 Verdict: {result.verdict}[/{verdict_color}]")
            console.print(f"   [{coverage_color}]📊 Coverage: {result.coverage_rate:.1%}[/{coverage_color}]")
            console.print(f"   [dim]⏱️  Time: {result.total_time:.2f}s[/dim]")
        
        return result
    
    def _parse_response(self, response: str) -> CompletenessResult:
        """Parse LLM response into CompletenessResult."""
        result = CompletenessResult()
        
        # Parse total events
        match = re.search(r'Total Events.*?:\s*(\d+)', response, re.IGNORECASE)
        if match:
            result.total_source_events = int(match.group(1))
        
        # Parse covered events
        match = re.search(r'Events Covered.*?:\s*(\d+)', response, re.IGNORECASE)
        if match:
            result.covered_events = int(match.group(1))
        
        # Parse coverage rate
        match = re.search(r'Coverage(?:\s+Rate)?[:\s]*([0-9.]+)', response, re.IGNORECASE)
        if match:
            try:
                result.coverage_rate = float(match.group(1))
                result.coverage_rate = min(1.0, max(0.0, result.coverage_rate))
            except ValueError:
                pass
        
        # Parse verdict
        if "INCOMPLETE" in response.upper():
            result.verdict = "INCOMPLETE"
        elif "MOSTLY_COMPLETE" in response.upper() or "MOSTLY COMPLETE" in response.upper():
            result.verdict = "MOSTLY_COMPLETE"
        elif "COMPLETE" in response.upper():
            result.verdict = "COMPLETE"
        
        # Parse confidence
        match = re.search(r'Confidence[:\s]*([0-9.]+)', response, re.IGNORECASE)
        if match:
            try:
                result.confidence = float(match.group(1))
                result.confidence = min(1.0, max(0.0, result.confidence))
            except ValueError:
                pass
        
        # Parse summary
        match = re.search(r'Summary[:\s]*(.+?)(?:\n|$)', response, re.IGNORECASE)
        if match:
            result.summary = match.group(1).strip()
        
        # Parse missing events
        missing_events_section = re.search(
            r'Missing Events[:\s]*\n(.*?)(?:Missing Details|Overall|Verdict|$)',
            response,
            re.IGNORECASE | re.DOTALL
        )
        if missing_events_section:
            events_text = missing_events_section.group(1)
            for line in events_text.strip().split('\n'):
                line = line.strip()
                if line.startswith('-') or line.startswith('•'):
                    line = line[1:].strip()
                    if line and line.lower() not in ['none', 'n/a', 'no missing events']:
                        # Try to extract date
                        date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})', line)
                        result.missing_events.append(MissingItem(
                            item_type="event",
                            description=line,
                            date=date_match.group(1) if date_match else None,
                            severity="high",
                        ))
        
        # Parse missing details
        missing_details_section = re.search(
            r'Missing Details[:\s]*\n(.*?)(?:Overall|Verdict|Confidence|$)',
            response,
            re.IGNORECASE | re.DOTALL
        )
        if missing_details_section:
            details_text = missing_details_section.group(1)
            for line in details_text.strip().split('\n'):
                line = line.strip()
                if line.startswith('-') or line.startswith('•'):
                    line = line[1:].strip()
                    if line and line.lower() not in ['none', 'n/a', 'no missing details']:
                        result.missing_details.append(MissingItem(
                            item_type="detail",
                            description=line,
                            severity="medium",
                        ))
        
        # Calculate coverage from events if not provided
        if result.total_source_events > 0 and result.coverage_rate == 1.0:
            result.coverage_rate = result.covered_events / result.total_source_events
        
        return result


def check_completeness(
    output_md: str,
    source_index: SourceIndex,
    quick_mode: bool = False,
    verbose: bool = False,
) -> CompletenessResult:
    """
    Convenience function to check output completeness.
    
    Args:
        output_md: Output markdown to evaluate
        source_index: Indexed source text
        quick_mode: Use faster/cheaper evaluation
        verbose: Print progress
        
    Returns:
        CompletenessResult with coverage analysis
    """
    judge = CompletenessJudge(quick_mode=quick_mode)
    return judge.check_completeness(output_md, source_index, verbose=verbose)
