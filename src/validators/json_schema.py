"""
JSON Schema Validator for structured output (list-type).

Validates:
- Output is valid JSON (with or without markdown code fences)
- Each entry has required fields with correct types
- Date format compliance (YYYY-MM-DD)
- Provider name kill-list rules
- Forbidden words in JSON values
- Entry count and include/exclude consistency
- Deduplication detection
"""

import json
import re
from typing import List, Tuple, Dict, Any, Optional

from ..contracts.base import BenchmarkContract, ValidationError


# Provider kill-list: credentials that do NOT qualify
NURSE_CREDENTIALS = {"RN", "LPN", "PCA", "MA"}
GENERIC_PROVIDERS = {"none", "unknown", "n/a", "staff", "tech", ""}
STATUS_PHRASES = {"cleared by pcp", "see attached", "treating physician"}

REQUIRED_ENTRY_FIELDS = {
    "include": bool,
    "encounter_date": (str, type(None)),
    "facility_name": (str, type(None)),
    "provider_name": (str, type(None)),
    "visit_type": (str, type(None)),
}

CLINICAL_FIELDS = [
    "subjective", "objective", "assessment", "plan",
    "diagnoses", "imaging_findings", "lab_results",
    "procedures", "medications", "referrals",
]

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences if present."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[len("```json"):].strip()
    elif text.startswith("```"):
        text = text[3:].strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    return text


def _is_nurse_only(provider: str) -> bool:
    """Check if provider has only nurse credentials (RN, LPN, PCA, MA)."""
    parts = re.split(r"[,;\s]+", provider.strip())
    creds_found = set()
    for part in parts:
        upper = part.strip().upper().rstrip(".")
        if upper in NURSE_CREDENTIALS:
            creds_found.add(upper)
    if not creds_found:
        return False
    qualifying = {"MD", "DO", "PA", "PA-C", "NP", "PT", "OT", "DPT",
                  "PHD", "LCSW", "LSW", "PSYD", "APRN", "DNP"}
    for part in parts:
        upper = part.strip().upper().rstrip(".")
        if upper in qualifying:
            return False
    return True


def _is_generic_provider(provider: str) -> bool:
    return provider.strip().lower() in GENERIC_PROVIDERS


def _is_status_phrase(provider: str) -> bool:
    return provider.strip().lower() in STATUS_PHRASES


