"""
Hallucination Judge for verifying claims against source text.

This module provides LLM-based verification of whether claims
in the output are supported by the source documents.

Supports three execution modes:
- Single mode: 1 claim = 1 API call (original)
- Batch mode: N claims = 1 API call (optimized, default)
- Parallel mode: Multiple batches concurrently (fastest)

Token limits are configurable via environment variables:
- BENCHMARK_MAX_SOURCE_CHARS: Max characters for source text (default: 30000)
- BENCHMARK_MAX_CLAIM_CHARS: Max characters per claim (default: 200)
"""

import asyncio
import json
import os
import re
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn, TaskProgressColumn
from rich.console import Console
from rich.live import Live
from rich.table import Table

from .base import LLMJudge, JudgeVerdict, Verdict
from .claim_extractor import Claim, ClaimExtractor, Citation
from .exceptions import APIError, ParsingError, TokenLimitError
from ..utils.source_index import SourceIndex
from ..utils.token_counter import count_tokens_tiktoken, truncate_to_token_limit
from ..contracts.llm_backend import LLMBackend, get_backend

# Rich console for pretty output
console = Console()


# Configurable limits via environment
# Set to 0 or negative to use full source (no truncation)
MAX_SOURCE_CHARS = int(os.getenv("BENCHMARK_MAX_SOURCE_CHARS", "0"))  # 0 = no limit
MAX_CLAIM_CHARS = int(os.getenv("BENCHMARK_MAX_CLAIM_CHARS", "200"))
MAX_SOURCE_EXCERPT_CHARS = int(os.getenv("BENCHMARK_MAX_SOURCE_EXCERPT_CHARS", "5000"))  # Per-claim source


# Prompt template for single claim checking (original)
HALLUCINATION_CHECK_PROMPT = """You are a fact-checking assistant. Your task is to determine if a claim is supported by the source text.

## Claim to Verify
Field Type: {field_type}
Claim: {claim}

## Source Text (from {source_info})
{source_excerpt}

## Instructions
1. Carefully read both the claim and the source text
2. Determine if the source text supports the claim
3. Consider semantic equivalence (e.g., "Type 2 Diabetes" = "Diabetes Mellitus Type 2")
4. Be strict: if the source doesn't mention something, it's UNSUPPORTED

## Response Format
Answer with EXACTLY this format:
Verdict: SUPPORTED | UNSUPPORTED | PARTIAL
Confidence: 0.0-1.0
Reason: <brief explanation in one sentence>

## Your Response:"""


# Prompt template for batch claim checking (optimized)
BATCH_HALLUCINATION_PROMPT = """You are a fact-checking assistant. Verify if each claim is supported by the source text.

## Source Text
{source_text}

## Claims to Verify
{claims_list}

## Instructions
For each claim:
1. Check if the source text supports the claim
2. Consider semantic equivalence (e.g., "Type 2 Diabetes" = "Diabetes Mellitus Type 2")
3. Be strict: if the source doesn't mention something, mark as UNSUPPORTED
4. PARTIAL means the source partially supports but misses some details

## Response Format
Return a JSON array with exactly one entry per claim:
```json
[
  {{"id": 1, "verdict": "SUPPORTED", "confidence": 0.9, "reason": "Source states patient has diabetes"}},
  {{"id": 2, "verdict": "UNSUPPORTED", "confidence": 0.8, "reason": "No mention of surgery in source"}},
  ...
]
```

Verdict options: SUPPORTED | UNSUPPORTED | PARTIAL

## Your Response (JSON only):"""


