"""
Scoring Calculator for combining validation results.

This module combines scores from all validators into
a final benchmark score.
"""

from typing import Dict, Tuple, Optional
from dataclasses import dataclass

from ..contracts.base import (
    BenchmarkContract, 
    SectionResult, 
    BenchmarkReport,
    ValidationError,
    CoverageViolation,
    UnsupportedClaim,
    TraceData,
)
from ..validators.formatting import FormattingValidator
from ..validators.coverage import CoverageValidator
from ..validators.citation import CitationValidator
from ..validators.forbidden_words import ForbiddenWordsValidator
from ..validators.source_limit import SourceLimitValidator
from ..validators.chronological import ChronologicalValidator
from ..utils.source_index import SourceIndex


@dataclass
class ScoreWeights:
    """Weights for combining scores."""
    formatting: float = 0.33
    completeness: float = 0.33
    hallucination: float = 0.34
    
    def validate(self):
        """Ensure weights sum to 1.0."""
        total = self.formatting + self.completeness + self.hallucination
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")


class ScoringCalculator:
    """
    Calculate benchmark scores from validation results.
    
    Combines:
    - Formatting score (deterministic)
    - Completeness/Coverage score (deterministic + optional LLM)
    - Hallucination score (citation-based, optional LLM)
    """
    
    def __init__(
        self, 
        contract: BenchmarkContract,
        weights: Optional[ScoreWeights] = None
    ):
        self.contract = contract
        self.weights = weights or ScoreWeights()
        self.weights.validate()
    
    def calculate(
        self, 
        output_md: str,
        source_text: Optional[str] = None,
        skip_llm_judge: bool = True,
        max_claims: int = 50,
        batch_size: int = 10,
        max_workers: int = 5,
        parallel: bool = True,
        verbose: bool = False,
        collect_trace: bool = True,
        use_v2_scoring: bool = False,
    ) -> SectionResult:
        """
        Calculate all scores for the output.
        
        Args:
            output_md: The output markdown to evaluate
            source_text: Optional source text for hallucination checking
            skip_llm_judge: If True, skip expensive LLM judge calls
            max_claims: Maximum claims to verify with LLM judge
            batch_size: Claims per API call (default: 10, set 1 for single mode)
            max_workers: Max concurrent API calls (default: 5)
            parallel: Use parallel processing (default: True)
            verbose: Print progress for LLM judge
            collect_trace: Collect trace data (claims, verdicts) for debugging
            
        Returns:
            SectionResult with all scores and errors
        """
        result = SectionResult(section_name=self.contract.section_name)
        
        # Run formatting validation
        formatting_validator = FormattingValidator(self.contract)
        formatting_score, formatting_errors = formatting_validator.validate(output_md)
        result.formatting_score = formatting_score
        result.formatting_errors = formatting_errors
        
        # Run coverage validation (deterministic)
        coverage_validator = CoverageValidator(self.contract)
        coverage_score, coverage_violations = coverage_validator.validate(output_md)
        result.completeness_score = coverage_score
        result.coverage_violations = coverage_violations
        
        # Run citation validation
        citation_validator = CitationValidator(self.contract)
        citation_score, citation_errors, citation_stats = citation_validator.validate(output_md)
        
        # Update stats
        result.total_entries = citation_stats.get('total_entries', 0)
        result.entries_with_citations = citation_stats.get('entries_with_citations', 0)
        result.total_citations = citation_stats.get('total_citations', 0)
        
        # Build source index if we have source text
        source_index = None
        if source_text:
            source_index = SourceIndex(source_text)
        
        # LLM-based scoring (if enabled)
        if not skip_llm_judge and source_index is not None:
            # 1. Completeness check with LLM Judge
            from ..judges.completeness import CompletenessJudge
            from ..contracts.base import CompletenessDetails, MissingItem
            
            if verbose:
                print("\n📋 Running completeness check with LLM Judge...")
            
            completeness_judge = CompletenessJudge(quick_mode=False)
            completeness_result = completeness_judge.check_completeness(
                output_md, source_index, verbose=verbose
            )
            
            # Combine deterministic coverage with LLM completeness
            # Weight: 50% deterministic, 50% LLM
            llm_completeness_score = completeness_result.compute_score()
            result.completeness_score = (coverage_score * 0.5) + (llm_completeness_score * 0.5)
            
            # Store completeness details
            result.completeness_details = CompletenessDetails(
                total_source_events=completeness_result.total_source_events,
                covered_events=completeness_result.covered_events,
                coverage_rate=completeness_result.coverage_rate,
                missing_events=[
                    MissingItem(
                        item_type=m.item_type,
                        description=m.description,
                        date=m.date,
                        severity=m.severity,
                    )
                    for m in completeness_result.missing_events
                ],
                missing_details=[
                    MissingItem(
                        item_type=m.item_type,
                        description=m.description,
                        date=m.date,
                        severity=m.severity,
                    )
                    for m in completeness_result.missing_details
                ],
                verdict=completeness_result.verdict,
                confidence=completeness_result.confidence,
                summary=completeness_result.summary,
            )
            
            if verbose:
                print(f"   Deterministic coverage: {coverage_score:.2%}")
                print(f"   LLM completeness: {llm_completeness_score:.2%}")
                print(f"   Combined score: {result.completeness_score:.2%}")
                if completeness_result.missing_events:
                    print(f"   Missing events: {len(completeness_result.missing_events)}")
            
            # 2. Hallucination check with LLM Judge
            from ..judges.hallucination import HallucinationJudge
            
            if verbose:
                mode_str = "parallel" if parallel else "sequential"
                print(f"\n🔬 Running hallucination check with LLM Judge ({mode_str} mode)...")
            
            hallucination_judge = HallucinationJudge(
                max_claims=max_claims,
                batch_size=batch_size,
                max_workers=max_workers,
            )
            
            # Use parallel or sequential based on flag
            if parallel and batch_size > 1:
                hallucination_result = hallucination_judge.verify_output_parallel(
                    output_md, source_index, verbose=verbose
                )
            else:
                hallucination_result = hallucination_judge.verify_output(
                    output_md, source_index, verbose=verbose
                )
            
            # Use LLM judge score for hallucination
            result.hallucination_score = hallucination_result.compute_score()
            
            # Add unsupported claims to result
            for verdict in hallucination_result.verdicts:
                if verdict.verdict.value == "UNSUPPORTED":
                    result.unsupported_claims.append(UnsupportedClaim(
                        claim=verdict.claim,
                        verdict=verdict.verdict.value,
                        confidence=verdict.confidence,
                        reason=verdict.reason,
                    ))
            
            if verbose:
                print(f"   Hallucination score: {result.hallucination_score:.2%}")
                print(f"   Claims verified: {hallucination_result.verified_claims}")
                print(f"   Unsupported: {hallucination_result.unsupported_claims}")
            
            # Collect trace data if enabled
            if collect_trace:
                # Get claims from hallucination judge
                claims = hallucination_judge.claim_extractor.extract(output_md)
                result.trace = TraceData(
                    claims=[c.to_dict() for c in claims],
                    verdicts=[v.to_dict() for v in hallucination_result.verdicts],
                    hallucination_result=hallucination_result.to_dict(),
                )
        else:
            # Use citation coverage as proxy for hallucination score
            result.hallucination_score = citation_score
            result.formatting_errors.extend(citation_errors)
        
        # V2 Validators (deterministic, always run if contract has rules)
        if self.contract.forbidden_words:
            fw_score, fw_errors = ForbiddenWordsValidator(self.contract).validate(output_md)
            result.forbidden_words_score = fw_score
            result.forbidden_words_violations = fw_errors
            if verbose and fw_errors:
                print(f"   Forbidden words violations: {len(fw_errors)}")

        if self.contract.source_citation_limit is not None:
            sl_score, sl_errors = SourceLimitValidator(self.contract).validate(output_md)
            result.source_limit_score = sl_score
            result.source_limit_violations = sl_errors
            if verbose and sl_errors:
                print(f"   Source limit violations: {len(sl_errors)}")

        if self.contract.chronological_order:
            ch_score, ch_errors = ChronologicalValidator(self.contract).validate(output_md)
            result.chronological_score = ch_score
            result.chronological_violations = ch_errors
            if verbose and ch_errors:
                print(f"   Chronological violations: {len(ch_errors)}")

        # Compute weighted total
        if use_v2_scoring:
            result.compute_total_score_v2(self.contract)
        else:
            result.compute_total_score((
                self.weights.formatting,
                self.weights.completeness,
                self.weights.hallucination,
            ))
        
        return result
    
    def calculate_quick(self, output_md: str) -> Dict[str, float]:
        """
        Quick score calculation without detailed errors.
        
        Args:
            output_md: The output markdown to evaluate
            
        Returns:
            Dictionary with score values
        """
        result = self.calculate(output_md, skip_llm_judge=True)
        return {
            'formatting': result.formatting_score,
            'completeness': result.completeness_score,
            'hallucination': result.hallucination_score,
            'total': result.total_score,
        }


def calculate_scores(
    output_md: str,
    contract: BenchmarkContract,
    source_text: Optional[str] = None,
    weights: Optional[ScoreWeights] = None,
) -> SectionResult:
    """
    Convenience function to calculate all scores.
    
    Args:
        output_md: Output markdown to evaluate
        contract: Benchmark contract with rules
        source_text: Optional source text for hallucination checking
        weights: Optional score weights
        
    Returns:
        SectionResult with all scores
    """
    calculator = ScoringCalculator(contract, weights)
    return calculator.calculate(output_md, source_text)


def create_report(
    output_md: str,
    contract: BenchmarkContract,
    mode: str = "v1",
) -> BenchmarkReport:
    """
    Create a complete benchmark report.
    
    Args:
        output_md: Output markdown to evaluate
        contract: Benchmark contract with rules
        mode: Pipeline mode (v1 or v2)
        
    Returns:
        Complete BenchmarkReport
    """
    calculator = ScoringCalculator(contract)
    section_result = calculator.calculate(output_md)
    
    report = BenchmarkReport(
        mode=mode,
        instruction_hash=contract.instruction_hash,
        sections=[section_result],
    )
    report.compute_overall_score()
    
    return report
