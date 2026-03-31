"""
Core data structures for benchmark validation.

This module defines the BenchmarkContract and related dataclasses
that form the foundation of the validation system.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any


@dataclass
class ValidationError:
    """Represents a formatting or structural error."""
    code: str
    message: str
    line: Optional[int] = None
    section: Optional[str] = None
    expected: Optional[str] = None
    actual: Optional[str] = None


@dataclass
class CoverageViolation:
    """Represents a missing field or incomplete data."""
    code: str
    field: str
    section: Optional[str] = None
    entry_index: Optional[int] = None
    details: Optional[str] = None


@dataclass 
class UnsupportedClaim:
    """Represents a claim not supported by source text."""
    claim: str
    verdict: str  # SUPPORTED | UNSUPPORTED | PARTIAL
    citation_file: Optional[str] = None
    citation_page: Optional[int] = None
    confidence: float = 0.0
    reason: Optional[str] = None


@dataclass
class MissingItem:
    """Represents missing information from completeness check."""
    item_type: str  # "event" or "detail"
    description: str
    date: Optional[str] = None
    severity: str = "medium"  # "high", "medium", "low"


@dataclass
class CompletenessDetails:
    """Detailed results from LLM completeness check."""
    total_source_events: int = 0
    covered_events: int = 0
    coverage_rate: float = 1.0
    missing_events: List["MissingItem"] = field(default_factory=list)
    missing_details: List["MissingItem"] = field(default_factory=list)
    verdict: str = "COMPLETE"  # COMPLETE | MOSTLY_COMPLETE | INCOMPLETE
    confidence: float = 1.0
    summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_source_events": self.total_source_events,
            "covered_events": self.covered_events,
            "coverage_rate": self.coverage_rate,
            "missing_events": [
                {"type": m.item_type, "description": m.description, "date": m.date, "severity": m.severity}
                for m in self.missing_events
            ],
            "missing_details": [
                {"type": m.item_type, "description": m.description, "severity": m.severity}
                for m in self.missing_details
            ],
            "verdict": self.verdict,
            "confidence": self.confidence,
            "summary": self.summary,
        }


@dataclass
class BenchmarkContract:
    """
    Validation rules extracted from instruction/schema.
    
    This is the unified contract that both V1 and V2 adapters must produce.
    It captures all the rules needed to validate an output.
    """
    
    section_name: str
    
    # Structure Rules
    heading_patterns: List[str] = field(default_factory=list)  # Regex for expected headings
    required_fields: List[str] = field(default_factory=list)   # Fields that must appear
    forbidden_fields: List[str] = field(default_factory=list)  # Fields that must NOT appear
    field_order: Optional[List[str]] = None                     # Expected ordering
    
    # Section Rules
    expected_sections: List[str] = field(default_factory=list)  # e.g., ["ATTESTATION", "COVER LETTERS", ...]
    section_order_strict: bool = False                           # Whether section order matters
    
    # Conditional Rules
    and_rules: List[Tuple[str, str]] = field(default_factory=list)  # Both must exist or both absent
    omit_if_missing: bool = False                                    # Omit section if no data
    
    # Citation Rules
    citation_required: bool = True
    citation_style: str = "inline"  # "inline" | "consolidated" | "per_event"
    citation_field: Optional[str] = None  # e.g., "Source References"
    citation_pattern: str = r'<!--\s*Source:.*?-->'  # Regex for citation format
    high_risk_fields: List[str] = field(default_factory=list)  # Fields requiring citation
    
    # Content Rules
    verbatim_required: bool = False  # Must quote source exactly
    date_format: Optional[str] = None  # Expected date format (e.g., "MM/DD/YY")
    grouping_rule: Optional[str] = None  # e.g., "same_date_same_provider_combine"
    
    # Entry Format Rules
    entry_header_pattern: Optional[str] = None  # e.g., r'\*\*<u>.*?</u>\*\*'
    entry_fields_by_section: Dict[str, List[str]] = field(default_factory=dict)
    
    # Exclusion Rules
    excluded_signers: List[str] = field(default_factory=list)  # e.g., ["Dr. Coppelson"]
    excluded_sources: List[str] = field(default_factory=list)  # Source types to exclude
    
    # === V2 Rules (extracted from structured instructions) ===
    
    # Forbidden words that must never appear in output (e.g., "None", "N/A", "Unknown")
    forbidden_words: List[str] = field(default_factory=list)
    
    # Max source citations per entry/bullet (e.g., 5 from "do not include beyond 5 source reference")
    source_citation_limit: Optional[int] = None
    
    # Expected heading hierarchy (e.g., ["## Condition Name", "### YYYY", "- **DD MMM YYYY**"])
    heading_hierarchy: List[str] = field(default_factory=list)
    
    # Chronological ordering requirements
    chronological_order: bool = False
    chronological_direction: str = "ascending"  # "ascending" | "descending"
    
    # Text to output when no data is found for this section
    empty_state_message: Optional[str] = None
    
    # Output type: "list" (structured records) or "single" (free-form markdown)
    output_type: str = "single"
    
    # Sort field for list-type outputs (e.g., "encounter_date")
    sort_by: Optional[str] = None
    
    # Document scope filters (e.g., ["Section F only", "exclude administrative"])
    scope_filters: List[str] = field(default_factory=list)
    
    # Whether deduplication is required
    dedup_required: bool = False
    
    # Explicitly forbidden behaviors from ANTI-PATTERNS sections
    anti_patterns: List[str] = field(default_factory=list)
    
    # Metadata
    raw_instruction: str = ""
    instruction_hash: str = ""
    instruction_version: str = ""  # SHA256 prefix for tracking instruction changes
    
    def __post_init__(self):
        """Compute instruction hash if not provided."""
        if self.raw_instruction and not self.instruction_hash:
            self.instruction_hash = hashlib.sha256(
                self.raw_instruction.encode('utf-8')
            ).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "section_name": self.section_name,
            "heading_patterns": self.heading_patterns,
            "required_fields": self.required_fields,
            "forbidden_fields": self.forbidden_fields,
            "field_order": self.field_order,
            "expected_sections": self.expected_sections,
            "section_order_strict": self.section_order_strict,
            "and_rules": self.and_rules,
            "omit_if_missing": self.omit_if_missing,
            "citation_required": self.citation_required,
            "citation_style": self.citation_style,
            "citation_field": self.citation_field,
            "citation_pattern": self.citation_pattern,
            "high_risk_fields": self.high_risk_fields,
            "verbatim_required": self.verbatim_required,
            "date_format": self.date_format,
            "grouping_rule": self.grouping_rule,
            "entry_header_pattern": self.entry_header_pattern,
            "entry_fields_by_section": self.entry_fields_by_section,
            "excluded_signers": self.excluded_signers,
            "excluded_sources": self.excluded_sources,
            "forbidden_words": self.forbidden_words,
            "source_citation_limit": self.source_citation_limit,
            "heading_hierarchy": self.heading_hierarchy,
            "chronological_order": self.chronological_order,
            "chronological_direction": self.chronological_direction,
            "empty_state_message": self.empty_state_message,
            "output_type": self.output_type,
            "sort_by": self.sort_by,
            "scope_filters": self.scope_filters,
            "dedup_required": self.dedup_required,
            "anti_patterns": self.anti_patterns,
            "instruction_hash": self.instruction_hash,
            "instruction_version": self.instruction_version,
        }
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BenchmarkContract":
        """Create from dictionary."""
        return cls(
            section_name=data.get("section_name", ""),
            heading_patterns=data.get("heading_patterns", []),
            required_fields=data.get("required_fields", []),
            forbidden_fields=data.get("forbidden_fields", []),
            field_order=data.get("field_order"),
            expected_sections=data.get("expected_sections", []),
            section_order_strict=data.get("section_order_strict", False),
            and_rules=[tuple(r) for r in data.get("and_rules", [])],
            omit_if_missing=data.get("omit_if_missing", False),
            citation_required=data.get("citation_required", True),
            citation_style=data.get("citation_style", "inline"),
            citation_field=data.get("citation_field"),
            citation_pattern=data.get("citation_pattern", r'<!--\s*Source:.*?-->'),
            high_risk_fields=data.get("high_risk_fields", []),
            verbatim_required=data.get("verbatim_required", False),
            date_format=data.get("date_format"),
            grouping_rule=data.get("grouping_rule"),
            entry_header_pattern=data.get("entry_header_pattern"),
            entry_fields_by_section=data.get("entry_fields_by_section", {}),
            excluded_signers=data.get("excluded_signers", []),
            excluded_sources=data.get("excluded_sources", []),
            forbidden_words=data.get("forbidden_words", []),
            source_citation_limit=data.get("source_citation_limit"),
            heading_hierarchy=data.get("heading_hierarchy", []),
            chronological_order=data.get("chronological_order", False),
            chronological_direction=data.get("chronological_direction", "ascending"),
            empty_state_message=data.get("empty_state_message"),
            output_type=data.get("output_type", "single"),
            sort_by=data.get("sort_by"),
            scope_filters=data.get("scope_filters", []),
            dedup_required=data.get("dedup_required", False),
            anti_patterns=data.get("anti_patterns", []),
            instruction_hash=data.get("instruction_hash", ""),
            instruction_version=data.get("instruction_version", ""),
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "BenchmarkContract":
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class TraceData:
    """Trace data for debugging and analysis."""
    claims: List[Dict[str, Any]] = field(default_factory=list)
    verdicts: List[Dict[str, Any]] = field(default_factory=list)
    hallucination_result: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "claims": self.claims,
            "verdicts": self.verdicts,
            "hallucination_result": self.hallucination_result,
        }


@dataclass
class SectionResult:
    """Benchmark result for a single section."""
    
    section_name: str
    
    # Core Scores (0.0 to 1.0) — original three dimensions
    formatting_score: float = 0.0
    completeness_score: float = 0.0
    hallucination_score: float = 0.0
    total_score: float = 0.0
    
    # V2 Rule Scores (0.0 to 1.0) — from deterministic validators
    forbidden_words_score: float = 1.0
    source_limit_score: float = 1.0
    chronological_score: float = 1.0
    heading_hierarchy_score: float = 1.0
    empty_state_score: float = 1.0
    field_completeness_score: float = 1.0
    clinical_coverage_score: float = 0.0
    date_coverage_score: float = 1.0
    
    # Core Errors
    formatting_errors: List[ValidationError] = field(default_factory=list)
    coverage_violations: List[CoverageViolation] = field(default_factory=list)
    unsupported_claims: List[UnsupportedClaim] = field(default_factory=list)
    
    # V2 Rule Violations
    forbidden_words_violations: List[ValidationError] = field(default_factory=list)
    source_limit_violations: List[ValidationError] = field(default_factory=list)
    chronological_violations: List[ValidationError] = field(default_factory=list)
    heading_hierarchy_violations: List[ValidationError] = field(default_factory=list)
    empty_state_violations: List[ValidationError] = field(default_factory=list)
    field_completeness_violations: List[ValidationError] = field(default_factory=list)
    date_coverage_violations: List[ValidationError] = field(default_factory=list)
    date_coverage_stats: Dict[str, Any] = field(default_factory=dict)
    
    # Completeness Details (from LLM judge)
    completeness_details: Optional[CompletenessDetails] = None
    
    # Trace Data (for debugging)
    trace: Optional[TraceData] = None
    
    # Stats
    total_entries: int = 0
    entries_with_citations: int = 0
    total_citations: int = 0
    
    # Metadata
    contract_version: str = "1.0"
    evaluated_at: datetime = field(default_factory=datetime.utcnow)
    
    def compute_total_score(self, weights: Tuple[float, float, float] = (0.33, 0.33, 0.34)):
        """Compute weighted total score (legacy 3-weight mode)."""
        self.total_score = (
            self.formatting_score * weights[0] +
            self.completeness_score * weights[1] +
            self.hallucination_score * weights[2]
        )
    
    def compute_total_score_v2(self, contract: Optional["BenchmarkContract"] = None):
        """
        Compute weighted total using all active dimensions.
        
        Dimensions with no corresponding contract rules get weight 0
        and their weight is redistributed proportionally to active dimensions.
        
        For models with no parsed entries, hallucination is excluded from
        weighting (no entries = nothing to hallucinate, not "perfect").
        """
        has_entries = (self.clinical_coverage_score > 0 or
                       self.completeness_score > 0 or
                       bool(self.date_coverage_stats and self.date_coverage_stats.get("model_dates", 0) > 0))

        dimensions = {
            "formatting": self.formatting_score,
            "completeness": self.completeness_score,
        }
        # Only include hallucination if the model actually produced entries
        if has_entries:
            dimensions["hallucination"] = self.hallucination_score
        
        # Use sidecar weights if available, otherwise use defaults.
        # Med-legal priority: Coverage > Traceability > Structure
        sidecar_weights = getattr(contract, '_sidecar_weights', None) if contract else None
        base_weights = sidecar_weights or {
            "formatting": 0.10,
            "completeness": 0.25,
            "hallucination": 0.20,       # traceability (source references)
            "forbidden_words": 0.05,
            "chronological": 0.10,
            "clinical_coverage": 0.10,
            "date_coverage": 0.20,
        }
        
        if contract:
            if contract.forbidden_words:
                dimensions["forbidden_words"] = self.forbidden_words_score
            if contract.chronological_order and has_entries:
                dimensions["chronological"] = self.chronological_score
            if self.clinical_coverage_score > 0:
                dimensions["clinical_coverage"] = self.clinical_coverage_score
            if self.date_coverage_stats:
                dimensions["date_coverage"] = self.date_coverage_score
        
        active_weights = {k: base_weights[k] for k in dimensions}
        weight_sum = sum(active_weights.values())
        
        if weight_sum == 0:
            self.total_score = 0.0
            return
        
        self.total_score = sum(
            dimensions[k] * (active_weights[k] / weight_sum)
            for k in dimensions
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        scores = {
            "formatting": self.formatting_score,
            "completeness": self.completeness_score,
            "traceability": self.hallucination_score,
            "chronological": self.chronological_score,
            "clinical_coverage": self.clinical_coverage_score,
            "date_coverage": self.date_coverage_score,
            "total": self.total_score,
        }
        if self.forbidden_words_violations:
            scores["forbidden_words"] = self.forbidden_words_score

        errors = {
            "formatting": [
                {"code": e.code, "message": e.message, "line": e.line}
                for e in self.formatting_errors
            ],
            "chronological": [
                {"code": e.code, "message": e.message}
                for e in self.chronological_violations
            ],
            "date_coverage": [
                {"code": e.code, "message": e.message}
                for e in self.date_coverage_violations
            ],
        }
        if self.forbidden_words_violations:
            errors["forbidden_words"] = [
                {"code": e.code, "message": e.message}
                for e in self.forbidden_words_violations
            ]

        result = {
            "section_name": self.section_name,
            "scores": scores,
            "stats": {
                "total_entries": self.total_entries,
                "entries_with_citations": self.entries_with_citations,
                "total_citations": self.total_citations,
            },
            "errors": errors,
            "date_coverage_stats": self.date_coverage_stats if self.date_coverage_stats else None,
            "metadata": {
                "contract_version": self.contract_version,
                "evaluated_at": self.evaluated_at.isoformat(),
            }
        }
        
        if self.completeness_details:
            result["completeness_details"] = self.completeness_details.to_dict()
        
        return result


@dataclass
class BenchmarkReport:
    """Complete benchmark report across all sections."""
    
    benchmark_version: str = "1.0.0"
    evaluated_at: datetime = field(default_factory=datetime.utcnow)
    mode: str = "v1"  # v1 or v2
    instruction_hash: str = ""
    
    overall_score: float = 0.0
    sections: List[SectionResult] = field(default_factory=list)
    
    # Summary statistics
    total_sections: int = 0
    formatting_errors_count: int = 0
    coverage_violations_count: int = 0
    unsupported_claims_count: int = 0
    
    def compute_overall_score(self):
        """Compute overall score from section scores."""
        if not self.sections:
            self.overall_score = 0.0
            return
        
        self.overall_score = sum(s.total_score for s in self.sections) / len(self.sections)
        self.total_sections = len(self.sections)
        self.formatting_errors_count = sum(len(s.formatting_errors) for s in self.sections)
        self.coverage_violations_count = sum(len(s.coverage_violations) for s in self.sections)
        self.unsupported_claims_count = sum(len(s.unsupported_claims) for s in self.sections)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "benchmark_version": self.benchmark_version,
            "evaluated_at": self.evaluated_at.isoformat(),
            "mode": self.mode,
            "instruction_hash": self.instruction_hash,
            "overall_score": self.overall_score,
            "sections": [s.to_dict() for s in self.sections],
            "summary": {
                "total_sections": self.total_sections,
                "formatting_errors": self.formatting_errors_count,
                "coverage_violations": self.coverage_violations_count,
                "unsupported_claims": self.unsupported_claims_count,
            }
        }
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
