"""
Extraction Accuracy Judge.

Uses LLM to verify whether extracted JSON entries are accurate
relative to the source document. Sends ALL entries in a single
batch call per model (one LLM call per model, not per entry).
"""

import json
import re
import random
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from .base import LLMJudge


@dataclass
class EntryVerdict:
    """Verdict for a single extracted entry."""
    entry_index: int
    encounter_date: str
    facility: str
    provider: str
    verdict: str  # ACCURATE | MINOR_ERRORS | MAJOR_ERRORS | HALLUCINATED
    accuracy_score: float  # 0.0 to 1.0
    issues: List[str] = field(default_factory=list)
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_index": self.entry_index,
            "encounter_date": self.encounter_date,
            "facility": self.facility,
            "provider": self.provider,
            "verdict": self.verdict,
            "accuracy_score": self.accuracy_score,
            "issues": self.issues,
            "reasoning": self.reasoning,
        }


@dataclass
class AccuracyResult:
    """Aggregate accuracy result."""
    total_checked: int = 0
    accurate_count: int = 0
    minor_errors_count: int = 0
    major_errors_count: int = 0
    hallucinated_count: int = 0
    average_score: float = 1.0
    entry_verdicts: List[EntryVerdict] = field(default_factory=list)

    def compute_score(self) -> float:
        if not self.entry_verdicts:
            return 1.0
        self.average_score = sum(v.accuracy_score for v in self.entry_verdicts) / len(self.entry_verdicts)
        return self.average_score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_checked": self.total_checked,
            "accurate_count": self.accurate_count,
            "minor_errors_count": self.minor_errors_count,
            "major_errors_count": self.major_errors_count,
            "hallucinated_count": self.hallucinated_count,
            "average_score": self.average_score,
            "entry_verdicts": [v.to_dict() for v in self.entry_verdicts],
        }


BATCH_ACCURACY_PROMPT = """You are a medical-legal document review expert. Your task is to verify whether extracted medical encounter entries are accurate based on the source document.

## Source Document
{source_text}

## Extracted Entries (JSON)
There are {entry_count} entries to evaluate. Each has an "entry_index" for reference.

```json
{entries_json}
```

## Instructions
For EACH entry, compare it against the source document and check:
1. **Date accuracy**: Is the encounter_date correct and verifiable in the source?
2. **Provider accuracy**: Is the provider_name correct? A provider name is HALLUCINATED if the person named was NOT the treating/attending provider for that encounter (e.g., a reviewing physician, a disability examiner, or a provider from a different encounter).
3. **Facility accuracy**: Is the facility_name correct and verifiable for this specific encounter?
4. **Clinical accuracy**: Are subjective, objective, diagnoses, plan, imaging findings faithful to the source?
5. **Hallucination check**: Does the entry contain ANY fabricated information not present in the source?

## Verdict Definitions (MUST follow consistently)

- **ACCURATE** (score 0.9-1.0): All facts correct and directly verifiable in source. Minor formatting differences are OK.
- **MINOR_ERRORS** (score 0.7-0.89): Small issues that do NOT change the medical meaning — e.g., minor omissions of non-critical details, slight paraphrasing, reasonable inferences from context. Core identity fields (date, provider, facility) are correct.
- **MAJOR_ERRORS** (score 0.4-0.69): Any of these → MAJOR: wrong provider name, wrong facility, wrong date, significant clinical facts attributed to wrong encounter, or mixing data from different encounters. A hallucinated provider name is ALWAYS at least MAJOR_ERRORS.
- **HALLUCINATED** (score 0.0-0.39): The entry is largely fabricated — the encounter doesn't exist in the source, or most fields are invented.

CRITICAL: Be consistent. The same type of error (e.g., attributing a reviewing physician as the treating provider) MUST receive the same verdict category across all entries.

## Response Format
Return a JSON array with one verdict per entry. Keep reasoning SHORT (1-2 sentences max).

```json
[
  {{
    "entry_index": 0,
    "verdict": "ACCURATE|MINOR_ERRORS|MAJOR_ERRORS|HALLUCINATED",
    "accuracy_score": 0.0-1.0,
    "issues": ["field_name that has the issue"],
    "reasoning": "Brief explanation"
  }}
]
```
"""


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[len("```json"):].strip()
    elif text.startswith("```"):
        text = text[3:].strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    return text


