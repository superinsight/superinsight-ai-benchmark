"""
Model Comparison Runner.

Evaluates the same instruction against multiple model outputs and
produces a side-by-side comparison report with:
- Deterministic scoring (formatting, schema, forbidden words, etc.)
- JSON schema validation (for list-type outputs)
- Optional LLM-based extraction accuracy checking
- Optional pairwise comparison between models

Config JSON format:
{
  "comparison_name": "Medical Chronology Model Comparison",
  "instruction": "examples/medical_chronology_instruction.txt",
  "source": "examples/benchmark_source_small.txt",
  "parser": "v2",
  "models": [
    {
      "name": "gemini-2.5-pro",
      "output": "outputs/gemini-2.5-pro/output.md",
      "provider": "gemini",
      "model_id": "gemini-2.5-pro"
    },
    ...
  ]
}
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple

from ..contracts.base import BenchmarkContract, SectionResult, ValidationError
from ..contracts.v1_parser import V1Parser
from ..contracts.v2_parser import V2Parser
from ..contracts.sidecar_loader import load_sidecar
from ..contracts.llm_backend import get_backend
from ..validators.json_schema import JsonSchemaValidator
from ..validators.date_coverage import DateCoverageValidator
from ..validators.markdown_entry_parser import parse_markdown_entries
from .calculator import ScoringCalculator


@dataclass
class ModelConfig:
    """Configuration for a single model's output."""
    name: str
    output: str
    provider: str = ""
    model_id: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelConfig":
        return cls(
            name=data["name"],
            output=data["output"],
            provider=data.get("provider", ""),
            model_id=data.get("model_id", ""),
        )


@dataclass
class ModelResult:
    """Benchmark result for a single model."""
    name: str
    provider: str = ""
    model_id: str = ""
    section_result: Optional[SectionResult] = None
    json_schema_score: float = 0.0
    json_schema_errors: List[ValidationError] = field(default_factory=list)
    json_stats: Dict[str, Any] = field(default_factory=dict)
    parsed_entries: List[Dict[str, Any]] = field(default_factory=list)
    raw_output: str = ""
    accuracy_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "name": self.name,
            "provider": self.provider,
            "model_id": self.model_id,
        }
        if self.section_result:
            d["scores"] = self.section_result.to_dict()["scores"]
            d["scores"]["json_schema"] = self.json_schema_score
            d["errors"] = self.section_result.to_dict()["errors"]
            d["errors"]["json_schema"] = [
                {"code": e.code, "message": e.message}
                for e in self.json_schema_errors
            ]
        d["json_stats"] = self.json_stats
        if self.accuracy_result:
            d["accuracy"] = self.accuracy_result
        if self.error:
            d["error"] = self.error
        return d


@dataclass
class ComparisonConfig:
    """Configuration for a model comparison run."""
    comparison_name: str = "Model Comparison"
    instruction: str = ""
    source: Optional[str] = None
    parser: str = "auto"
    base_path: str = ""
    models: List[ModelConfig] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], base_path: str = "") -> "ComparisonConfig":
        return cls(
            comparison_name=data.get("comparison_name", "Model Comparison"),
            instruction=data.get("instruction", ""),
            source=data.get("source"),
            parser=data.get("parser", "auto"),
            base_path=base_path,
            models=[ModelConfig.from_dict(m) for m in data.get("models", [])],
        )

    @classmethod
    def from_json_file(cls, path: str) -> "ComparisonConfig":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        base_path = str(Path(path).parent)
        return cls.from_dict(data, base_path)

    def resolve_path(self, path: str) -> str:
        if not path:
            return path
        if os.path.isabs(path):
            return path
        return os.path.join(self.base_path, path)


@dataclass
class ComparisonReport:
    """Complete comparison report across models."""
    comparison_name: str = ""
    instruction_file: str = ""
    section_name: str = ""
    results: List[ModelResult] = field(default_factory=list)
    pairwise: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "comparison_name": self.comparison_name,
            "instruction_file": self.instruction_file,
            "section_name": self.section_name,
            "models": [r.to_dict() for r in self.results],
            "ranking": self._compute_ranking(),
        }
        if self.pairwise:
            d["pairwise"] = self.pairwise
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def _compute_ranking(self) -> List[Dict[str, Any]]:
        ranked = [
            r for r in self.results
            if r.section_result is not None
        ]
        ranked.sort(key=lambda r: r.section_result.total_score, reverse=True)
        return [
            {"rank": i + 1, "name": r.name, "total_score": r.section_result.total_score}
            for i, r in enumerate(ranked)
        ]


