"""
Forbidden Words Validator.

Checks that the output does not contain any words/phrases that the
instruction explicitly forbids (e.g., "None", "N/A", "Unknown").

Citations (<!-- Source: ... -->) are stripped before scanning so that
forbidden words appearing inside citation comments are not penalized.
"""

import re
from typing import List, Tuple

from ..contracts.base import BenchmarkContract, ValidationError


class ForbiddenWordsValidator:
    """Validate that output contains no forbidden words."""

    def __init__(self, contract: BenchmarkContract):
        self.contract = contract

    def validate(self, output_md: str) -> Tuple[float, List[ValidationError]]:
        if not self.contract.forbidden_words:
            return 1.0, []

        cleaned = re.sub(r"<!--.*?-->", "", output_md, flags=re.DOTALL)
        cleaned = re.sub(r"```.*?```", "", cleaned, flags=re.DOTALL)

        errors: List[ValidationError] = []

        for line_num, line in enumerate(cleaned.split("\n"), start=1):
            for word in self.contract.forbidden_words:
                pattern = re.compile(
                    r"(?<![a-zA-Z])" + re.escape(word) + r"(?![a-zA-Z])"
                )
                for match in pattern.finditer(line):
                    errors.append(ValidationError(
                        code="FORBIDDEN_WORD",
                        message=f"Forbidden word '{word}' found",
                        line=line_num,
                        expected=f"No occurrences of '{word}'",
                        actual=line.strip()[:120],
                    ))

        if not errors:
            return 1.0, []

        total_lines = max(len(cleaned.split("\n")), 1)
        violation_lines = len({e.line for e in errors})
        score = max(0.0, 1.0 - (violation_lines / total_lines))
        return score, errors
