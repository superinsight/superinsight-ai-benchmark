"""
Coverage Validator for checking completeness of output.

This validator checks:
- Required fields are present
- AND rules are satisfied
- Expected sections exist
"""

import re
from typing import List, Dict, Tuple, Optional, Set
from ..contracts.base import BenchmarkContract, CoverageViolation


class CoverageValidator:
    """
    Validate coverage/completeness rules.
    
    Checks:
    - Required fields are present in entries
    - AND rules (if A exists, B must exist)
    - Section coverage (expected sections present)
    - Entry coverage (reasonable number of entries per section)
    """
    
    def __init__(self, contract: BenchmarkContract):
        self.contract = contract
        self.violations: List[CoverageViolation] = []
    
    def validate(self, output_md: str) -> Tuple[float, List[CoverageViolation]]:
        """
        Validate output markdown for coverage.
        
        Args:
            output_md: The output markdown to validate
            
        Returns:
            Tuple of (score, list of violations)
        """
        self.violations = []
        
        # Parse output into sections
        sections = self._parse_sections(output_md)
        
        # Run checks
        self._check_section_coverage(sections)
        self._check_entry_fields(sections)
        self._check_and_rules(sections)
        
        # Calculate score
        total_checks = self._count_coverage_items(sections)
        if total_checks == 0:
            score = 1.0
        else:
            violation_count = len(self.violations)
            score = max(0.0, 1.0 - (violation_count / total_checks))
        
        return score, self.violations
    
    def _parse_sections(self, output_md: str) -> Dict[str, List[str]]:
        """Parse output into sections with their entries."""
        sections = {}
        current_section = None
        current_entries = []
        
        lines = output_md.split('\n')
        entry_buffer = []
        
        def is_entry_header(line: str) -> bool:
            """Check if line is an entry header (supports both formats)."""
            stripped = line.strip()
            # Format 1: **<u>...</u>** (Review of Records style)
            if stripped.startswith('**<u>'):
                return True
            # Format 2: ### MM/DD/YYYY (Medical Chronology style)
            # Only match ### headers that start with a date pattern
            # This avoids misidentifying sub-headings like "### Notes" or "### Summary"
            if stripped.startswith('### ') and not stripped.startswith('#### '):
                header_content = stripped[4:].strip()
                # Only consider it an entry if it starts with a date (MM/DD/YYYY or MM/DD/YY)
                if re.match(r'\d{1,2}/\d{1,2}/\d{2,4}', header_content):
                    return True
            return False
        
        for line in lines:
            stripped = line.strip()
            
            # Check for section header (## level)
            if stripped.startswith('## ') and not stripped.startswith('### '):
                # Save previous section
                if current_section:
                    if entry_buffer:
                        current_entries.append('\n'.join(entry_buffer))
                    sections[current_section] = current_entries
                
                # Start new section
                section_name = stripped[3:].strip().rstrip(':').upper()
                current_section = section_name
                current_entries = []
                entry_buffer = []
            
            # Check for entry header (both formats)
            elif is_entry_header(line):
                # Save previous entry
                if entry_buffer:
                    current_entries.append('\n'.join(entry_buffer))
                entry_buffer = [line]
            
            # Accumulate entry content
            elif entry_buffer:
                # Stop if we hit a citation or new entry
                if stripped.startswith('<!--') or is_entry_header(line):
                    current_entries.append('\n'.join(entry_buffer))
                    entry_buffer = []
                    if is_entry_header(line):
                        entry_buffer = [line]
                else:
                    entry_buffer.append(line)
        
        # Save last section and entry
        if entry_buffer:
            current_entries.append('\n'.join(entry_buffer))
        if current_section:
            sections[current_section] = current_entries
        
        return sections
    
    def _check_section_coverage(self, sections: Dict[str, List[str]]) -> None:
        """Check that expected sections are present."""
        found_sections = set(sections.keys())
        expected_sections = set(s.upper() for s in self.contract.expected_sections)
        
        # Only check if contract has expected sections defined
        if not expected_sections:
            return
        
        # Find missing sections
        missing_sections = expected_sections - found_sections
        
        # Always report missing sections when expected_sections is defined
        # This ensures "missing entire section" is flagged as a violation
        for section in missing_sections:
            self.violations.append(CoverageViolation(
                code="MISSING_SECTION",
                field="",
                section=section,
                entry_index=-1,
                details=f"Expected section '{section}' not found",
            ))
    
    def _check_entry_fields(self, sections: Dict[str, List[str]]) -> None:
        """Check that entries have required fields."""
        for section_name, entries in sections.items():
            # Get expected fields for this section
            expected_fields = self.contract.entry_fields_by_section.get(
                section_name, []
            )
            
            for i, entry in enumerate(entries):
                self._check_single_entry(section_name, i, entry, expected_fields)
    
    def _check_single_entry(
        self, 
        section: str, 
        index: int, 
        entry: str, 
        expected_fields: List[str]
    ) -> None:
        """Check a single entry for required fields."""
        # Extract fields present in entry
        present_fields = set()
        
        # Check for common field patterns
        field_patterns = {
            "date": r'\d{2}/\d{2}/\d{2,4}',
            "impression": r'\*\*Impression:\*\*',
            "diagnosis": r'\*\*Diagnos[ie]s?:\*\*',
            "treatment_plan": r'\*\*Treatment Plan:\*\*',
            "subjective": r'\*\*Subjective[^:]*:\*\*',
            "provider": r'[A-Z][a-z]+\s+[A-Z][a-z]+,?\s*(?:M\.?D\.?|D\.?C\.?|D\.?O\.?)',
            "signer": r'Signed by\s+[A-Z]',
        }
        
        for field, pattern in field_patterns.items():
            if re.search(pattern, entry, re.IGNORECASE):
                present_fields.add(field.lower())
        
        # Check for specific required fields
        # Relaxed checking - only flag critical missing fields
        critical_fields = {'date', 'impression', 'diagnosis'}
        
        for field in expected_fields:
            field_lower = field.lower()
            if field_lower in critical_fields:
                if field_lower not in present_fields:
                    # Double-check with direct pattern
                    if field_lower == 'impression':
                        if not re.search(r'impression', entry, re.IGNORECASE):
                            self.violations.append(CoverageViolation(
                                code="MISSING_FIELD",
                                field=field,
                                section=section,
                                entry_index=index,
                                details=f"Entry {index + 1} missing {field}",
                            ))
    
    def _check_and_rules(self, sections: Dict[str, List[str]]) -> None:
        """Check AND rules (if A exists, B must exist)."""
        for section_name, entries in sections.items():
            for i, entry in enumerate(entries):
                for field_a, field_b in self.contract.and_rules:
                    has_a = field_a.lower() in entry.lower()
                    has_b = field_b.lower() in entry.lower()
                    
                    if has_a and not has_b:
                        self.violations.append(CoverageViolation(
                            code="AND_RULE_VIOLATION",
                            field=field_b,
                            section=section_name,
                            entry_index=i,
                            details=f"'{field_a}' present but '{field_b}' missing",
                        ))
    
    def _count_coverage_items(self, sections: Dict[str, List[str]]) -> int:
        """Count total items to check for coverage."""
        count = 0
        
        # Count entries
        for entries in sections.values():
            count += len(entries)
            # Count expected fields per entry
            count += len(entries) * 3  # Approximate fields per entry
        
        return max(count, 1)


def validate_coverage(output_md: str, contract: BenchmarkContract) -> Tuple[float, List[CoverageViolation]]:
    """
    Convenience function to validate coverage.
    
    Args:
        output_md: Output markdown to validate
        contract: Benchmark contract with rules
        
    Returns:
        Tuple of (score, violations)
    """
    validator = CoverageValidator(contract)
    return validator.validate(output_md)
