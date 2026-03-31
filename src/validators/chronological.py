"""
Chronological Order Validator.

Checks that dates in the output appear in the correct order
(ascending or descending) as specified by the contract.

Only examines ## and ### heading lines to avoid false positives
from dates mentioned in entry body text or scratchpad blocks.
"""

import re
from datetime import datetime
from typing import List, Tuple, Optional

from ..contracts.base import BenchmarkContract, ValidationError

_SCRATCHPAD_RE = re.compile(
    r"<(?:scratchpad|thinking|internal)>[\s\S]*?</(?:scratchpad|thinking|internal)>",
    re.IGNORECASE,
)

DATE_PATTERNS = [
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), "%Y-%m-%d"),
    (re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b"), "%m/%d/%Y"),
    (re.compile(r"\b(\d{2})/(\d{2})/(\d{2})\b"), "%m/%d/%y"),
    (re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b"), "Month"),
    (re.compile(r"(?:^|\s)((?:19|20)\d{2})(?:\s|$)"), "Year"),
]

MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


class ChronologicalValidator:
    """Validate that dates appear in the correct chronological order."""

    def __init__(self, contract: BenchmarkContract):
        self.contract = contract

    def validate(self, output_md: str) -> Tuple[float, List[ValidationError]]:
        if not self.contract.chronological_order:
            return 1.0, []

        cleaned = _SCRATCHPAD_RE.sub("", output_md)
        dates = self._extract_dates(cleaned)

        if len(dates) < 2:
            return 1.0, []

        ascending = self.contract.chronological_direction == "ascending"
        errors: List[ValidationError] = []
        in_order_pairs = 0
        total_pairs = len(dates) - 1

        for i in range(total_pairs):
            line_a, date_a, raw_a = dates[i]
            line_b, date_b, raw_b = dates[i + 1]

            if date_a == date_b:
                in_order_pairs += 1
                continue

            if ascending:
                if date_a <= date_b:
                    in_order_pairs += 1
                else:
                    errors.append(ValidationError(
                        code="OUT_OF_ORDER",
                        message=f"Date '{raw_b}' (line {line_b}) appears after '{raw_a}' (line {line_a}) but is earlier",
                        line=line_b,
                        expected=f"Date >= {raw_a}",
                        actual=raw_b,
                    ))
            else:
                if date_a >= date_b:
                    in_order_pairs += 1
                else:
                    errors.append(ValidationError(
                        code="OUT_OF_ORDER",
                        message=f"Date '{raw_b}' (line {line_b}) appears after '{raw_a}' (line {line_a}) but is later",
                        line=line_b,
                        expected=f"Date <= {raw_a}",
                        actual=raw_b,
                    ))

        score = in_order_pairs / total_pairs if total_pairs > 0 else 1.0
        return score, errors

    def _extract_dates(self, text: str) -> List[Tuple[int, datetime, str]]:
        """Extract (line_number, datetime, raw_text) from ## and ### heading lines only.

        Restricting to headings avoids false positives from historical dates
        mentioned in entry body text (e.g. "Last recorded weight on 12/19/23").
        """
        results: List[Tuple[int, datetime, str]] = []
        seen_on_line: dict = {}

        for line_num, line in enumerate(text.split("\n"), start=1):
            stripped = line.strip()
            if not stripped.startswith("#"):
                continue

            for pattern, fmt in DATE_PATTERNS:
                for match in pattern.finditer(line):
                    parsed = self._parse_match(match, fmt)
                    if parsed and line_num not in seen_on_line:
                        seen_on_line[line_num] = True
                        results.append((line_num, parsed, match.group(0)))

        return results

    def _parse_match(self, match: re.Match, fmt: str) -> Optional[datetime]:
        try:
            if fmt == "Year":
                year = int(match.group(1))
                return datetime(year, 1, 1)
            if fmt == "Month":
                month = MONTH_MAP.get(match.group(1).lower())
                day = int(match.group(2))
                year = int(match.group(3))
                if month:
                    return datetime(year, month, day)
                return None
            return datetime.strptime(match.group(0), fmt)
        except (ValueError, IndexError):
            return None
