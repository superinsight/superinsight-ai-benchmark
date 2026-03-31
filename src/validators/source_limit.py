"""
Source Limit Validator.

Checks that each entry/bullet does not exceed the maximum number of
source citations allowed by the contract.
"""

import re
from typing import List, Tuple

from ..contracts.base import BenchmarkContract, ValidationError

CITATION_PATTERN = re.compile(r"<!--\s*Source:.*?-->", re.DOTALL)


class SourceLimitValidator:
    """Validate that no entry exceeds the source citation limit."""

    def __init__(self, contract: BenchmarkContract):
        self.contract = contract

    def validate(self, output_md: str) -> Tuple[float, List[ValidationError]]:
        if self.contract.source_citation_limit is None:
            return 1.0, []

        limit = self.contract.source_citation_limit
        errors: List[ValidationError] = []
        total_entries = 0
        compliant_entries = 0

        chunks = self._split_into_entries(output_md)

        for line_num, chunk_text in chunks:
            citations = CITATION_PATTERN.findall(chunk_text)
            count = len(citations)
            if count == 0:
                continue

            total_entries += 1
            if count > limit:
                errors.append(ValidationError(
                    code="SOURCE_LIMIT_EXCEEDED",
                    message=f"Found {count} citations (limit: {limit})",
                    line=line_num,
                    expected=f"<= {limit} citations",
                    actual=f"{count} citations",
                ))
            else:
                compliant_entries += 1

        if total_entries == 0:
            return 1.0, []

        score = compliant_entries / total_entries
        return score, errors

    def _split_into_entries(self, text: str) -> List[Tuple[int, str]]:
        """Split output into (line_number, text) chunks by entry boundaries."""
        entries: List[Tuple[int, str]] = []
        current_lines: List[str] = []
        current_start = 1

        for i, line in enumerate(text.split("\n"), start=1):
            if re.match(r"^#{1,4}\s+", line) and current_lines:
                entries.append((current_start, "\n".join(current_lines)))
                current_lines = [line]
                current_start = i
            else:
                current_lines.append(line)

        if current_lines:
            entries.append((current_start, "\n".join(current_lines)))

        return entries