class ExtractionAccuracyJudge(LLMJudge):
    """Judge extraction accuracy of JSON entries against source (batch mode).

    Checks ALL included entries by splitting into batches of `batch_size`.
    """

    def __init__(self, batch_size: int = 25, **kwargs):
        super().__init__(max_tokens=8192, **kwargs)
        self.batch_size = batch_size

    def check_accuracy(
        self,
        entries: List[Dict[str, Any]],
        source_text: str,
        verbose: bool = False,
    ) -> AccuracyResult:
        included = [
            (i, e) for i, e in enumerate(entries)
            if isinstance(e, dict) and e.get("include") is True
        ]

        if not included:
            return AccuracyResult()

        batches = [
            included[i:i + self.batch_size]
            for i in range(0, len(included), self.batch_size)
        ]

        if verbose:
            print(f"   Checking all {len(included)} entries in {len(batches)} batch(es)...")

        result = AccuracyResult(total_checked=len(included))

        for batch_idx, batch in enumerate(batches):
            if verbose and len(batches) > 1:
                print(f"   Batch {batch_idx + 1}/{len(batches)} ({len(batch)} entries)...")

            tagged_entries = [{"entry_index": idx, **entry} for idx, entry in batch]

            prompt = BATCH_ACCURACY_PROMPT.format(
                source_text=source_text,
                entry_count=len(tagged_entries),
                entries_json=json.dumps(tagged_entries, indent=2),
            )

            try:
                response = self.generate(prompt)
                verdicts = self._parse_batch_response(response, batch)
            except Exception as e:
                if verbose:
                    print(f"   LLM error on batch {batch_idx + 1}: {e}")
                verdicts = [
                    EntryVerdict(
                        entry_index=idx,
                        encounter_date=entry.get("encounter_date", ""),
                        facility=entry.get("facility_name", ""),
                        provider=entry.get("provider_name", ""),
                        verdict="ERROR",
                        accuracy_score=0.5,
                        issues=[f"LLM error: {e}"],
                    )
                    for idx, entry in batch
                ]

            for v in verdicts:
                result.entry_verdicts.append(v)
                if v.verdict == "ACCURATE":
                    result.accurate_count += 1
                elif v.verdict == "MINOR_ERRORS":
                    result.minor_errors_count += 1
                elif v.verdict == "MAJOR_ERRORS":
                    result.major_errors_count += 1
                elif v.verdict == "HALLUCINATED":
                    result.hallucinated_count += 1

        result.compute_score()
        return result

    def _parse_batch_response(
        self,
        response: str,
        sampled: List[tuple],
    ) -> List[EntryVerdict]:
        """Parse batch LLM response into list of EntryVerdicts."""
        cleaned = _strip_code_fences(response)

        # Try to find JSON array
        array_match = re.search(r'\[[\s\S]*\]', cleaned)
        if array_match:
            try:
                data_list = json.loads(array_match.group())
                if isinstance(data_list, list):
                    return self._map_verdicts(data_list, sampled)
            except json.JSONDecodeError:
                pass

        # Fallback: try to find individual JSON objects
        verdicts = []
        for obj_match in re.finditer(r'\{[^{}]*\}', cleaned):
            try:
                data = json.loads(obj_match.group())
                if "verdict" in data or "accuracy_score" in data:
                    verdicts.append(data)
            except json.JSONDecodeError:
                continue

        if verdicts:
            return self._map_verdicts(verdicts, sampled)

        # Complete fallback
        return [
            EntryVerdict(
                entry_index=idx,
                encounter_date=entry.get("encounter_date", ""),
                facility=entry.get("facility_name", ""),
                provider=entry.get("provider_name", ""),
                verdict="MINOR_ERRORS",
                accuracy_score=0.7,
                issues=["Could not parse LLM batch response"],
            )
            for idx, entry in sampled
        ]

    def _map_verdicts(
        self,
        data_list: List[Dict],
        sampled: List[tuple],
    ) -> List[EntryVerdict]:
        """Map parsed JSON verdicts back to entries."""
        idx_map = {idx: entry for idx, entry in sampled}
        verdicts = []

        # Build lookup by entry_index from LLM response
        response_map = {}
        for d in data_list:
            eidx = d.get("entry_index")
            if eidx is not None:
                response_map[eidx] = d

        for entry_idx, entry in sampled:
            d = response_map.get(entry_idx)
            if d:
                verdicts.append(EntryVerdict(
                    entry_index=entry_idx,
                    encounter_date=entry.get("encounter_date", ""),
                    facility=entry.get("facility_name", ""),
                    provider=entry.get("provider_name", ""),
                    verdict=d.get("verdict", "MINOR_ERRORS"),
                    accuracy_score=float(d.get("accuracy_score", 0.7)),
                    issues=d.get("issues", []),
                    reasoning=d.get("reasoning", ""),
                ))
            else:
                # No matching verdict from LLM, try positional fallback
                verdicts.append(EntryVerdict(
                    entry_index=entry_idx,
                    encounter_date=entry.get("encounter_date", ""),
                    facility=entry.get("facility_name", ""),
                    provider=entry.get("provider_name", ""),
                    verdict="MINOR_ERRORS",
                    accuracy_score=0.7,
                    issues=["No matching verdict in LLM response"],
                ))

        # If we got fewer verdicts from LLM than entries, try positional mapping
        if not any(d.get("entry_index") is not None for d in data_list) and len(data_list) == len(sampled):
            verdicts = []
            for (entry_idx, entry), d in zip(sampled, data_list):
                verdicts.append(EntryVerdict(
                    entry_index=entry_idx,
                    encounter_date=entry.get("encounter_date", ""),
                    facility=entry.get("facility_name", ""),
                    provider=entry.get("provider_name", ""),
                    verdict=d.get("verdict", "MINOR_ERRORS"),
                    accuracy_score=float(d.get("accuracy_score", 0.7)),
                    issues=d.get("issues", []),
                    reasoning=d.get("reasoning", ""),
                ))

        return verdicts
