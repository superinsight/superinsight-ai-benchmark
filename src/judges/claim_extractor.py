"""
Claim Extractor for extracting verifiable claims from output.

This module extracts claims from the output markdown that need to be
verified against source text. Supports dynamic formats based on instruction.

Key Features:
- Generic mode: Extracts ALL **Field:** Value patterns (adapts to any format)
- Contract mode: Uses BenchmarkContract.required_fields for targeted extraction
- Supports multiple entry header formats (### dates, **<u> headers, etc.)
- Supports bullet point and non-bullet formats
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..contracts.base import BenchmarkContract


@dataclass
class Citation:
    """Source citation associated with a claim."""
    file: str
    page: str
    file_id: str = ""
    paragraph_ref: str = ""
    raw_text: str = ""

    @property
    def source_excerpt(self) -> str:
        """Alias for raw_text for compatibility."""
        return self.raw_text


@dataclass
class Claim:
    """A verifiable claim extracted from output."""
    text: str
    field_type: str  # e.g., "Diagnoses", "Provider Name", "Facility Name"
    section: str  # e.g., "MEDICAL CHRONOLOGY", "DIAGNOSTIC RECORDS"
    citations: List[Citation] = field(default_factory=list)
    entry_header: str = ""
    line_number: int = 0
    source_excerpt: str = ""  # Source text for verification
    
    def has_citation(self) -> bool:
        """Check if claim has at least one citation."""
        return len(self.citations) > 0
    
    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "field_type": self.field_type,
            "section": self.section,
            "has_citation": self.has_citation(),
            "citation_count": len(self.citations),
            "entry_header": self.entry_header[:100] if self.entry_header else "",
        }


# Default high-risk fields (fallback when no contract provided)
DEFAULT_HIGH_RISK_FIELDS = [
    # Medical findings
    "Impression",
    "Diagnosis",
    "Diagnoses",
    "Assessment",
    "Pre-operative Diagnosis",
    "Post-operative Diagnosis",
    "Procedure",
    "Surgery/Procedure",
    # Treatment info
    "Treatment Plan",
    "Plan/Assessment",
    "Medications",
    "Medication(s)",
    # Clinical details
    "Subjective/HPI/CC/Hospital Course",
    "Objective/PE",
    "Labs",
    "Imaging",
    "MSS",
    # Work/disability
    "Work Status",
    "Work Restrictions",
    "Apportionment",
    "Impairment Rating",
    "Causation",
    "Medical Causation",
    # Visit info (for chronology)
    "Provider Name",
    "Facility Name",
    "Referrals",
    "Social",
]


class ClaimExtractor:
    """
    Extract verifiable claims from output markdown.
    
    Supports two modes:
    1. Generic mode (default): Extracts ALL **Field:** Value patterns
    2. Contract mode: Uses BenchmarkContract.required_fields for targeted extraction

    Automatically detects and handles different output formats:
    - Medical Chronology: ### MM/DD/YYYY headers, * **Field:** Value bullets
    - Review of Records: **<u>Date. Info.</u>** headers, **Field:** Value fields
    """
    
    def __init__(
        self,
        high_risk_fields: Optional[List[str]] = None,
        contract: Optional["BenchmarkContract"] = None,
        generic_mode: bool = True,  # Default to generic mode
    ):
        """
        Initialize claim extractor.
        
        Args:
            high_risk_fields: List of field names to extract claims from.
            contract: BenchmarkContract to get field names from (overrides high_risk_fields).
            generic_mode: If True, extract ALL fields regardless of high_risk_fields list.
        """
        self.generic_mode = generic_mode

        # Priority: contract > high_risk_fields > DEFAULT_HIGH_RISK_FIELDS
        if contract and hasattr(contract, 'required_fields') and contract.required_fields:
            # required_fields is List[str], use directly
            self.high_risk_fields = list(contract.required_fields)
            self.generic_mode = False  # Use specific fields from contract
        else:
            self.high_risk_fields = high_risk_fields or DEFAULT_HIGH_RISK_FIELDS
    
    def extract(self, output_md: str) -> List[Claim]:
        """
        Extract all claims from output.
        
        Args:
            output_md: Output markdown text
            
        Returns:
            List of Claim objects
        """
        claims = []
        
        # Split into sections
        sections = self._split_sections(output_md)
        
        for section_name, section_content in sections.items():
            section_claims = self._extract_section_claims(section_name, section_content)
            claims.extend(section_claims)
        
        return claims
    
    def _split_sections(self, output_md: str) -> Dict[str, str]:
        """Split output into sections by ## headers."""
        sections = {}
        current_section = "UNKNOWN"
        current_content = []
        
        for line in output_md.split('\n'):
            stripped = line.strip()
            # Match ## headers (but not ### which are entry headers)
            if stripped.startswith('## ') and not stripped.startswith('### '):
                # Save previous section
                if current_content:
                    sections[current_section] = '\n'.join(current_content)
                # Start new section
                current_section = stripped[3:].strip().rstrip(':').upper()
                current_content = []
            else:
                current_content.append(line)
        
        # Save last section
        if current_content:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def _extract_section_claims(self, section_name: str, content: str) -> List[Claim]:
        """Extract claims from a single section."""
        claims = []
        
        # Split into entries (medical visits, records, etc.)
        entries = self._split_entries(content)
        
        for entry_header, entry_content, entry_citations in entries:
            entry_claims = self._extract_entry_claims(
                section_name, entry_header, entry_content, entry_citations
            )
            claims.extend(entry_claims)
        
        return claims
    
    def _split_entries(self, content: str) -> List[Tuple[str, str, List[Citation]]]:
        """
        Split section content into entries with their citations.

        Supports multiple entry header formats:
        - ### MM/DD/YYYY (Medical Chronology)
        - **<u>Date. Info.</u>** (Review of Records)
        """
        entries = []
        
        lines = content.split('\n')
        current_header = ""
        current_content = []
        current_citations = []
        
        for line in lines:
            stripped = line.strip()
            
            # Check for entry headers (multiple formats)
            is_entry_header = (
                stripped.startswith('### ') or  # Medical Chronology format
                stripped.startswith('**<u>') or  # Review of Records format
                re.match(r'^#{3,}\s+\d{1,2}/\d{1,2}', stripped)  # Date headers
            )

            if is_entry_header:
                # Save previous entry
                if current_header or current_content:
                    entries.append((current_header, '\n'.join(current_content), current_citations))
                # Start new entry
                current_header = stripped
                current_content = []
                current_citations = []
            elif self._is_citation_line(stripped):
                # Line contains citation(s) - extract all of them
                citations = self._extract_all_citations(stripped)
                if citations:
                    current_citations.extend(citations)
                # If line has other content besides citations, keep it
                clean_line = re.sub(r'<!--.*?-->', '', stripped).strip()
                if clean_line:
                    current_content.append(line)
            else:
                current_content.append(line)
        
        # Save last entry
        if current_header or current_content:
            entries.append((current_header, '\n'.join(current_content), current_citations))
        
        return entries
    
    def _is_citation_line(self, line: str) -> bool:
        """Check if a line contains HTML comment citations."""
        return '<!--' in line and '-->' in line
    
    def _extract_all_citations(self, line: str) -> List[Citation]:
        """Extract all citations from a line (may have multiple <!-- --> comments)."""
        citations = []
        # Find all HTML comments in the line
        for match in re.finditer(r'<!--.*?-->', line):
            citation = self._parse_citation(match.group(0))
            if citation:
                citations.append(citation)
        return citations

    def _parse_citation(self, citation_text: str) -> Optional[Citation]:
        """
        Parse citation from HTML comment.
        
        Supports multiple formats:
        - TRACE_ID format: <!-- TRACE_ID_abc123 -->
        - Source format: <!-- Source: file: xxx, page: xxx -->
        - Generic ID format: <!-- any_identifier_string -->
        """
        # Try TRACE_ID format first: <!-- TRACE_ID_xxx -->
        trace_match = re.search(r'TRACE_ID_([a-f0-9]+)', citation_text, re.IGNORECASE)
        if trace_match:
            trace_id = trace_match.group(1)
            return Citation(
                file='',
                page='',
                file_id='',
                paragraph_ref=trace_id,
                raw_text=citation_text,
            )
        
        # Try structured Source format
        patterns = {
            'file': r'file:\s*([^,\n>]+)',
            'page': r'page:\s*([^,\n>]+)',
            'file_id': r'file_id:\s*([^,\n>]+)',
            'paragraph_ref': r'paragraph_ref:\s*([^,\n>]+)',
        }
        
        fields = {}
        for field_name, pattern in patterns.items():
            match = re.search(pattern, citation_text, re.IGNORECASE)
            if match:
                fields[field_name] = match.group(1).strip()
        
        # If we got structured fields, use them
        if fields.get('file') or fields.get('file_id') or fields.get('paragraph_ref'):
            return Citation(
                file=fields.get('file', ''),
                page=fields.get('page', ''),
                file_id=fields.get('file_id', ''),
                paragraph_ref=fields.get('paragraph_ref', ''),
                raw_text=citation_text,
            )
        
        # Fallback: treat any HTML comment content as a generic ID
        # Extract content between <!-- and -->
        generic_match = re.search(r'<!--\s*(.+?)\s*-->', citation_text)
        if generic_match:
            content = generic_match.group(1).strip()
            # Skip if it's just whitespace or looks like a section marker
            if content and not content.lower().startswith('section'):
                return Citation(
                    file='',
                    page='',
                    file_id=content,
                    paragraph_ref=content,
                    raw_text=citation_text,
                )

        return None
    
    def _extract_entry_claims(
        self,
        section: str,
        header: str,
        content: str,
        citations: List[Citation]
    ) -> List[Claim]:
        """
        Extract claims from a single entry.

        Supports two modes:
        - Generic mode: Extract ALL **Field:** patterns
        - Specific mode: Only extract fields in high_risk_fields list
        
        Uses line-level citation tracking for precise claim-to-citation mapping.
        """
        claims = []

        # Build line-to-citation map for precise mapping
        line_citations = self._build_line_citation_map(content, citations)
        
        # Combine header and content for searching
        full_text = header + "\n" + content
        
        if self.generic_mode:
            # Generic mode: Extract ALL **Field:** Value patterns
            claims.extend(self._extract_generic_claims(section, header, full_text, line_citations, citations))
        else:
            # Specific mode: Only extract high-risk fields
            claims.extend(self._extract_specific_claims(section, header, full_text, line_citations, citations))

        return claims
    
    def _build_line_citation_map(
        self, 
        content: str, 
        entry_citations: List[Citation]
    ) -> Dict[int, List[Citation]]:
        """
        Build a map of line numbers to their associated citations.
        
        Strategy:
        1. Lines with inline citations get those specific citations
        2. Lines following a standalone citation line inherit that citation
        3. Lines before any citation use entry_citations as fallback
        
        Args:
            content: Entry content text
            entry_citations: Entry-level citations as fallback
            
        Returns:
            Dict mapping line number (0-indexed in content) to list of citations
        """
        line_citations: Dict[int, List[Citation]] = {}
        lines = content.split('\n')
        
        # Track the "active" citation(s) that apply to subsequent lines
        active_citations: List[Citation] = entry_citations.copy() if entry_citations else []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Check for citation(s) in this line
            if self._is_citation_line(stripped):
                inline_citations = self._extract_all_citations(stripped)
                if inline_citations:
                    # This line has citations
                    line_citations[i] = inline_citations
                    # Update active citation for following lines
                    active_citations = inline_citations
                else:
                    # Failed to parse, use active
                    line_citations[i] = active_citations.copy()
                
                # Check if line has content besides citations
                clean_line = re.sub(r'<!--.*?-->', '', stripped).strip()
                if not clean_line:
                    # Pure citation line - don't store line mapping, just update active
                    continue
            else:
                # Regular line - use active citations
                line_citations[i] = active_citations.copy()
        
        return line_citations
    
    def _get_citation_for_position(
        self,
        match_start: int,
        full_text: str,
        line_citations: Dict[int, List[Citation]],
        entry_citations: List[Citation]
    ) -> List[Citation]:
        """
        Get citations for a claim based on its position in text.
        
        Args:
            match_start: Character position where match starts
            full_text: Full text being searched
            line_citations: Map of line numbers to citations (0-indexed from content)
            entry_citations: Fallback citations
            
        Returns:
            List of citations for this claim
        """
        # Find line number for this position in full_text
        # Note: full_text = header + "\n" + content, so header is line 0
        text_before = full_text[:match_start + 1]  # +1 to include the matched newline
        full_text_line_num = text_before.count('\n')
        
        # Convert to content line number (content starts after header line)
        # full_text line 0 = header
        # full_text line 1 = content line 0
        # full_text line 2 = content line 1
        content_line_num = full_text_line_num - 1
        
        # Get citations for this line
        if content_line_num >= 0 and content_line_num in line_citations:
            return line_citations[content_line_num]
        
        # Fallback to entry citations
        return entry_citations.copy() if entry_citations else []

    def _extract_generic_claims(
        self,
        section: str,
        header: str,
        full_text: str,
        line_citations: Dict[int, List[Citation]],
        entry_citations: List[Citation]
    ) -> List[Claim]:
        """
        Extract ALL field-value patterns from text (generic mode).
        
        Supports multiple markdown formats for robustness:
        - **Field:** Value (standard bold)
        - *Field:* Value (italic/single asterisk)
        - __Field:__ Value (underline)
        - - **Field:** Value (bullet + bold)
        - FieldName: Value (no formatting, capitalized)
        """
        claims = []

        # Multiple patterns for different markdown styles (robustness)
        patterns = [
            # Pattern 1 (primary): **Field:** Value - standard bold with colon inside
            r'(?:^|\n)\s*(?:[\*\-]\s*)?\*\*([^*:]+):\*\*\s*(.+?)(?=(?:\n\s*(?:[\*\-]\s*)?\*\*[^*]+:\*\*)|<!--|$)',
            
            # Pattern 2: **Field**: Value - colon after bold (common variant)
            r'(?:^|\n)\s*(?:[\*\-]\s*)?\*\*([^*:]+)\*\*:\s*(.+?)(?=(?:\n\s*(?:[\*\-]\s*)?\*\*[^*]+)|<!--|$)',
            
            # Pattern 3: *Field:* Value - single asterisk (italic)
            r'(?:^|\n)\s*(?:[\*\-]\s*)?\*([^*:]+):\*\s+(.+?)(?=(?:\n\s*(?:[\*\-]\s*)?\*[^*]+:\*)|<!--|$)',
            
            # Pattern 4: __Field:__ Value - underline style
            r'(?:^|\n)\s*(?:[\*\-]\s*)?__([^_:]+):__\s*(.+?)(?=(?:\n\s*(?:[\*\-]\s*)?__[^_]+:__)|<!--|$)',
            
            # Pattern 5: Capitalized Field: Value - no formatting (fallback)
            # Only match if it looks like a field name (starts with capital, reasonable length)
            r'(?:^|\n)\s*(?:[\*\-]\s*)?([A-Z][A-Za-z\s/]{2,30}):\s+(.+?)(?=\n\s*(?:[\*\-]\s*)?[A-Z][A-Za-z\s/]{2,30}:|<!--|$)',
        ]
        
        # Fields to skip (metadata, not claims)
        skip_fields = {
            'source references', 'source', 'references', 'ref', 'refs',
            'citation', 'citations', 'note', 'notes'
        }
        
        # Track matched positions to avoid duplicates
        matched_positions = set()

        for pattern in patterns:
            matches = re.finditer(pattern, full_text, re.DOTALL)
            
            for match in matches:
                # Skip if we already matched this position with a higher-priority pattern
                pos_key = (match.start(), match.end())
                if pos_key in matched_positions:
                    continue
                    
                # Check for overlapping match (within 5 chars of existing match start)
                if any(abs(match.start() - pos[0]) < 5 for pos in matched_positions):
                    continue
                
                field_name = match.group(1).strip()
                claim_text = match.group(2).strip()

                # Clean up claim text
                claim_text = self._clean_claim_text(claim_text)

                # Skip empty or very short claims
                if claim_text and len(claim_text) > 3:
                    # Skip metadata fields
                    if field_name.lower() in skip_fields:
                        continue

                    # Get citations for this specific claim position
                    claim_citations = self._get_citation_for_position(
                        match.start(), full_text, line_citations, entry_citations
                    )

                    claims.append(Claim(
                        text=claim_text,
                        field_type=field_name,
                        section=section,
                        citations=claim_citations,
                        entry_header=header,
                    ))
                    
                    matched_positions.add(pos_key)

        return claims

    def _extract_specific_claims(
        self,
        section: str,
        header: str,
        full_text: str,
        line_citations: Dict[int, List[Citation]],
        entry_citations: List[Citation]
    ) -> List[Claim]:
        """
        Extract only fields in high_risk_fields list (specific mode).
        
        Supports multiple markdown formats for robustness.
        """
        claims = []

        for field_name in self.high_risk_fields:
            escaped_field = re.escape(field_name)
            
            # Multiple patterns for different markdown styles
            patterns = [
                # **Field:** Value (colon inside)
                rf'(?:[\*\-]\s*)?\*\*{escaped_field}:\*\*\s*(.+?)(?=(?:[\*\-]\s*)?\*\*[^*]+:\*\*|<!--|$|\n\s*(?:[\*\-]\s*)?\*\*)',
                # **Field**: Value (colon outside)
                rf'(?:[\*\-]\s*)?\*\*{escaped_field}\*\*:\s*(.+?)(?=(?:[\*\-]\s*)?\*\*[^*]+|<!--|$|\n\s*(?:[\*\-]\s*)?\*\*)',
                # *Field:* Value (single asterisk)
                rf'(?:[\*\-]\s*)?\*{escaped_field}:\*\s+(.+?)(?=(?:[\*\-]\s*)?\*[^*]+:\*|<!--|$)',
                # __Field:__ Value (underline)
                rf'(?:[\*\-]\s*)?__{escaped_field}:__\s*(.+?)(?=(?:[\*\-]\s*)?__[^_]+:__|<!--|$)',
                # Field: Value (no formatting)
                rf'(?:^|\n)\s*(?:[\*\-]\s*)?{escaped_field}:\s+(.+?)(?=\n\s*(?:[\*\-]\s*)?[A-Z]|<!--|$)',
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, full_text, re.DOTALL | re.IGNORECASE)

                for match in matches:
                    claim_text = match.group(1).strip()
                    claim_text = self._clean_claim_text(claim_text)

                    if claim_text and len(claim_text) > 3:
                        # Get citations for this specific claim position
                        claim_citations = self._get_citation_for_position(
                            match.start(), full_text, line_citations, entry_citations
                        )
                        
                        claims.append(Claim(
                            text=claim_text,
                            field_type=field_name,
                            section=section,
                            citations=claim_citations,
                        entry_header=header,
                    ))
        
        return claims
    
    def _clean_claim_text(self, text: str) -> str:
        """Clean up claim text by removing extra whitespace and citations."""
        # Remove inline citations
        text = re.sub(r'<!--.*?-->', '', text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        # Strip
        text = text.strip()
        # Remove trailing punctuation that might be incomplete
        text = text.rstrip(',;')
        return text

    def get_claims_without_citations(self, claims: List[Claim]) -> List[Claim]:
        """Get claims that don't have citations."""
        return [c for c in claims if not c.has_citation()]
    
    def get_claims_by_section(self, claims: List[Claim], section: str) -> List[Claim]:
        """Get claims for a specific section."""
        return [c for c in claims if c.section.upper() == section.upper()]
    
    def get_claims_by_field(self, claims: List[Claim], field_type: str) -> List[Claim]:
        """Get claims for a specific field type."""
        return [c for c in claims if c.field_type.lower() == field_type.lower()]

    def get_high_risk_claims(self, claims: List[Claim]) -> List[Claim]:
        """Get claims from high-risk fields only."""
        high_risk_lower = [f.lower() for f in self.high_risk_fields]
        return [c for c in claims if c.field_type.lower() in high_risk_lower]
