"""
Citation Validator for checking source references.

This validator checks:
- Citations are present after entries
- Citation format is correct
- Citation coverage (entries have citations)
"""

import re
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from ..contracts.base import BenchmarkContract, ValidationError


@dataclass
class Citation:
    """Represents a source citation."""
    file: str
    page: str
    file_id: str = ""
    paragraph_ref: str = ""
    bookmark: str = ""
    raw_text: str = ""


class CitationValidator:
    """
    Validate citation rules in the output markdown.
    
    Checks:
    - Citations exist after entries
    - Citation format is correct (<!-- Source: ... -->)
    - Citation fields are present (file, page)
    - Citation coverage ratio
    """
    
    def __init__(self, contract: BenchmarkContract):
        self.contract = contract
        self.errors: List[ValidationError] = []
    
    def validate(self, output_md: str) -> Tuple[float, List[ValidationError], Dict]:
        """
        Validate citations in output markdown.
        
        Args:
            output_md: The output markdown to validate
            
        Returns:
            Tuple of (score, errors, stats)
        """
        self.errors = []
        
        # Extract citations
        citations = self._extract_citations(output_md)
        
        # Extract entries
        entries = self._extract_entries(output_md)
        
        # Check citation format
        self._check_citation_format(citations)
        
        # Check citation coverage
        coverage_stats = self._check_citation_coverage(output_md, entries, citations)
        
        # Calculate score
        if not entries:
            score = 1.0
        else:
            entries_with_citations = coverage_stats['entries_with_citations']
            total_entries = coverage_stats['total_entries']
            score = entries_with_citations / total_entries if total_entries > 0 else 1.0
        
        # Penalize for format errors
        if self.errors:
            score = score * (1 - len(self.errors) * 0.05)
            score = max(0.0, score)
        
        stats = {
            'total_citations': len(citations),
            'total_entries': len(entries),
            **coverage_stats,
        }
        
        return score, self.errors, stats
    
    def _extract_citations(self, output_md: str) -> List[Citation]:
        """Extract all citations from output."""
        citations = []
        
        # Pattern for source citations (support multiple formats)
        # Matches: <!-- Source: ... -->, <!-- TRACE_ID_xxx -->, <!-- any_id -->
        pattern = r'<!--\s*(Source:\s*.+?|TRACE_ID_[a-f0-9]+|[a-f0-9]{20,})\s*-->'
        matches = re.finditer(pattern, output_md, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            citation_text = match.group(1)
            citation = self._parse_citation(citation_text, match.group(0))
            if citation:
                citations.append(citation)
        
        return citations
    
    def _parse_citation(self, citation_text: str, raw_text: str) -> Optional[Citation]:
        """Parse a citation string into Citation object."""
        # Check for TRACE_ID format first
        trace_match = re.search(r'TRACE_ID_([a-f0-9]+)', citation_text, re.IGNORECASE)
        if trace_match:
            trace_id = trace_match.group(1)
            return Citation(
                file='',
                page='',
                file_id='',
                paragraph_ref=trace_id,
                bookmark='',
                raw_text=raw_text,
            )
        
        # Parse key: value pairs for Source format
        fields = {}
        patterns = {
            'file': r'file:\s*([^,\n]+)',
            'page': r'page:\s*([^,\n]+)',
            'file_id': r'file_id:\s*([^,\n]+)',
            'paragraph_ref': r'paragraph_ref:\s*([^,\n]+)',
            'bookmark': r'bookmark:\s*([^,\n]+)',
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, citation_text, re.IGNORECASE)
            if match:
                fields[field] = match.group(1).strip()
        
        # Accept citation if it has file+page OR file_id OR paragraph_ref
        if not fields.get('file') and not fields.get('file_id') and not fields.get('paragraph_ref'):
            # Check for generic hex ID (at least 20 chars)
            hex_match = re.search(r'([a-f0-9]{20,})', citation_text, re.IGNORECASE)
            if hex_match:
                return Citation(
                    file='',
                    page='',
                    file_id='',
                    paragraph_ref=hex_match.group(1),
                    bookmark='',
                    raw_text=raw_text,
                )
            return None
        
        return Citation(
            file=fields.get('file', ''),
            page=fields.get('page', ''),
            file_id=fields.get('file_id', ''),
            paragraph_ref=fields.get('paragraph_ref', ''),
            bookmark=fields.get('bookmark', ''),
            raw_text=raw_text,
        )
    
    def _extract_entries(self, output_md: str) -> List[Tuple[int, str]]:
        """Extract entry headers with their positions (supports both formats)."""
        entries = []
        
        # Format 1: **<u>...</u>** (Review of Records style)
        pattern1 = r'\*\*<u>[^<]+</u>\*\*'
        for match in re.finditer(pattern1, output_md):
            entries.append((match.start(), match.group(0)))
        
        # Format 2: ### MM/DD/YYYY (Medical Chronology style)
        # Only match ### headers that start with a date pattern
        # This avoids misidentifying sub-headings like "### Notes" or "### Summary"
        pattern2 = r'^###\s+(\d{1,2}/\d{1,2}/\d{2,4}[^\n]*)'
        for match in re.finditer(pattern2, output_md, re.MULTILINE):
            entries.append((match.start(), match.group(0)))
        
        # Sort by position
        entries.sort(key=lambda x: x[0])
        
        return entries
    
    def _check_citation_format(self, citations: List[Citation]) -> None:
        """Check that citations have correct format."""
        for citation in citations:
            # TRACE_ID or paragraph_ref citations don't need file/page
            has_ref_id = citation.paragraph_ref or citation.file_id
            
            # Check required fields (only if not a reference-based citation)
            if not has_ref_id:
                if not citation.file:
                    self.errors.append(ValidationError(
                        code="CITATION_MISSING_FILE",
                        message="Citation missing 'file' field",
                        actual=citation.raw_text[:100],
                    ))
                
                if not citation.page:
                    self.errors.append(ValidationError(
                        code="CITATION_MISSING_PAGE",
                        message="Citation missing 'page' field",
                        actual=citation.raw_text[:100],
                    ))
    
    def _check_citation_coverage(
        self, 
        output_md: str,
        entries: List[Tuple[int, str]], 
        citations: List[Citation]
    ) -> Dict:
        """Check that entries have citations."""
        if not entries:
            return {
                'entries_with_citations': 0,
                'entries_without_citations': 0,
                'total_entries': 0,
                'coverage_rate': 1.0,
            }
        
        # Find citation positions (support any HTML comment format)
        # Matches: <!-- TRACE_ID_xxx -->, <!-- Source: ... -->, or any <!-- ... -->
        citation_pattern = r'<!--\s*(?:TRACE_ID_[a-f0-9]+|Source:|[a-f0-9]{20,})'
        citation_positions = [m.start() for m in re.finditer(citation_pattern, output_md, re.IGNORECASE)]
        
        # For each entry, check if there's a citation before the next entry
        entries_with_citations = 0
        
        for i, (pos, _header) in enumerate(entries):
            # Find the end of this entry (start of next entry or end of text)
            if i + 1 < len(entries):
                entry_end = entries[i + 1][0]
            else:
                entry_end = len(output_md)
            
            # Check if there's a citation between this entry and the next
            has_citation = any(pos < cp < entry_end for cp in citation_positions)
            if has_citation:
                entries_with_citations += 1
        
        total_entries = len(entries)
        entries_without = total_entries - entries_with_citations
        coverage_rate = entries_with_citations / total_entries if total_entries > 0 else 1.0
        
        return {
            'entries_with_citations': entries_with_citations,
            'entries_without_citations': entries_without,
            'total_entries': total_entries,
            'coverage_rate': coverage_rate,
        }


def validate_citations(output_md: str, contract: BenchmarkContract) -> Tuple[float, List[ValidationError], Dict]:
    """
    Convenience function to validate citations.
    
    Args:
        output_md: Output markdown to validate
        contract: Benchmark contract with rules
        
    Returns:
        Tuple of (score, errors, stats)
    """
    validator = CitationValidator(contract)
    return validator.validate(output_md)


def extract_source_citations(text: str) -> List[Citation]:
    """
    Extract all source citations from text.
    
    Compatible with research v1's citation_validation module.
    
    Args:
        text: Text containing source citations
        
    Returns:
        List of Citation objects
    """
    validator = CitationValidator(BenchmarkContract(section_name=""))
    return validator._extract_citations(text)


def count_citations(text: str) -> int:
    """Count the number of citations in text."""
    # Support multiple citation formats: <!-- Source: ... -->, <!-- TRACE_ID_xxx -->, etc.
    pattern = r'<!--\s*(?:Source:|TRACE_ID_[a-f0-9]+|[a-f0-9]{20,}).*?-->'
    return len(re.findall(pattern, text, re.DOTALL | re.IGNORECASE))
