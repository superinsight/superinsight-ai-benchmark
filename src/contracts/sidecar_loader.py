"""
Sidecar JSON loader for benchmark configuration.

Loads validation rules from a .benchmark.json file alongside the instruction.
This decouples the instruction (given to the LLM) from the benchmark rules
(used for scoring), allowing instructions to be written freely.

Lookup order:
  1. {instruction_path}.benchmark.json   (e.g. instruction.txt.benchmark.json)
  2. {instruction_stem}.benchmark.json   (e.g. instruction.benchmark.json)

If no sidecar is found, returns None so callers can fall back to V2/V1 parsers.
"""

import json
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any

from .base import BenchmarkContract


def _resolve_sidecar_path(instruction_path: str) -> Optional[Path]:
    """Find the sidecar JSON file for an instruction."""
    p = Path(instruction_path)

    candidates = [
        p.parent / f"{p.name}.benchmark.json",
        p.parent / f"{p.stem}.benchmark.json",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def load_sidecar(instruction_path: str, instruction_text: str = "") -> Optional[BenchmarkContract]:
    """
    Load a BenchmarkContract from a sidecar JSON file.

    Returns None if no sidecar file exists.
    """
    sidecar_path = _resolve_sidecar_path(instruction_path)
    if sidecar_path is None:
        return None

    with open(sidecar_path, "r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)

    inst_hash = ""
    if instruction_text:
        inst_hash = hashlib.sha256(instruction_text.encode("utf-8")).hexdigest()[:16]

    return _build_contract(data, instruction_text, inst_hash)


def _build_contract(data: Dict[str, Any], raw_instruction: str, inst_hash: str) -> BenchmarkContract:
    """Convert sidecar JSON into a BenchmarkContract."""

    inclusion = data.get("inclusion_rules", {})
    and_rules = []
    require_both = inclusion.get("require_both", [])
    if len(require_both) == 2:
        and_rules = [(require_both[0], require_both[1])]

    chrono = data.get("chronological_order", False)
    chrono_dir = data.get("chronological_direction", "ascending")

    scoring_weights = data.get("scoring_weights", {})

    contract = BenchmarkContract(
        section_name=data.get("section_name", "Unknown Section"),

        required_fields=data.get("required_fields", []),
        forbidden_fields=data.get("forbidden_fields", []),
        field_order=data.get("field_order"),

        expected_sections=data.get("expected_sections", []),
        section_order_strict=data.get("section_order_strict", False),

        and_rules=and_rules,
        omit_if_missing=data.get("omit_if_missing", False),

        citation_required=data.get("citation_style", "none") != "none",
        citation_style=data.get("citation_style", "inline"),
        citation_field=data.get("citation_field"),

        date_format=data.get("date_format"),

        forbidden_words=data.get("forbidden_words", []),
        source_citation_limit=data.get("source_citation_limit"),

        heading_hierarchy=data.get("heading_hierarchy", []),

        chronological_order=chrono,
        chronological_direction=chrono_dir,

        empty_state_message=data.get("empty_state_message"),

        output_type=data.get("output_type", "single"),
        sort_by=data.get("sort_by"),

        scope_filters=data.get("scope_filters", []),
        dedup_required=data.get("dedup_required", False),
        anti_patterns=data.get("anti_patterns", []),

        entry_header_pattern=data.get("entry_header_pattern"),

        raw_instruction=raw_instruction,
        instruction_hash=inst_hash,
        instruction_version=inst_hash,
    )

    if scoring_weights:
        contract._sidecar_weights = scoring_weights

    return contract