@dataclass
class HallucinationResult:
    """Result from hallucination checking."""
    total_claims: int = 0
    verified_claims: int = 0
    supported_claims: int = 0
    unsupported_claims: int = 0
    partial_claims: int = 0
    inconclusive_claims: int = 0  # Claims that couldn't be verified (truncated source)
    error_claims: int = 0
    
    verdicts: List[JudgeVerdict] = field(default_factory=list)
    
    # Timing
    total_time: float = 0.0
    avg_time_per_claim: float = 0.0
    api_calls: int = 0  # Track API calls for monitoring
    
    def compute_score(self) -> float:
        """
        Compute hallucination score (higher = less hallucination).
        
        INCONCLUSIVE claims are excluded from scoring since we can't
        determine if they're supported or not.
        """
        # Exclude inconclusive and error claims from scoring
        scorable_claims = (
            self.supported_claims + 
            self.partial_claims + 
            self.unsupported_claims
        )
        
        if scorable_claims == 0:
            return 1.0
        
        # SUPPORTED = 1.0, PARTIAL = 0.5, UNSUPPORTED = 0.0
        score = (
            self.supported_claims * 1.0 +
            self.partial_claims * 0.5 +
            self.unsupported_claims * 0.0
        ) / scorable_claims
        
        return score
    
    def to_dict(self) -> Dict:
        return {
            "total_claims": self.total_claims,
            "verified_claims": self.verified_claims,
            "supported_claims": self.supported_claims,
            "unsupported_claims": self.unsupported_claims,
            "partial_claims": self.partial_claims,
            "inconclusive_claims": self.inconclusive_claims,
            "error_claims": self.error_claims,
            "score": self.compute_score(),
            "timing": {
                "total_time": self.total_time,
                "avg_time_per_claim": self.avg_time_per_claim,
                "api_calls": self.api_calls,
            },
            "verdicts": [v.to_dict() for v in self.verdicts],
        }