class JsonSchemaValidator:
    """Validate JSON-structured output against contract rules."""

    def __init__(self, contract: BenchmarkContract):
        self.contract = contract

    def validate(self, output_text: str) -> Tuple[
        List[Dict[str, Any]],  # parsed entries
        float,                  # overall score
        List[ValidationError],  # errors
        Dict[str, Any],         # stats
    ]:
        """
        Parse and validate JSON output.

        Returns:
            (entries, score, errors, stats)
        """
        errors: List[ValidationError] = []
        stats: Dict[str, Any] = {}

        # 1. Parse JSON
        cleaned = _strip_code_fences(output_text)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            errors.append(ValidationError(
                code="INVALID_JSON",
                message=f"Output is not valid JSON: {e}",
            ))
            return [], 0.0, errors, {"parse_error": True}

        if not isinstance(data, list):
            errors.append(ValidationError(
                code="NOT_A_LIST",
                message=f"Expected JSON array, got {type(data).__name__}",
            ))
            return [], 0.0, errors, {"parse_error": True}

        stats["total_entries"] = len(data)
        stats["included_entries"] = 0
        stats["excluded_entries"] = 0

        # 2. Validate each entry
        type_errors = 0
        date_errors = 0
        provider_errors = 0
        forbidden_errors = 0
        exclude_reason_errors = 0
        include_consistency_errors = 0

        forbidden_words = [w.lower() for w in self.contract.forbidden_words]

        for i, entry in enumerate(data):
            if not isinstance(entry, dict):
                errors.append(ValidationError(
                    code="ENTRY_NOT_OBJECT",
                    message=f"Entry [{i}] is not a JSON object",
                ))
                type_errors += 1
                continue

            is_included = entry.get("include")

            if is_included is True:
                stats["included_entries"] = stats.get("included_entries", 0) + 1
            else:
                stats["excluded_entries"] = stats.get("excluded_entries", 0) + 1

            # 2a. Required fields & types
            for field_name, expected_type in REQUIRED_ENTRY_FIELDS.items():
                if field_name not in entry:
                    errors.append(ValidationError(
                        code="MISSING_FIELD",
                        message=f"Entry [{i}]: missing required field '{field_name}'",
                    ))
                    type_errors += 1
                else:
                    val = entry[field_name]
                    if not isinstance(val, expected_type):
                        errors.append(ValidationError(
                            code="WRONG_TYPE",
                            message=f"Entry [{i}]: '{field_name}' should be {expected_type}, got {type(val).__name__} ({repr(val)[:50]})",
                        ))
                        type_errors += 1

            # 2b. Date format (YYYY-MM-DD)
            enc_date = entry.get("encounter_date")
            if is_included and enc_date is not None:
                if not isinstance(enc_date, str) or not DATE_PATTERN.match(enc_date):
                    errors.append(ValidationError(
                        code="BAD_DATE_FORMAT",
                        message=f"Entry [{i}]: encounter_date '{enc_date}' is not YYYY-MM-DD",
                    ))
                    date_errors += 1

            # 2c. Provider name validation
            provider = entry.get("provider_name")
            if is_included and provider is not None:
                if _is_nurse_only(provider):
                    errors.append(ValidationError(
                        code="NURSE_INCLUDED",
                        message=f"Entry [{i}]: nurse-only provider '{provider}' should have include=false",
                    ))
                    provider_errors += 1
                elif _is_generic_provider(provider):
                    errors.append(ValidationError(
                        code="GENERIC_PROVIDER",
                        message=f"Entry [{i}]: generic provider '{provider}' should have include=false",
                    ))
                    provider_errors += 1
                elif _is_status_phrase(provider):
                    errors.append(ValidationError(
                        code="STATUS_PROVIDER",
                        message=f"Entry [{i}]: status phrase '{provider}' is not a valid provider",
                    ))
                    provider_errors += 1

            # 2d. Forbidden words in values
            if forbidden_words:
                for key, val in entry.items():
                    if isinstance(val, str):
                        val_lower = val.lower().strip()
                        for fw in forbidden_words:
                            if val_lower == fw:
                                errors.append(ValidationError(
                                    code="FORBIDDEN_VALUE",
                                    message=f"Entry [{i}].{key}: value '{val}' is a forbidden word",
                                ))
                                forbidden_errors += 1

            # 2e. Include/exclude consistency
            if is_included is False:
                exclude_reason = entry.get("exclude_reason")
                if not exclude_reason or (isinstance(exclude_reason, str) and exclude_reason.strip() == ""):
                    errors.append(ValidationError(
                        code="MISSING_EXCLUDE_REASON",
                        message=f"Entry [{i}]: include=false but no exclude_reason provided",
                    ))
                    exclude_reason_errors += 1

            if is_included is True:
                if not entry.get("encounter_date"):
                    errors.append(ValidationError(
                        code="INCLUDED_NO_DATE",
                        message=f"Entry [{i}]: include=true but encounter_date is missing/null",
                    ))
                    include_consistency_errors += 1
                if not entry.get("facility_name"):
                    errors.append(ValidationError(
                        code="INCLUDED_NO_FACILITY",
                        message=f"Entry [{i}]: include=true but facility_name is missing/null",
                    ))
                    include_consistency_errors += 1
                if not entry.get("provider_name"):
                    errors.append(ValidationError(
                        code="INCLUDED_NO_PROVIDER",
                        message=f"Entry [{i}]: include=true but provider_name is missing/null",
                    ))
                    include_consistency_errors += 1

        # 2f. Chronological order check (on included entries)
        if self.contract.chronological_order and self.contract.sort_by:
            included = [e for e in data if isinstance(e, dict) and e.get("include") is True]
            sort_field = self.contract.sort_by
            ascending = self.contract.chronological_direction == "ascending"
            prev_val = None
            chrono_errors = 0
            for e in included:
                val = e.get(sort_field)
                if val and prev_val:
                    if ascending and val < prev_val:
                        errors.append(ValidationError(
                            code="CHRONO_OUT_OF_ORDER",
                            message=f"Entry date '{val}' appears after '{prev_val}' but is earlier (expected ascending)",
                        ))
                        chrono_errors += 1
                    elif not ascending and val > prev_val:
                        errors.append(ValidationError(
                            code="CHRONO_OUT_OF_ORDER",
                            message=f"Entry date '{val}' appears after '{prev_val}' but is later (expected descending)",
                        ))
                        chrono_errors += 1
                if val:
                    prev_val = val
            stats["chrono_errors"] = chrono_errors

        # 2g. Duplicate detection
        seen_keys = {}
        dup_count = 0
        for i, entry in enumerate(data):
            if not isinstance(entry, dict) or entry.get("include") is not True:
                continue
            key = (
                entry.get("encounter_date", ""),
                (entry.get("facility_name") or "").lower().strip(),
                (entry.get("provider_name") or "").lower().strip(),
            )
            if key in seen_keys:
                errors.append(ValidationError(
                    code="DUPLICATE_ENTRY",
                    message=f"Entry [{i}] is a duplicate of entry [{seen_keys[key]}]: {key[0]} / {key[1]} / {key[2]}",
                ))
                dup_count += 1
            else:
                seen_keys[key] = i
        stats["duplicate_entries"] = dup_count

        # 2h. Clinical field coverage (for included entries)
        included_entries = [e for e in data if isinstance(e, dict) and e.get("include") is True]
        if included_entries:
            total_fields = 0
            filled_fields = 0
            for entry in included_entries:
                for cf in CLINICAL_FIELDS:
                    total_fields += 1
                    val = entry.get(cf)
                    if val and isinstance(val, str) and val.strip():
                        filled_fields += 1
            clinical_coverage = filled_fields / total_fields if total_fields else 0.0
        else:
            clinical_coverage = 0.0
        stats["clinical_field_coverage"] = round(clinical_coverage, 4)
        stats["clinical_fields_filled"] = filled_fields if included_entries else 0
        stats["clinical_fields_total"] = total_fields if included_entries else 0

        # Compute score
        total_checks = max(len(data) * 6, 1)  # ~6 checks per entry
        total_issues = type_errors + date_errors + provider_errors + forbidden_errors + exclude_reason_errors + include_consistency_errors + dup_count
        score = max(0.0, 1.0 - (total_issues / total_checks))

        stats.update({
            "type_errors": type_errors,
            "date_errors": date_errors,
            "provider_errors": provider_errors,
            "forbidden_value_errors": forbidden_errors,
            "exclude_reason_errors": exclude_reason_errors,
            "include_consistency_errors": include_consistency_errors,
        })

        return data, score, errors, stats
