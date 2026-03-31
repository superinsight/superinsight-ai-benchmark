"""
Date Coverage Validator.

Extracts dates from the source document using regex patterns,
compares them against model output dates, and identifies
potential missed encounters (dates in source not in output).

This provides a deterministic "completeness" signal without
requiring a golden dataset.
"""

import re
from collections import Counter
from typing import List, Dict, Any, Set, Tuple

from ..contracts.base import ValidationError


# Common date patterns found in medical records
DATE_PATTERNS = [
    # YYYY-MM-DD (ISO)
    re.compile(r'\b(\d{4})-(\d{2})-(\d{2})\b'),
    # MM/DD/YYYY
    re.compile(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b'),
    # MM-DD-YYYY
    re.compile(r'\b(\d{1,2})-(\d{1,2})-(\d{4})\b'),
    # Month DD, YYYY (e.g., January 15, 2024)
    re.compile(
        r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+'
        r'(\d{1,2}),?\s+(\d{4})\b',
        re.IGNORECASE,
    ),
    # DD Month YYYY (e.g., 15 January 2024)
    re.compile(
        r'\b(\d{1,2})\s+'
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+'
        r'(\d{4})\b',
        re.IGNORECASE,
    ),
    # Mon DD, YYYY (e.g., Jan 15, 2024)
    re.compile(
        r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+'
        r'(\d{1,2}),?\s+(\d{4})\b',
        re.IGNORECASE,
    ),
]

MONTH_MAP = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "jun": "06", "jul": "07", "aug": "08", "sep": "09",
    "oct": "10", "nov": "11", "dec": "12",
}


def _normalize_date(match: re.Match, pattern_idx: int) -> str:
    """Normalize a regex match to YYYY-MM-DD format."""
    groups = match.groups()

    if pattern_idx == 0:
        # YYYY-MM-DD
        return f"{groups[0]}-{groups[1].zfill(2)}-{groups[2].zfill(2)}"
    elif pattern_idx == 1:
        # MM/DD/YYYY
        return f"{groups[2]}-{groups[0].zfill(2)}-{groups[1].zfill(2)}"
    elif pattern_idx == 2:
        # MM-DD-YYYY
        return f"{groups[2]}-{groups[0].zfill(2)}-{groups[1].zfill(2)}"
    elif pattern_idx == 3:
        # Month DD, YYYY
        month = MONTH_MAP.get(groups[0].lower().rstrip("."), "00")
        return f"{groups[2]}-{month}-{groups[1].zfill(2)}"
    elif pattern_idx == 4:
        # DD Month YYYY
        month = MONTH_MAP.get(groups[1].lower().rstrip("."), "00")
        return f"{groups[2]}-{month}-{groups[0].zfill(2)}"
    elif pattern_idx == 5:
        # Mon DD, YYYY (abbreviated)
        month = MONTH_MAP.get(groups[0].lower().rstrip("."), "00")
        return f"{groups[2]}-{month}-{groups[1].zfill(2)}"
    return ""


def _is_valid_date(date_str: str) -> bool:
    """Basic validation that a date string is plausible."""
    try:
        parts = date_str.split("-")
        if len(parts) != 3:
            return False
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        return 1900 <= y <= 2030 and 1 <= m <= 12 and 1 <= d <= 31
    except (ValueError, IndexError):
        return False


def extract_dates_from_text(text: str) -> Set[str]:
    """Extract all unique dates from text, normalized to YYYY-MM-DD."""
    dates: Set[str] = set()
    for idx, pattern in enumerate(DATE_PATTERNS):
        for match in pattern.finditer(text):
            normalized = _normalize_date(match, idx)
            if normalized and _is_valid_date(normalized):
                dates.add(normalized)
    return dates


def extract_dates_from_entries(entries: List[Dict[str, Any]], included_only: bool = True) -> Set[str]:
    """Extract encounter_date values from parsed JSON entries."""
    dates: Set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if included_only and entry.get("include") is not True:
            continue
        date_val = entry.get("encounter_date")
        if date_val and isinstance(date_val, str) and _is_valid_date(date_val):
            dates.add(date_val)
    return dates


class DateCoverageValidator:
    """Compare dates found in source vs. model output to detect missed encounters."""

    def validate(
        self,
        entries: List[Dict[str, Any]],
        source_text: str,
    ) -> Tuple[float, List[ValidationError], Dict[str, Any]]:
        """
        Compute date coverage score.

        Returns:
            (score, errors, stats)
            - score: fraction of source dates covered by model output
            - errors: list of MISSED_DATE validation errors
            - stats: detailed statistics
        """
        source_dates = extract_dates_from_text(source_text)
        model_dates = extract_dates_from_entries(entries, included_only=True)

        if not source_dates:
            return 1.0, [], {
                "source_dates_found": 0,
                "model_dates": len(model_dates),
                "covered": 0,
                "missed": 0,
                "extra": 0,
                "coverage_ratio": 1.0,
            }

        covered = source_dates & model_dates
        missed = source_dates - model_dates
        extra = model_dates - source_dates

        coverage_ratio = len(covered) / len(source_dates) if source_dates else 1.0

        errors: List[ValidationError] = []
        for d in sorted(missed):
            errors.append(ValidationError(
                code="MISSED_DATE",
                message=f"Date {d} found in source but not in model output",
            ))

        stats = {
            "source_dates_found": len(source_dates),
            "model_dates": len(model_dates),
            "covered": len(covered),
            "missed": len(missed),
            "extra": len(extra),
            "coverage_ratio": round(coverage_ratio, 4),
            "missed_dates": sorted(missed)[:20],
            "extra_dates": sorted(extra)[:20],
        }

        return coverage_ratio, errors, stats