class HallucinationJudge(LLMJudge):
    """
    LLM-based judge for verifying claims against source text.
    
    Uses Gemini to evaluate whether each claim is supported
    by the cited source text.
    
    Supports batch mode to reduce API calls:
    - batch_size=1: Original mode (1 claim per API call)
    - batch_size=10: Batch mode (10 claims per API call, 90% fewer calls)
    
    Supports LLMBackend for retry/fallback functionality.
    """
    
    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        temperature: float = 0.1,
        max_claims: int = 100,
        batch_size: int = 10,  # Default to batch mode
        max_workers: int = 5,  # Default concurrent workers
        backend: Optional[LLMBackend] = None,  # Use LLMBackend for retry/fallback
        **kwargs
    ):
        """
        Initialize HallucinationJudge.
        
        Args:
            model: Gemini model to use (ignored if backend is provided)
            temperature: Low temperature for consistent judging
            max_claims: Maximum claims to verify (for cost control)
            batch_size: Claims per API call (default: 10, set to 1 for single mode)
            max_workers: Max concurrent API calls (default: 5, for parallel mode)
            backend: Optional LLMBackend for retry/fallback support
            **kwargs: Additional args passed to LLMJudge
        """
        super().__init__(model=model, temperature=temperature, **kwargs)
        self.max_claims = max_claims
        self.batch_size = batch_size
        self.max_workers = int(os.getenv("MAX_WORKERS", str(max_workers)))
        self.claim_extractor = ClaimExtractor()
        
        # Use provided backend or create one with fallback support
        self._backend = backend
        self._backend_initialized = False
    
    def _get_backend(self, create_new: bool = False) -> Optional[LLMBackend]:
        """
        Get or create LLM backend with retry/fallback support.
        
        Args:
            create_new: If True, always create a new backend (for thread safety in parallel mode)
        """
        if self._backend is not None and not create_new:
            return self._backend
        
        if create_new or not self._backend_initialized:
            # Create a new backend with fallback support
            try:
                new_backend = get_backend()
                if not create_new:
                    self._backend = new_backend
                    self._backend_initialized = True
                return new_backend
            except Exception as e:
                if not self._backend_initialized:
                    print(f"⚠ Failed to create LLMBackend: {e}, falling back to LLMJudge")
                    self._backend_initialized = True
                return None
        
        return self._backend
    
    def _generate_with_fallback(self, prompt: str, use_new_backend: bool = False) -> str:
        """
        Generate response using backend (with retry/fallback) or fallback to LLMJudge.
        
        Args:
            prompt: The prompt to send
            use_new_backend: If True, create a new backend for thread safety
        """
        backend = self._get_backend(create_new=use_new_backend)
        if backend is not None:
            return backend.generate(prompt)
        else:
            # Fallback to parent class generate() without retry/fallback
            return self.generate(prompt)
    
    def evaluate(self, claim: str, source_excerpt: str, field_type: str = "Unknown") -> JudgeVerdict:
        """
        Evaluate if a single claim is supported by source text.
        
        Args:
            claim: The claim to verify
            source_excerpt: Source text that should support the claim
            field_type: Type of field (e.g., "Impression", "Diagnosis")
            
        Returns:
            JudgeVerdict with evaluation result
        """
        if not source_excerpt or not source_excerpt.strip():
            return JudgeVerdict(
                verdict=Verdict.ERROR,
                confidence=0.0,
                reason="No source text available for verification",
                claim=claim,
                source_excerpt="",
            )
        
        # Build prompt (use configurable limit)
        prompt = HALLUCINATION_CHECK_PROMPT.format(
            field_type=field_type,
            claim=claim[:MAX_CLAIM_CHARS],
            source_info="source document",
            source_excerpt=source_excerpt[:MAX_SOURCE_EXCERPT_CHARS],
        )
        
        try:
            response = self._generate_with_fallback(prompt)
            return self.parse_verdict(response, claim, source_excerpt)
        except Exception as e:
            return JudgeVerdict(
                verdict=Verdict.ERROR,
                confidence=0.0,
                reason=f"Error during evaluation: {str(e)}",
                claim=claim,
                source_excerpt=source_excerpt,
            )
    
    def evaluate_batch(
        self,
        claims: List[Claim],
        source_text: str,
        source_index: Optional[SourceIndex] = None,
        verbose: bool = False,
        parallel_mode: bool = False,
    ) -> List[JudgeVerdict]:
        """
        Evaluate multiple claims in a single API call.
        
        Uses citation-based source lookup when available for more accurate verification.
        
        Args:
            claims: List of claims to verify
            source_text: Full source text (fallback if citation lookup fails)
            source_index: Source index for citation-based lookup (optional)
            verbose: Print progress
            parallel_mode: If True, create new backend for thread safety
            
        Returns:
            List of JudgeVerdict for each claim
        """
        if not claims:
            return []
        
        if not source_text or not source_text.strip():
            return [
                JudgeVerdict(
                    verdict=Verdict.ERROR,
                    confidence=0.0,
                    reason="No source text available",
                    claim=c.text,
                    source_excerpt="",
                )
                for c in claims
            ]
        
        # Build claims list for prompt (truncate each claim)
        claims_list = "\n".join([
            f"{i+1}. [{c.field_type}] {c.text[:MAX_CLAIM_CHARS]}"
            for i, c in enumerate(claims)
        ])
        
        # Try to get relevant source text using citation-based lookup
        relevant_source, citation_success, was_truncated = self._get_relevant_source_for_batch(
            claims, source_index, source_text, verbose
        )
        
        # If citation lookup failed AND source was truncated, return INCONCLUSIVE
        # because we can't reliably verify claims against partial source
        if not citation_success and was_truncated:
            if verbose:
                print(f"   ⚠ Citation lookup failed and source truncated - returning INCONCLUSIVE")
            stored_excerpt = relevant_source[:2000] + "..." if len(relevant_source) > 2000 else relevant_source
            return [
                JudgeVerdict(
                    verdict=Verdict.INCONCLUSIVE,
                    confidence=0.3,
                    reason=f"Cannot reliably verify: citation lookup failed and source was truncated to {MAX_SOURCE_CHARS:,} chars. Claim may reference content beyond truncation point.",
                    claim=c.text,
                    source_excerpt=stored_excerpt,
                )
                for c in claims
            ]
        
        # Log token estimate if verbose
        if verbose:
            prompt_estimate = count_tokens_tiktoken(relevant_source + claims_list)
            print(f"   📊 Estimated input tokens: ~{prompt_estimate:,}")
        
        prompt = BATCH_HALLUCINATION_PROMPT.format(
            source_text=relevant_source,
            claims_list=claims_list,
        )
        
        try:
            response = self._generate_with_fallback(prompt, use_new_backend=parallel_mode)
            # Pass relevant_source to store in verdicts for tracing
            return self._parse_batch_response(response, claims, relevant_source)
        except (TimeoutError, ConnectionError, OSError) as e:
            # API errors - potentially retryable
            if verbose:
                print(f"   ⚠ API error (retryable): {e}")
            error_msg = str(e)[:200]
            return [
                JudgeVerdict(
                    verdict=Verdict.ERROR,
                    confidence=0.0,
                    reason=f"API error (retryable): {error_msg}",
                    claim=c.text,
                    source_excerpt="",
                )
                for c in claims
            ]
        except json.JSONDecodeError as e:
            # Parsing error - not retryable
            if verbose:
                print(f"   ⚠ JSON parsing error: {e}")
            return [
                JudgeVerdict(
                    verdict=Verdict.ERROR,
                    confidence=0.0,
                    reason=f"Parsing error: invalid JSON response - {str(e)[:100]}",
                    claim=c.text,
                    source_excerpt="",
                )
                for c in claims
            ]
        except Exception as e:
            if verbose:
                print(f"   ⚠ Batch evaluation error: {e}")
            # Return error verdicts for all claims with detailed error info
            error_type = type(e).__name__
            error_msg = str(e)[:200]
            return [
                JudgeVerdict(
                    verdict=Verdict.ERROR,
                    confidence=0.0,
                    reason=f"Batch evaluation error ({error_type}): {error_msg}",
                    claim=c.text,
                    source_excerpt="",
                )
                for c in claims
            ]
    
    def _get_relevant_source_for_batch(
        self,
        claims: List[Claim],
        source_index: Optional[SourceIndex],
        full_source: str,
        verbose: bool = False,
    ) -> Tuple[str, bool, bool]:
        """
        Get relevant source text for a batch of claims.
        
        Strategy:
        1. Try citation-based lookup for each claim
        2. Combine unique excerpts
        3. Fallback to full source (with optional truncation)
        
        Args:
            claims: List of claims with citations
            source_index: Source index for lookup
            full_source: Full source text as fallback
            verbose: Print progress
            
        Returns:
            Tuple of (source_text, citation_lookup_success, was_truncated)
        """
        excerpts = []
        seen_refs = set()
        citation_lookup_success = False
        was_truncated = False
        
        # Try to get source for each claim using citations
        if source_index:
            for claim in claims:
                for citation in claim.citations:
                    # Build a unique key for this citation
                    ref_key = f"{citation.file_id}:{citation.page}:{citation.paragraph_ref}"
                    if ref_key in seen_refs:
                        continue
                    seen_refs.add(ref_key)
                    
                    # Try to get source excerpt
                    excerpt = self._get_source_for_claim(claim, source_index)
                    if excerpt:
                        citation_lookup_success = True
                        # Add with citation info for context
                        header = f"[Source: {citation.file}, page {citation.page}]"
                        excerpts.append(f"{header}\n{excerpt[:MAX_SOURCE_EXCERPT_CHARS]}")
        
        # If we got citation-based excerpts, use them
        if excerpts:
            combined = "\n\n---\n\n".join(excerpts)
            if verbose:
                print(f"   📎 Using citation-based source ({len(excerpts)} excerpts, {len(combined):,} chars)")
            return combined, True, False
        
        # Fallback to full source
        if verbose:
            print(f"   📄 Using full source ({len(full_source):,} chars)")
        
        # Apply truncation only if MAX_SOURCE_CHARS is set (> 0)
        if MAX_SOURCE_CHARS > 0 and len(full_source) > MAX_SOURCE_CHARS:
            if verbose:
                print(f"   ⚠ Source truncated from {len(full_source):,} to {MAX_SOURCE_CHARS:,} chars")
            was_truncated = True
            return full_source[:MAX_SOURCE_CHARS] + "\n... (truncated)", False, True
        
        return full_source, False, False
    
    def _parse_batch_response(
        self, 
        response: str, 
        claims: List[Claim], 
        source_excerpt: str = ""
    ) -> List[JudgeVerdict]:
        """
        Parse batch JSON response into list of verdicts.
        
        Args:
            response: LLM response containing JSON array
            claims: Original claims for reference
            source_excerpt: The source text used for this batch (for tracing)
            
        Returns:
            List of JudgeVerdict
        """
        verdicts = []
        
        # Truncate source_excerpt for storage (keep first 2000 chars for tracing)
        stored_excerpt = source_excerpt[:2000] + "..." if len(source_excerpt) > 2000 else source_excerpt
        
        # Try to extract JSON from response
        json_match = re.search(r'\[[\s\S]*\]', response)
        if not json_match:
            # Fallback: return error verdicts with raw response preview
            raw_preview = response[:300].replace('\n', ' ').strip() if response else "(empty response)"
            return [
                JudgeVerdict(
                    verdict=Verdict.ERROR,
                    confidence=0.0,
                    reason=f"Could not parse batch response. Raw: {raw_preview}...",
                    claim=c.text,
                    source_excerpt=stored_excerpt,
                )
                for c in claims
            ]
        
        try:
            results = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            # Include JSON error details and raw preview
            raw_preview = json_match.group()[:300].replace('\n', ' ').strip()
            return [
                JudgeVerdict(
                    verdict=Verdict.ERROR,
                    confidence=0.0,
                    reason=f"Invalid JSON in batch response: {str(e)[:100]}. Raw: {raw_preview}...",
                    claim=c.text,
                    source_excerpt=stored_excerpt,
                )
                for c in claims
            ]
        
        # Map results back to claims
        results_by_id = {r.get('id', i+1): r for i, r in enumerate(results)}
        
        for i, claim in enumerate(claims):
            result = results_by_id.get(i + 1, {})
            
            # Parse verdict
            verdict_str = result.get('verdict', 'ERROR').upper()
            if verdict_str == 'SUPPORTED':
                verdict = Verdict.SUPPORTED
            elif verdict_str == 'UNSUPPORTED':
                verdict = Verdict.UNSUPPORTED
            elif verdict_str == 'PARTIAL':
                verdict = Verdict.PARTIAL
            else:
                verdict = Verdict.ERROR
            
            verdicts.append(JudgeVerdict(
                verdict=verdict,
                confidence=float(result.get('confidence', 0.5)),
                reason=result.get('reason', 'No reason provided'),
                claim=claim.text,
                source_excerpt=stored_excerpt,  # Store truncated source for tracing
            ))
        
        return verdicts
    
    def _create_stats_table(self, result: HallucinationResult, elapsed: float, total_items: int) -> Table:
        """Create a live stats table for progress display."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column(style="cyan")
        table.add_column(style="white")
        
        # Stats row
        stats = (
            f"[green]✅ {result.supported_claims}[/green]  "
            f"[red]❌ {result.unsupported_claims}[/red]  "
            f"[yellow]⚠ {result.partial_claims}[/yellow]  "
            f"[dim]🔴 {result.error_claims}[/dim]"
        )
        table.add_row("Stats:", stats)
        
        # Score row (live calculation)
        if result.verified_claims > 0:
            current_score = result.compute_score()
            score_color = "green" if current_score >= 0.8 else "yellow" if current_score >= 0.6 else "red"
            table.add_row("Score:", f"[{score_color}]{current_score:.1%}[/{score_color}]")
        
        # Speed row
        if elapsed > 0 and result.verified_claims > 0:
            speed = result.verified_claims / elapsed
            remaining = (total_items - result.verified_claims) / speed if speed > 0 else 0
            table.add_row("Speed:", f"{speed:.1f} claims/s | ~{remaining:.0f}s remaining")
        
        return table
    
    def verify_output(
        self,
        output_md: str,
        source_index: SourceIndex,
        verbose: bool = False,
    ) -> HallucinationResult:
        """
        Verify all claims in output against source text.
        
        Uses batch mode by default for efficiency.
        
        Args:
            output_md: Output markdown to verify
            source_index: Index of source text by citation
            verbose: Print progress
            
        Returns:
            HallucinationResult with all verdicts
        """
        result = HallucinationResult()
        start_time = time.time()
        
        # Extract claims
        claims = self.claim_extractor.extract(output_md)
        result.total_claims = len(claims)
        
        if verbose:
            console.print(f"[cyan]📋 Extracted {len(claims)} claims from output[/cyan]")
        
        # Limit claims for cost control
        claims_to_verify = claims[:self.max_claims]
        
        if verbose and len(claims) > self.max_claims:
            console.print(f"[yellow]   ⚠ Limiting to {self.max_claims} claims (cost control)[/yellow]")
        
        # Get full source text for batch mode
        source_text = source_index.get_full_text()
        
        # Use batch mode or single mode based on batch_size
        if self.batch_size > 1:
            # Batch mode: process claims in batches
            total_batches = (len(claims_to_verify) + self.batch_size - 1) // self.batch_size
            
            if verbose:
                console.print(f"[cyan]🔄 Batch mode: {self.batch_size} claims/batch, {total_batches} API calls[/cyan]")
                
                # Use rich progress bar
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(bar_width=40),
                    TaskProgressColumn(),
                    TimeElapsedColumn(),
                    TimeRemainingColumn(),
                    console=console,
                    transient=False,
                ) as progress:
                    task = progress.add_task(
                        "[cyan]🔍 Verifying claims...", 
                        total=len(claims_to_verify)
                    )
                    
                    for batch_idx in range(0, len(claims_to_verify), self.batch_size):
                        batch = claims_to_verify[batch_idx:batch_idx + self.batch_size]
                        batch_num = batch_idx // self.batch_size + 1
                        
                        # Update description with current stats
                        progress.update(
                            task, 
                            description=f"[cyan]🔍 Batch {batch_num}/{total_batches} | ✅{result.supported_claims} ❌{result.unsupported_claims} ⚠{result.partial_claims}"
                        )
                        
                        # Evaluate batch with source_index for citation-based lookup
                        batch_verdicts = self.evaluate_batch(batch, source_text, source_index, verbose=False)
                        result.api_calls += 1
                        
                        # Process verdicts
                        for verdict in batch_verdicts:
                            result.verdicts.append(verdict)
                            result.verified_claims += 1
                            
                            if verdict.verdict == Verdict.SUPPORTED:
                                result.supported_claims += 1
                            elif verdict.verdict == Verdict.UNSUPPORTED:
                                result.unsupported_claims += 1
                            elif verdict.verdict == Verdict.PARTIAL:
                                result.partial_claims += 1
                            elif verdict.verdict == Verdict.INCONCLUSIVE:
                                result.inconclusive_claims += 1
                            else:
                                result.error_claims += 1
                        
                        # Advance progress
                        progress.update(task, advance=len(batch))
            else:
                # Non-verbose mode: no progress bar
                for batch_idx in range(0, len(claims_to_verify), self.batch_size):
                    batch = claims_to_verify[batch_idx:batch_idx + self.batch_size]
                    batch_verdicts = self.evaluate_batch(batch, source_text, source_index, verbose=False)
                    result.api_calls += 1
                    
                    for verdict in batch_verdicts:
                        result.verdicts.append(verdict)
                        result.verified_claims += 1
                        
                        if verdict.verdict == Verdict.SUPPORTED:
                            result.supported_claims += 1
                        elif verdict.verdict == Verdict.UNSUPPORTED:
                            result.unsupported_claims += 1
                        elif verdict.verdict == Verdict.PARTIAL:
                            result.partial_claims += 1
                        elif verdict.verdict == Verdict.INCONCLUSIVE:
                            result.inconclusive_claims += 1
                        else:
                            result.error_claims += 1
        else:
            # Single mode: process claims one by one (original behavior)
            if verbose:
                console.print(f"[cyan]🔄 Single mode: 1 claim/API call, {len(claims_to_verify)} API calls[/cyan]")
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(bar_width=40),
                    TaskProgressColumn(),
                    TimeElapsedColumn(),
                    TimeRemainingColumn(),
                    console=console,
                    transient=False,
                ) as progress:
                    task = progress.add_task(
                        "[cyan]🔍 Verifying claims...", 
                        total=len(claims_to_verify)
                    )
                    
                    for i, claim in enumerate(claims_to_verify):
                        # Update description with current stats
                        progress.update(
                            task, 
                            description=f"[cyan]🔍 Claim {i+1}/{len(claims_to_verify)} | ✅{result.supported_claims} ❌{result.unsupported_claims} ⚠{result.partial_claims}"
                        )
                        
                        # Get source text for this claim
                        source_excerpt = self._get_source_for_claim(claim, source_index)
                        
                        if not source_excerpt:
                            result.error_claims += 1
                            result.verdicts.append(JudgeVerdict(
                                verdict=Verdict.ERROR,
                                confidence=0.0,
                                reason="Could not find source text for citation",
                                claim=claim.text,
                                source_excerpt="",
                            ))
                            progress.update(task, advance=1)
                            continue
                        
                        # Evaluate single claim
                        verdict = self.evaluate(claim.text, source_excerpt, claim.field_type)
                        result.api_calls += 1
                        result.verdicts.append(verdict)
                        result.verified_claims += 1
                        
                        if verdict.verdict == Verdict.SUPPORTED:
                            result.supported_claims += 1
                        elif verdict.verdict == Verdict.UNSUPPORTED:
                            result.unsupported_claims += 1
                        elif verdict.verdict == Verdict.PARTIAL:
                            result.partial_claims += 1
                        elif verdict.verdict == Verdict.INCONCLUSIVE:
                            result.inconclusive_claims += 1
                        else:
                            result.error_claims += 1
                        
                        progress.update(task, advance=1)
            else:
                # Non-verbose mode
                for i, claim in enumerate(claims_to_verify):
                    source_excerpt = self._get_source_for_claim(claim, source_index)
                    
                    if not source_excerpt:
                        result.error_claims += 1
                        result.verdicts.append(JudgeVerdict(
                            verdict=Verdict.ERROR,
                            confidence=0.0,
                            reason="Could not find source text for citation",
                            claim=claim.text,
                            source_excerpt="",
                        ))
                        continue
                    
                    verdict = self.evaluate(claim.text, source_excerpt, claim.field_type)
                    result.api_calls += 1
                    result.verdicts.append(verdict)
                    result.verified_claims += 1
                    
                    if verdict.verdict == Verdict.SUPPORTED:
                        result.supported_claims += 1
                    elif verdict.verdict == Verdict.UNSUPPORTED:
                        result.unsupported_claims += 1
                    elif verdict.verdict == Verdict.PARTIAL:
                        result.partial_claims += 1
                    elif verdict.verdict == Verdict.INCONCLUSIVE:
                        result.inconclusive_claims += 1
                    else:
                        result.error_claims += 1
        
        # Timing
        result.total_time = time.time() - start_time
        if result.verified_claims > 0:
            result.avg_time_per_claim = result.total_time / result.verified_claims
        
        if verbose:
            # Print final summary with rich formatting
            console.print()
            console.print("[bold green]✓ Verification Complete[/bold green]")
            console.print(f"  ⏱️  Time: {result.total_time:.1f}s ({result.api_calls} API calls)")
            console.print(f"  📊 Claims: {result.verified_claims}/{result.total_claims}")
            console.print(f"  [green]✅ Supported: {result.supported_claims}[/green]")
            console.print(f"  [red]❌ Unsupported: {result.unsupported_claims}[/red]")
            console.print(f"  [yellow]⚠  Partial: {result.partial_claims}[/yellow]")
            if result.inconclusive_claims > 0:
                console.print(f"  [cyan]❓ Inconclusive: {result.inconclusive_claims}[/cyan] (excluded from score)")
            console.print(f"  [dim]🔴 Errors: {result.error_claims}[/dim]")
            
            score = result.compute_score()
            score_color = "green" if score >= 0.8 else "yellow" if score >= 0.6 else "red"
            console.print(f"  [{score_color}]📈 Score: {score:.1%}[/{score_color}]")
        
        return result
    
    def _get_source_for_claim(self, claim: Claim, source_index: SourceIndex) -> Optional[str]:
        """
        Get source text for a claim from its citations.
        
        Args:
            claim: The claim with citations
            source_index: Source text index
            
        Returns:
            Source text excerpt or None
        """
        if not claim.citations:
            return None
        
        # Try each citation until we find source text
        for citation in claim.citations:
            # Try by paragraph_ref first (most specific)
            if citation.paragraph_ref:
                source = source_index.get_by_paragraph_ref(citation.paragraph_ref)
                if source:
                    return source
            
            # Try by file_id and page
            if citation.file_id:
                source = source_index.get_by_file_id(citation.file_id, int(citation.page) if citation.page.isdigit() else None)
                if source:
                    return source
            
            # Try by file and page
            if citation.file and citation.page:
                try:
                    page_num = int(citation.page)
                    source = source_index.get_excerpt(citation.file, page_num)
                    if source:
                        return source
                except ValueError:
                    pass
        
        return None
    
    async def evaluate_batch_async(
        self,
        claims: List[Claim],
        source_text: str,
        source_index: Optional[SourceIndex],
        semaphore: asyncio.Semaphore,
        batch_num: int,
        verbose: bool = False,
    ) -> Tuple[int, List[JudgeVerdict]]:
        """
        Async wrapper for evaluate_batch with concurrency control.
        
        Args:
            claims: List of claims to verify
            source_text: Source text to verify against
            source_index: Source index for citation-based lookup
            semaphore: Semaphore to control concurrency
            batch_num: Batch number for logging
            verbose: Print progress
            
        Returns:
            Tuple of (batch_num, list of JudgeVerdict)
        """
        async with semaphore:
            loop = asyncio.get_event_loop()
            # Run the synchronous function in a thread pool
            # Use parallel_mode=True to create a new backend for thread safety
            verdicts = await loop.run_in_executor(
                None,
                lambda: self.evaluate_batch(claims, source_text, source_index, verbose, parallel_mode=True)
            )
            return batch_num, verdicts
    
    async def verify_output_parallel_async(
        self,
        output_md: str,
        source_index: SourceIndex,
        verbose: bool = False,
    ) -> HallucinationResult:
        """
        Verify all claims in output against source text using parallel processing.
        
        Uses asyncio with semaphore to process multiple batches concurrently.
        
        Args:
            output_md: Output markdown to verify
            source_index: Index of source text by citation
            verbose: Print progress
            
        Returns:
            HallucinationResult with all verdicts
        """
        result = HallucinationResult()
        start_time = time.time()
        
        # Extract claims
        claims = self.claim_extractor.extract(output_md)
        result.total_claims = len(claims)
        
        if verbose:
            print(f"📋 Extracted {len(claims)} claims from output")
        
        # Limit claims for cost control
        claims_to_verify = claims[:self.max_claims]
        
        if verbose and len(claims) > self.max_claims:
            print(f"   Limiting to {self.max_claims} claims (cost control)")
        
        # Get full source text for batch mode
        source_text = source_index.get_full_text()
        
        # Split claims into batches
        batches = []
        for i in range(0, len(claims_to_verify), self.batch_size):
            batches.append(claims_to_verify[i:i + self.batch_size])
        
        total_batches = len(batches)
        
        if verbose:
            print(f"🚀 Parallel mode: {self.batch_size} claims/batch, {total_batches} batches, {self.max_workers} workers")
        
        # Create semaphore to control concurrency
        semaphore = asyncio.Semaphore(self.max_workers)
        
        # Create tasks for all batches with source_index for citation-based lookup
        tasks = [
            self.evaluate_batch_async(batch, source_text, source_index, semaphore, batch_num, verbose=False)
            for batch_num, batch in enumerate(batches, 1)
        ]
        
        # Process all batches concurrently
        try:
            batch_results = await asyncio.gather(*tasks)
            result.api_calls = total_batches
            
            # Sort results by batch number to maintain order
            batch_results.sort(key=lambda x: x[0])
            
            # Process verdicts
            for batch_num, verdicts in batch_results:
                for verdict in verdicts:
                    result.verdicts.append(verdict)
                    result.verified_claims += 1
                    
                    if verdict.verdict == Verdict.SUPPORTED:
                        result.supported_claims += 1
                    elif verdict.verdict == Verdict.UNSUPPORTED:
                        result.unsupported_claims += 1
                    elif verdict.verdict == Verdict.PARTIAL:
                        result.partial_claims += 1
                    else:
                        result.error_claims += 1
            
        except Exception as e:
            if verbose:
                print(f"❌ Error in parallel verification: {e}")
            raise
        
        # Timing
        result.total_time = time.time() - start_time
        if result.verified_claims > 0:
            result.avg_time_per_claim = result.total_time / result.verified_claims
        
        if verbose:
            print(f"✓ Parallel verification complete in {result.total_time:.1f}s ({result.api_calls} API calls)")
            print(f"  Supported: {result.supported_claims}/{result.verified_claims}")
            print(f"  Unsupported: {result.unsupported_claims}/{result.verified_claims}")
            print(f"  Score: {result.compute_score():.2%}")
        
        return result
    
    def verify_output_parallel(
        self,
        output_md: str,
        source_index: SourceIndex,
        verbose: bool = False,
    ) -> HallucinationResult:
        """
        Sync wrapper for parallel verification.
        
        Runs the async parallel verification in an event loop.
        
        Args:
            output_md: Output markdown to verify
            source_index: Index of source text by citation
            verbose: Print progress
            
        Returns:
            HallucinationResult with all verdicts
        """
        return asyncio.run(
            self.verify_output_parallel_async(output_md, source_index, verbose)
        )


def verify_hallucinations(
    output_md: str,
    source_text: str,
    model: str = "gemini-2.0-flash",
    max_claims: int = 50,
    batch_size: int = 10,
    max_workers: int = 5,
    parallel: bool = True,
    verbose: bool = False,
    backend: Optional["LLMBackend"] = None,
) -> HallucinationResult:
    """
    Convenience function to verify hallucinations.
    
    Args:
        output_md: Output markdown to verify
        source_text: Source text to verify against
        model: Gemini model to use (ignored if backend is provided)
        max_claims: Maximum claims to verify
        batch_size: Claims per API call (default: 10)
        max_workers: Max concurrent API calls (default: 5)
        parallel: Use parallel processing (default: True)
        verbose: Print progress
        backend: Optional LLMBackend instance (overrides model param)
        
    Returns:
        HallucinationResult
    """
    # Build source index
    source_index = SourceIndex(source_text)
    
    # Create judge and verify
    judge = HallucinationJudge(
        model=model,
        max_claims=max_claims,
        batch_size=batch_size,
        max_workers=max_workers,
        backend=backend,
    )
    
    if parallel and batch_size > 1:
        return judge.verify_output_parallel(output_md, source_index, verbose=verbose)
    else:
        return judge.verify_output(output_md, source_index, verbose=verbose)