class ModelComparisonRunner:
    """
    Run the same benchmark against multiple model outputs.

    Parses the instruction once, then evaluates each model's output
    against the shared contract. Supports:
    - Deterministic scoring (existing validators)
    - JSON schema validation (for list-type outputs)
    - LLM-based extraction accuracy (optional, --deep-check)
    - Pairwise comparison (optional, --deep-check)
    """

    def __init__(self, config: ComparisonConfig):
        self.config = config

    def run(
        self,
        verbose: bool = False,
        deep_check: bool = False,
    ) -> ComparisonReport:
        instruction_path = self.config.resolve_path(self.config.instruction)
        with open(instruction_path, "r", encoding="utf-8") as f:
            instruction_text = f.read()

        contract = self._parse_instruction(instruction_text, str(instruction_path))
        is_list_output = contract.output_type == "list"

        if verbose:
            print(f"Contract: {contract.section_name}")
            print(f"  Output type: {contract.output_type}")
            print(f"  Required fields: {len(contract.required_fields)}")
            if contract.forbidden_words:
                print(f"  Forbidden words: {contract.forbidden_words}")
            if contract.chronological_order:
                print(f"  Chronological: {contract.chronological_direction}")

        source_text = None
        if self.config.source:
            source_path = self.config.resolve_path(self.config.source)
            with open(source_path, "r", encoding="utf-8") as f:
                source_text = f.read()
            if verbose:
                print(f"  Source: {len(source_text):,} chars")

        has_v2_rules = bool(
            contract.forbidden_words
            or contract.source_citation_limit is not None
            or contract.chronological_order
        )

        report = ComparisonReport(
            comparison_name=self.config.comparison_name,
            instruction_file=self.config.instruction,
            section_name=contract.section_name,
        )

        json_validator = JsonSchemaValidator(contract) if is_list_output else None

        for model_cfg in self.config.models:
            if verbose:
                print(f"\n  Evaluating: {model_cfg.name}")

            result = ModelResult(
                name=model_cfg.name,
                provider=model_cfg.provider,
                model_id=model_cfg.model_id,
            )

            try:
                output_path = self.config.resolve_path(model_cfg.output)
                with open(output_path, "r", encoding="utf-8") as f:
                    output_md = f.read()
                result.raw_output = output_md

                # 1. Standard scoring (formatting, coverage, citation, V2 rules)
                calculator = ScoringCalculator(contract)
                section_result = calculator.calculate(
                    output_md,
                    source_text,
                    skip_llm_judge=True,
                    use_v2_scoring=has_v2_rules,
                    verbose=False,
                )
                section_result.section_name = model_cfg.name

                # 2. Parse entries — JSON validator for list-type, markdown parser otherwise
                entries = []
                if json_validator:
                    entries, schema_score, schema_errors, stats = json_validator.validate(output_md)
                    result.json_schema_score = schema_score
                    result.json_schema_errors = schema_errors
                    result.json_stats = stats
                    result.parsed_entries = entries

                    if entries:
                        section_result.formatting_score = schema_score
                        section_result.formatting_errors = schema_errors

                        chrono_errs = [e for e in schema_errors if e.code == "CHRONO_OUT_OF_ORDER"]
                        if contract.chronological_order:
                            included_count = stats.get("included_entries", 1) or 1
                            section_result.chronological_score = max(0.0, 1.0 - len(chrono_errs) / included_count)
                            section_result.chronological_violations = chrono_errs

                        fw_errs = [e for e in schema_errors if e.code == "FORBIDDEN_VALUE"]
                        if fw_errs:
                            total_vals = stats.get("total_entries", 1) * 6
                            section_result.forbidden_words_score = max(0.0, 1.0 - len(fw_errs) / total_vals)
                            section_result.forbidden_words_violations = fw_errs
                else:
                    entries = parse_markdown_entries(output_md)
                    result.parsed_entries = entries

                # 3. Entry-level metrics (works for both JSON and markdown-parsed entries)
                if entries:
                    self._compute_entry_metrics(
                        entries, section_result, contract, source_text, verbose,
                    )
                else:
                    # No entries parsed — set clinical/date coverage to 0
                    # so models that produce empty output don't get inflated scores
                    section_result.clinical_coverage_score = 0.0
                    section_result.date_coverage_score = 0.0
                    section_result.date_coverage_stats = {"source_dates_found": 0, "model_dates": 0, "covered": 0, "missed": 0, "coverage_ratio": 0.0}
                    section_result.completeness_score = 0.0

                # Recompute total with all updated dimension scores
                section_result.compute_total_score_v2(contract)

                if verbose and entries:
                    inc = len([e for e in entries if e.get("include") is not False])
                    print(f"    Entries parsed: {inc}")

                result.section_result = section_result

                if verbose:
                    print(f"    Total: {section_result.total_score:.2%}")

            except Exception as e:
                result.error = str(e)
                if verbose:
                    print(f"    ERROR: {e}")
                    import traceback
                    traceback.print_exc()

            report.results.append(result)

        # 4. Entry count scoring (cross-model comparison)
        self._compute_entry_count_scores(report, verbose)

        # 5. Consensus-based date coverage (replaces naive per-model date coverage)
        if source_text and any(r.parsed_entries for r in report.results):
            self._compute_date_coverage_with_consensus(report, source_text, contract, verbose)

        # 6. Update completeness from entry_count_score (cross-model relative)
        for r in report.results:
            if r.error or not r.section_result:
                continue
            entry_score = (r.json_stats or {}).get("entry_count_score")
            if entry_score is not None:
                r.section_result.completeness_score = entry_score
                r.section_result.compute_total_score_v2(contract)

        # 7. LLM-based checks (optional)
        if deep_check and source_text:
            self._run_deep_checks(report, source_text, verbose)

        return report

    def _compute_entry_metrics(
        self,
        entries: List[Dict[str, Any]],
        section_result: SectionResult,
        contract: BenchmarkContract,
        source_text: Optional[str],
        verbose: bool,
    ):
        """Compute entry-level metrics from parsed entries (JSON or markdown).

        Populates: clinical_coverage_score, date_coverage_score/stats,
        chronological_score (from structured dates).
        """
        included = [e for e in entries if e.get("include") is not False]
        if not included:
            return

        # Clinical field coverage — measures how much useful clinical data
        # was extracted per entry. "Not specified" / "N/A" / "None" don't count.
        CLINICAL_FIELDS = [
            "subjective", "objective", "assessment", "plan",
            "diagnoses", "imaging_findings", "lab_results",
            "procedures", "medications", "referrals",
        ]
        _EMPTY_PATTERNS = {"not specified", "n/a", "none", "not available", "not applicable", "unknown", ""}
        total_fields = 0
        filled_fields = 0
        for entry in included:
            for cf in CLINICAL_FIELDS:
                total_fields += 1
                val = entry.get(cf)
                if val and isinstance(val, str) and val.strip().lower() not in _EMPTY_PATTERNS:
                    filled_fields += 1
        if total_fields > 0:
            section_result.clinical_coverage_score = round(filled_fields / total_fields, 4)

        # Chronological order check (from structured encounter_date)
        # This overrides the text-based check from ScoringCalculator since
        # structured dates are more reliable than regex-based text matching
        if contract.chronological_order:
            section_result.chronological_violations = []
            ascending = contract.chronological_direction == "ascending"
            prev_date = None
            chrono_violations = 0
            for entry in included:
                d = entry.get("encounter_date")
                if d and prev_date:
                    if ascending and d < prev_date:
                        chrono_violations += 1
                        section_result.chronological_violations.append(
                            ValidationError(
                                code="CHRONO_OUT_OF_ORDER",
                                message=f"Date '{d}' after '{prev_date}' but is earlier (expected ascending)",
                            )
                        )
                    elif not ascending and d > prev_date:
                        chrono_violations += 1
                        section_result.chronological_violations.append(
                            ValidationError(
                                code="CHRONO_OUT_OF_ORDER",
                                message=f"Date '{d}' after '{prev_date}' but is later (expected descending)",
                            )
                        )
                if d:
                    prev_date = d
            if included:
                section_result.chronological_score = max(
                    0.0, 1.0 - chrono_violations / len(included)
                )

        # Traceability: what fraction of entries have source references?
        # In med-legal, every claim must be traceable back to source documents.
        # This is NOT a hallucination detector — real hallucination detection
        # requires the LLM Extraction Accuracy judge.
        entries_with_refs = sum(
            1 for e in included
            if e.get("source_references")
            and str(e["source_references"]).strip().lower() not in _EMPTY_PATTERNS
        )
        if included:
            section_result.hallucination_score = entries_with_refs / len(included)

        # Date coverage vs source
        if source_text:
            dc_validator = DateCoverageValidator()
            dc_score, dc_errors, dc_stats = dc_validator.validate(entries, source_text)
            section_result.date_coverage_score = dc_score
            section_result.date_coverage_violations = dc_errors
            section_result.date_coverage_stats = dc_stats
            if verbose:
                print(f"    Date coverage: {dc_score:.1%} "
                      f"({dc_stats.get('covered', 0)}/{dc_stats.get('source_dates_found', 0)} source dates)")

        if verbose:
            print(f"    Clinical coverage: {section_result.clinical_coverage_score:.1%}")
            print(f"    Source ref coverage: {entries_with_refs}/{len(included)} entries")

    def _compute_entry_count_scores(self, report: ComparisonReport, verbose: bool):
        """Score each model's entry count relative to the median across models.

        Models that extract significantly fewer entries than the median are
        penalized (potential missed extractions). Models with significantly
        more entries get a mild penalty (potential hallucinations/duplicates).
        """
        import statistics

        counts = []
        for r in report.results:
            if r.error or not r.parsed_entries:
                continue
            inc = len([e for e in r.parsed_entries if e.get("include") is not False])
            counts.append(inc)

        if len(counts) < 2:
            return

        median_count = statistics.median(counts)
        if median_count == 0:
            return

        if verbose:
            print(f"\n  Entry count median: {median_count:.0f}")

        for r in report.results:
            if r.error or not r.parsed_entries or not r.section_result:
                continue
            inc = len([e for e in r.parsed_entries if e.get("include") is not False])
            ratio = inc / median_count
            if ratio < 1.0:
                # Fewer than median → penalize (missing entries)
                # ratio 0.5 → score 0.5, ratio 0.8 → score 0.8
                score = max(0.0, ratio)
            elif ratio > 1.5:
                # Much more than median → mild penalty (possible hallucination)
                score = max(0.5, 1.0 - (ratio - 1.5) * 0.2)
            else:
                score = 1.0

            if r.json_stats is None:
                r.json_stats = {}
            r.json_stats["entry_count_score"] = round(score, 4)
            r.json_stats["entry_count_ratio"] = round(ratio, 4)
            r.json_stats["included_entries"] = inc
            if verbose:
                print(f"    {r.name}: {inc} entries (ratio={ratio:.2f}, score={score:.2%})")

    def _compute_date_coverage_with_consensus(
        self,
        report: ComparisonReport,
        source_text: str,
        contract: BenchmarkContract,
        verbose: bool,
    ):
        """Recompute date coverage using cross-model consensus.

        A source date is considered a "likely encounter date" only if at
        least one model extracted it.  Dates that *no* model extracted are
        assumed to be non-encounter dates (birth dates, insurance dates,
        filing dates, etc.) and are excluded from the expected set.
        """
        from ..validators.date_coverage import extract_dates_from_text, extract_dates_from_entries

        source_dates = extract_dates_from_text(source_text)
        if not source_dates:
            return

        model_date_sets: Dict[str, set] = {}
        for r in report.results:
            if r.error or not r.parsed_entries:
                continue
            model_date_sets[r.name] = extract_dates_from_entries(r.parsed_entries)

        if len(model_date_sets) < 2:
            return

        all_model_dates: set = set()
        for ds in model_date_sets.values():
            all_model_dates |= ds

        consensus_dates = source_dates & all_model_dates

        if verbose:
            excluded = source_dates - consensus_dates
            print(f"\n  Date consensus filter:")
            print(f"    Raw source dates: {len(source_dates)}")
            print(f"    Consensus encounter dates: {len(consensus_dates)}")
            print(f"    Excluded (no model extracted): {len(excluded)}")

        for r in report.results:
            if r.error or not r.parsed_entries or not r.section_result:
                continue

            my_dates = model_date_sets.get(r.name, set())

            if not consensus_dates:
                r.section_result.date_coverage_score = 1.0
                r.section_result.date_coverage_stats = {
                    "source_dates_found": len(source_dates),
                    "consensus_encounter_dates": 0,
                    "model_dates": len(my_dates),
                    "covered": 0, "missed": 0,
                    "coverage_ratio": 1.0,
                }
                continue

            covered = consensus_dates & my_dates
            missed = consensus_dates - my_dates
            score = len(covered) / len(consensus_dates)

            r.section_result.date_coverage_score = score
            r.section_result.date_coverage_violations = [
                ValidationError(
                    code="MISSED_DATE",
                    message=f"Date {d} is a consensus encounter date but missing from this model",
                )
                for d in sorted(missed)
            ]
            r.section_result.date_coverage_stats = {
                "source_dates_found": len(source_dates),
                "consensus_encounter_dates": len(consensus_dates),
                "model_dates": len(my_dates),
                "covered": len(covered),
                "missed": len(missed),
                "coverage_ratio": round(score, 4),
                "missed_dates": sorted(missed)[:20],
            }

            r.section_result.compute_total_score_v2(contract)

            if verbose:
                print(f"    {r.name}: {len(covered)}/{len(consensus_dates)} "
                      f"({score:.1%}), missed {len(missed)}")

    def _run_deep_checks(
        self,
        report: ComparisonReport,
        source_text: str,
        verbose: bool,
    ):
        """Run LLM-based extraction accuracy and pairwise comparison."""
        # Extraction accuracy
        try:
            from ..judges.extraction_accuracy import ExtractionAccuracyJudge

            if verbose:
                print(f"\n  🔬 Running extraction accuracy checks...")

            judge = ExtractionAccuracyJudge()
            for result in report.results:
                if result.parsed_entries and not result.error:
                    if verbose:
                        print(f"    {result.name}:")
                    acc = judge.check_accuracy(result.parsed_entries, source_text, verbose=verbose)
                    result.accuracy_result = acc.to_dict()
                    if verbose:
                        print(f"      Accuracy: {acc.average_score:.2%} ({acc.accurate_count} accurate, {acc.minor_errors_count} minor, {acc.major_errors_count} major)")
        except Exception as e:
            if verbose:
                print(f"    Accuracy check error: {e}")

        # Pairwise comparison
        try:
            from ..judges.pairwise import PairwiseJudge

            model_outputs = {}
            for result in report.results:
                if not result.error and result.raw_output:
                    entries = result.parsed_entries or []
                    model_outputs[result.name] = (entries, result.raw_output)

            if len(model_outputs) >= 2:
                if verbose:
                    print(f"\n  🏆 Running pairwise comparisons...")
                pw_judge = PairwiseJudge()
                pw_result = pw_judge.compare_all(model_outputs, source_text, verbose=verbose)
                report.pairwise = pw_result.to_dict()

                if verbose:
                    print(f"    Elo scores: {pw_result.elo_scores}")
        except Exception as e:
            if verbose:
                print(f"    Pairwise comparison error: {e}")

    def _parse_instruction(self, instruction_text: str, instruction_path: str = "") -> BenchmarkContract:
        # Priority 1: sidecar JSON (most accurate, zero parsing risk)
        if instruction_path:
            contract = load_sidecar(instruction_path, instruction_text)
            if contract is not None:
                return contract

        # Priority 2: V2 deterministic parser
        use_v2 = (
            self.config.parser == "v2"
            or (self.config.parser == "auto" and "PRIORITY 0" in instruction_text)
        )

        if use_v2:
            return V2Parser().parse(instruction_text)
        else:
            return V1Parser(backend=None, use_llm=False).parse(instruction_text)
