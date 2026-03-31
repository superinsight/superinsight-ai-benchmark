"""
Formatting Validator for checking markdown structure and format.

This validator checks:
- Heading hierarchy and format
- Entry header format (bold + underline)
- Date format consistency
- Field formatting

Scratchpad / thinking blocks are stripped before structural checks
so that internal reasoning content does not inflate the denominator
or cause false positives. The presence of a scratchpad is still
flagged as a separate error.
"""

import re
from typing import List, Dict, Tuple, Optional
from ..contracts.base import BenchmarkContract, ValidationError

_SCRATCHPAD_RE = re.compile(
    r"<(?:scratchpad|thinking|internal)>[\s\S]*?</(?:scratchpad|thinking|internal)>",
    re.IGNORECASE,
)


class FormattingValidator:
    """
    Validate formatting rules in the output markdown.
    
    Checks:
    - Heading levels (##, ###, ####)
    - Entry header format (**<u>...</u>**)
    - Date format (MM/DD/YY or MM/DD/YYYY)
    - Field labels (**Field:**)
    - Section order
    """
    
    def __init__(self, contract: BenchmarkContract):
        self.contract = contract
        self.errors: List[ValidationError] = []
    
    def validate(self, output_md: str) -> Tuple[float, List[ValidationError]]:
        """
        Validate output markdown against contract.
        
        Args:
            output_md: The output markdown to validate
            
        Returns:
            Tuple of (score, list of errors)
        """
        self.errors = []

        # Detect extraneous content on the raw output first
        self._check_extraneous_content(output_md)

        # Strip scratchpad/thinking blocks so they don't pollute
        # structural checks or inflate the checkable-item count
        cleaned = _SCRATCHPAD_RE.sub("", output_md)

        lines = cleaned.split('\n')
        
        # Run structural checks on cleaned output
        self._check_main_heading(lines)
        self._check_section_headings(cleaned)
        self._check_section_order(cleaned)
        self._check_entry_headers(cleaned)
        self._check_date_format(cleaned)
        self._check_field_formatting(cleaned)
        
        # Calculate score
        # Score = 1 - (errors / total_checks)
        total_checks = self._count_checkable_items(cleaned)
        if total_checks == 0:
            score = 1.0
        else:
            error_count = len(self.errors)
            score = max(0.0, 1.0 - (error_count / total_checks))
        
        return score, self.errors
    
    def _check_main_heading(self, lines: List[str]) -> None:
        """Check that the main heading exists and is correct."""
        has_main_heading = False
        expected = f"# {self.contract.section_name}"
        
        for i, line in enumerate(lines):
            if line.strip().startswith('# '):
                has_main_heading = True
                if not line.strip().lower().startswith(expected.lower()):
                    self.errors.append(ValidationError(
                        code="MAIN_HEADING_MISMATCH",
                        message=f"Expected main heading '{expected}'",
                        line=i + 1,
                        expected=expected,
                        actual=line.strip(),
                    ))
                break
        
        if not has_main_heading:
            self.errors.append(ValidationError(
                code="MISSING_MAIN_HEADING",
                message=f"Missing main heading '# {self.contract.section_name}'",
                expected=expected,
            ))
    
    def _check_section_headings(self, output_md: str) -> None:
        """Check that section headings are properly formatted."""
        # Find all ## headings
        section_pattern = r'^##\s+(.+)$'
        matches = re.finditer(section_pattern, output_md, re.MULTILINE)
        
        found_sections = []
        for match in matches:
            section_name = match.group(1).strip().rstrip(':')
            found_sections.append(section_name.upper())
        
        # Check expected sections exist
        for expected_section in self.contract.expected_sections:
            if expected_section.upper() not in [s.upper() for s in found_sections]:
                # This is not necessarily an error - section may be empty
                pass
    
    def _check_section_order(self, output_md: str) -> None:
        """Check that sections appear in the correct order."""
        if not self.contract.section_order_strict:
            return
        
        # Find section positions
        section_positions = {}
        for section in self.contract.expected_sections:
            pattern = rf'^##\s+{re.escape(section)}:?'
            match = re.search(pattern, output_md, re.MULTILINE | re.IGNORECASE)
            if match:
                section_positions[section] = match.start()
        
        # Check order
        sorted_sections = sorted(section_positions.keys(), key=lambda s: section_positions[s])
        expected_order = [s for s in self.contract.expected_sections if s in section_positions]
        
        if sorted_sections != expected_order:
            self.errors.append(ValidationError(
                code="SECTION_ORDER_MISMATCH",
                message="Sections are not in the expected order",
                expected=str(expected_order),
                actual=str(sorted_sections),
            ))
    
    def _check_entry_headers(self, output_md: str) -> None:
        """Check that entry headers follow the expected format."""
        lines = output_md.split('\n')
        
        # Use contract's entry_header_pattern if defined
        if self.contract.entry_header_pattern:
            custom_pattern = self.contract.entry_header_pattern
            for i, line in enumerate(lines):
                stripped = line.strip()
                # Check if line looks like an entry header
                if self._looks_like_entry_header(stripped):
                    if not re.match(custom_pattern, stripped):
                        self.errors.append(ValidationError(
                            code="ENTRY_HEADER_FORMAT",
                            message="Entry header doesn't match expected pattern",
                            line=i + 1,
                            expected=custom_pattern,
                            actual=stripped[:100],
                        ))
            return
        
        # Default validation for both formats
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Format 1: **<u>...</u>** (Review of Records style)
            if stripped.startswith('**') and '<u>' in stripped:
                if not re.match(r'\*\*<u>.+</u>\*\*', stripped):
                    self.errors.append(ValidationError(
                        code="ENTRY_HEADER_FORMAT",
                        message="Entry header has incorrect format",
                        line=i + 1,
                        expected="**<u>DATE. Content.</u>**",
                        actual=stripped[:100],
                    ))
            
            # Format 2: ### MM/DD/YYYY (Medical Chronology style)
            # Only validate if it looks like a date-based entry
            elif stripped.startswith('### ') and not stripped.startswith('#### '):
                header_content = stripped[4:].strip()
                # Check if it starts with a date pattern - if so, validate format
                if re.match(r'\d{1,2}/\d{1,2}/\d{2,4}', header_content):
                    # This is a date-based entry header, validate it
                    pass  # Date format is checked in _check_date_format
    
    def _looks_like_entry_header(self, line: str) -> bool:
        """Check if a line looks like an entry header."""
        # If contract has custom entry_header_pattern, use it for detection too
        if self.contract.entry_header_pattern:
            if re.match(self.contract.entry_header_pattern, line):
                return True
        
        # Format 1: **<u>...</u>**
        if line.startswith('**<u>'):
            return True
        # Format 2: ### with date (Medical Chronology)
        if line.startswith('### ') and not line.startswith('#### '):
            header_content = line[4:].strip()
            # Only consider it an entry if it starts with a date
            if re.match(r'\d{1,2}/\d{1,2}/\d{2,4}', header_content):
                return True
        return False
    
    def _check_date_format(self, output_md: str) -> None:
        """Check that dates follow the expected format."""
        if not self.contract.date_format:
            return
        
        # Expected patterns
        if self.contract.date_format == "MM/DD/YY":
            expected_pattern = r'\d{2}/\d{2}/\d{2}(?!\d)'
            wrong_pattern = r'\d{2}/\d{2}/\d{4}'
        else:  # MM/DD/YYYY
            expected_pattern = r'\d{2}/\d{2}/\d{4}'
            wrong_pattern = r'\d{2}/\d{2}/\d{2}(?!\d)'
        
        # Find dates in entry headers (both formats)
        # Format 1: **<u>...</u>**
        entry_lines = re.findall(r'\*\*<u>([^<]+)</u>\*\*', output_md)
        
        # Format 2: ### MM/DD/... (Medical Chronology style - only date-based entries)
        entry_lines.extend(re.findall(r'^###\s+(\d{1,2}/\d{1,2}.+)$', output_md, re.MULTILINE))
        
        for entry in entry_lines:
            # Check for wrong format
            if re.search(wrong_pattern, entry):
                self.errors.append(ValidationError(
                    code="DATE_FORMAT",
                    message=f"Date format should be {self.contract.date_format}",
                    expected=self.contract.date_format,
                    actual=entry[:50],
                ))
    
    def _check_field_formatting(self, output_md: str) -> None:
        """Check that field labels are properly formatted."""
        # Field labels should be **Field Name:** format
        # Find all bold text that looks like field labels
        field_pattern = r'\*\*([^*]+):\*\*'
        matches = re.findall(field_pattern, output_md)
        
        # Check for common issues
        for field in matches:
            # Field should not have leading/trailing spaces
            if field != field.strip():
                self.errors.append(ValidationError(
                    code="FIELD_LABEL_WHITESPACE",
                    message=f"Field label has extra whitespace: '{field}'",
                    expected=field.strip(),
                    actual=field,
                ))
    
    def _check_extraneous_content(self, output_md: str) -> None:
        """Check for scratchpad, thinking, or other non-output content."""
        patterns = [
            (r'<scratchpad>[\s\S]*?</scratchpad>', "SCRATCHPAD_CONTENT",
             "Output contains <scratchpad> block — internal reasoning should not appear in final output"),
            (r'<thinking>[\s\S]*?</thinking>', "THINKING_CONTENT",
             "Output contains <thinking> block — internal reasoning should not appear in final output"),
            (r'<internal>[\s\S]*?</internal>', "INTERNAL_CONTENT",
             "Output contains <internal> block — internal reasoning should not appear in final output"),
        ]
        for pattern, code, message in patterns:
            matches = re.findall(pattern, output_md, re.IGNORECASE)
            if matches:
                self.errors.append(ValidationError(
                    code=code,
                    message=message,
                ))

    def _count_checkable_items(self, output_md: str) -> int:
        """Count total items that can be checked."""
        count = 0
        
        # Count sections (## but not ###)
        count += len(re.findall(r'^##\s+(?!#)', output_md, re.MULTILINE))
        
        # Count entries (both formats)
        # Format 1: **<u>...</u>**
        count += len(re.findall(r'\*\*<u>', output_md))
        # Format 2: ### MM/DD/... (Medical Chronology style - only date-based entries)
        # This ensures consistency with _check_entry_headers and _check_date_format
        count += len(re.findall(r'^###\s+\d{1,2}/\d{1,2}', output_md, re.MULTILINE))
        
        # Count fields
        count += len(re.findall(r'\*\*[^*]+:\*\*', output_md))
        
        # Base checks
        count += 5  # Main heading, section order, etc.
        
        return max(count, 1)


def validate_formatting(output_md: str, contract: BenchmarkContract) -> Tuple[float, List[ValidationError]]:
    """
    Convenience function to validate formatting.
    
    Args:
        output_md: Output markdown to validate
        contract: Benchmark contract with rules
        
    Returns:
        Tuple of (score, errors)
    """
    validator = FormattingValidator(contract)
    return validator.validate(output_md)
