"""
V1 Parser for extracting validation rules from natural language instructions.

This parser uses a two-phase approach:
1. Regex extraction (fast, free) - extracts obvious patterns
2. LLM extraction (comprehensive) - extracts complex rules

Supports any instruction type (Medical Chronology, Review of Records, etc.)
"""

import re
import json
from typing import List, Dict, Optional, Tuple, Any
from .base import BenchmarkContract
from .llm_backend import LLMBackend, get_backend


# LLM prompt for rule extraction
RULE_EXTRACTION_PROMPT = """Analyze this instruction and extract validation rules as JSON.

## Instruction
{instruction}

## Extract these rules:
1. section_name: The main section name (e.g., "Medical Chronology", "HISTORY OF ILLNESS", "Review of Records")
2. output_style: "narrative" (prose paragraphs, no bullets) | "structured" (headings + bullets) | "table"
3. required_fields: List of field names that must appear in the output (e.g., ["Facility Name", "Provider Name", "Diagnoses"])
4. date_format: Expected date format. Options: "MM/DD/YYYY", "MM/DD/YY", "Month Day, Year", "YYYY-MM-DD"
5. heading_pattern: Expected heading format for entries (e.g., "## MM/DD/YYYY", "### Field Name", "**<u>DATE. Title</u>**")
6. heading_level: Number 1-4 for H1-H4, or 0 if no headings expected
7. and_rules: Pairs of fields that must appear together. Format: [["field1", "field2"], ...]. Example: if instruction says "only include if both Facility and Provider are present", return [["Facility Name", "Provider Name"]]
8. omit_if_missing: true if instruction says to omit fields/sections when value is not available
9. citation_style: "inline" (after each claim) | "consolidated" (in a specific field) | "per_event" (at end of each event) | "none" (no citations required)
10. citation_field: Field name where citations should be consolidated (e.g., "Source References"). Only set if citation_style is "consolidated"
11. grouping_rule: How to group entries. Options: "same_date_same_provider_combine", "same_date_combine", "chronological", null
12. verbatim_required: true if instruction requires exact quotes from source
13. bullets_allowed: true if bullet points are allowed in output
14. expected_sections: List of section names if the output should have multiple sections (e.g., ["ATTESTATION", "DIAGNOSTIC RECORDS"])
15. entry_format: Description of how each entry should be formatted

## Output Format
Return ONLY valid JSON, no markdown code blocks, no explanation:
{{
  "section_name": "...",
  "output_style": "...",
  "required_fields": [...],
  "date_format": "...",
  "heading_pattern": "...",
  "heading_level": 2,
  "and_rules": [],
  "omit_if_missing": false,
  "citation_style": "...",
  "citation_field": null,
  "grouping_rule": null,
  "verbatim_required": false,
  "bullets_allowed": true,
  "expected_sections": [],
  "entry_format": "..."
}}"""


class V1Parser:
    """
    Extract contract from natural language instruction.
    
    Uses a two-phase approach:
    1. Regex extraction for obvious patterns
    2. LLM extraction for complex semantic rules
    
    This parser is generic and works with any instruction type.
    """
    
    def __init__(
        self, 
        backend: Optional[LLMBackend] = None,
        use_llm: bool = True,
    ):
        """
        Initialize V1 Parser.
        
        Args:
            backend: LLM backend for complex rule extraction
            use_llm: If False, only use regex extraction (faster but less accurate)
        """
        self.backend = backend
        self.use_llm = use_llm
        self.instruction = ""
        
    def parse(self, instruction: str) -> BenchmarkContract:
        """
        Parse instruction text into a BenchmarkContract.
        
        Args:
            instruction: The natural language instruction text
            
        Returns:
            BenchmarkContract with extracted validation rules
        """
        self.instruction = instruction
        
        # Phase 1: Regex extraction (fast, free)
        regex_rules = self._regex_extract(instruction)
        
        # Phase 2: LLM extraction (comprehensive)
        llm_rules = {}
        if self.use_llm:
            try:
                llm_rules = self._llm_extract(instruction)
            except Exception as e:
                print(f"Warning: LLM extraction failed: {e}")
                print("Falling back to regex-only extraction")
        
        # Phase 3: Merge rules (LLM takes precedence for complex rules)
        merged = self._merge_rules(regex_rules, llm_rules)
        
        # Build contract
        return BenchmarkContract(
            section_name=merged.get("section_name", "Unknown Section"),
            heading_patterns=self._build_heading_patterns(merged),
            required_fields=merged.get("required_fields", []),
            forbidden_fields=merged.get("forbidden_fields", []),
            expected_sections=merged.get("expected_sections", []),
            section_order_strict=bool(merged.get("expected_sections")),
            and_rules=[tuple(r) for r in merged.get("and_rules", []) if len(r) == 2],
            omit_if_missing=merged.get("omit_if_missing", False),
            citation_required=merged.get("citation_style") not in ["none", None],
            citation_style=merged.get("citation_style", "inline"),
            citation_field=merged.get("citation_field"),
            citation_pattern=r'<!--\s*Source:.*?-->',
            high_risk_fields=self._get_high_risk_fields(merged),
            verbatim_required=merged.get("verbatim_required", False),
            date_format=merged.get("date_format"),
            grouping_rule=merged.get("grouping_rule"),
            entry_header_pattern=merged.get("entry_header_pattern"),
            raw_instruction=instruction,
        )
    
    def _regex_extract(self, instruction: str) -> Dict[str, Any]:
        """
        Extract rules using regex patterns (fast, free).
        
        This catches obvious patterns that don't need LLM interpretation.
        """
        rules: Dict[str, Any] = {}
        
        # Extract section name
        rules["section_name"] = self._extract_section_name(instruction)
        
        # Extract fields from **Field:** or [Field] patterns
        rules["required_fields"] = self._extract_fields(instruction)
        
        # Detect date format
        rules["date_format"] = self._detect_date_format(instruction)
        
        # Detect heading level
        rules["heading_level"] = self._detect_heading_level(instruction)
        
        # Detect citation style
        citation_style, citation_field = self._detect_citation_style(instruction)
        rules["citation_style"] = citation_style
        rules["citation_field"] = citation_field
        
        # Detect output style
        rules["output_style"] = self._detect_output_style(instruction)
        rules["bullets_allowed"] = self._detect_bullets_allowed(instruction)
        
        # Detect verbatim requirement
        rules["verbatim_required"] = self._detect_verbatim(instruction)
        
        # Detect entry header pattern
        rules["entry_header_pattern"] = self._detect_entry_header_pattern(instruction)
        
        # Detect omit if missing
        rules["omit_if_missing"] = self._detect_omit_if_missing(instruction)
        
        return rules
    
    def _llm_extract(self, instruction: str) -> Dict[str, Any]:
        """
        Extract rules using LLM (comprehensive).
        
        This catches complex semantic rules that regex can't handle.
        """
        if self.backend is None:
            self.backend = get_backend()
        
        prompt = RULE_EXTRACTION_PROMPT.format(instruction=instruction)
        
        response = self.backend.generate(prompt)
        
        # Parse JSON from response
        # Try to extract JSON from markdown code block first
        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        # Try parsing entire response as JSON
        # Remove any leading/trailing whitespace and newlines
        response = response.strip()
        
        # Find JSON object boundaries
        start = response.find('{')
        end = response.rfind('}') + 1
        
        if start != -1 and end > start:
            json_str = response[start:end]
            return json.loads(json_str)
        
        raise ValueError(f"Could not parse JSON from LLM response: {response[:200]}...")
    
    def _merge_rules(self, regex_rules: Dict, llm_rules: Dict) -> Dict:
        """
        Merge regex and LLM rules.
        
        Strategy:
        - LLM wins for complex rules (and_rules, grouping_rule, expected_sections)
        - Regex wins if LLM returns empty/null for simple rules
        - Combine required_fields from both sources
        """
        merged = {**regex_rules}
        
        # Fields to merge (combine lists)
        list_fields = ["required_fields", "expected_sections", "high_risk_fields"]
        
        # Fields where LLM takes precedence
        llm_priority_fields = [
            "and_rules", "grouping_rule", "output_style", 
            "entry_format", "section_name"
        ]
        
        for key, value in llm_rules.items():
            if value is None or value == "" or value == []:
                continue
            
            if key in list_fields:
                # Merge lists
                existing = merged.get(key, []) or []
                merged[key] = list(set(existing + value))
            elif key in llm_priority_fields:
                # LLM takes precedence
                merged[key] = value
            elif key not in merged or merged[key] is None:
                # Fill in missing values
                merged[key] = value
        
        return merged
    
    def _extract_section_name(self, instruction: str) -> str:
        """Extract the main section name from instruction."""
        patterns = [
            r"[Cc]reate a (?:section|report).*?call(?:ed)?\s+[\"']?([A-Z][A-Za-z\s]+)[\"']?",
            r"[Ss]ection.*?(?:call(?:ed)?|named?)\s+[\"']?([A-Z][A-Za-z\s]+)[\"']?",
            r"^#\s+([A-Z][A-Za-z\s]+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, instruction, re.MULTILINE)
            if match:
                name = match.group(1).strip()
                if name and 3 < len(name) < 50:
                    return name
        
        # Check for common section keywords
        keywords = [
            "Medical Chronology", "Review of Records", "HISTORY OF ILLNESS",
            "Claim Information", "Red Flags", "Imaging Reports"
        ]
        for keyword in keywords:
            if keyword.lower() in instruction.lower():
                return keyword
        
        return "Unknown Section"
    
    def _extract_fields(self, instruction: str) -> List[str]:
        """Extract field names from instruction text."""
        fields = set()
        
        # Keywords that are instruction terms, NOT data fields
        # These should be excluded from required_fields
        instruction_keywords = {
            # Rule/instruction terms
            "critical", "critical exclusion", "critical filter",
            "strict filtering", "strict inclusion", "strict exclusion",
            "scope filtering", "the \"and\" rule", "and rule",
            "formatting", "format", "sorting", "order", "grouping",
            "deduplication", "extraction", "role", "task", "objective",
            "medical only", "exclude", "include", "omit",
            "global rule", "global exclusion", "global",
            "output format", "response format", "entry format",
            "quantity rule", "selection logic", "content rules",
            "strict selection criteria", "strict source check",
            "examples", "example output", "example",
            "anti-hallucination", "visual cue", "visual logic",
            "happening now logic", "review of records trap",
            "date format", "heading level", "section header", "entry header",
            "source references", "verbatim", "verbatim count",
        }
        
        def is_valid_field(field: str) -> bool:
            """Check if a string is a valid data field name."""
            if not field or len(field) > 50:
                return False
            field_lower = field.lower().strip()
            # Check against instruction keywords
            if field_lower in instruction_keywords:
                return False
            # Check for common instruction patterns
            if any(kw in field_lower for kw in ["must ", "should ", "do not", "if ", "when ", "only "]):
                return False
            # Check for parenthetical explanations (likely instructions)
            if '(' in field and len(field) > 30:
                return False
            return True
        
        # Pattern 1: **Field Name:** - common in structured instructions
        for match in re.finditer(r'\*\*([^*]+):\*\*', instruction):
            field = match.group(1).strip()
            if is_valid_field(field):
                fields.add(field)
        
        # Pattern 2: [Field Name] - bracketed field names
        for match in re.finditer(r'\[([^\]]+)\]', instruction):
            field = match.group(1).strip()
            if is_valid_field(field) and not field.startswith('http'):
                fields.add(field)
        
        # Pattern 3: "Include: Field1, Field2, Field3" or "Include the following fields"
        include_match = re.search(
            r'[Ii]nclude(?:\s+the\s+following)?[:\s]+([^\.]+?)(?:\.|$)', 
            instruction
        )
        if include_match:
            field_text = include_match.group(1)
            # Split by comma, "and", or newline
            for field in re.split(r',|\band\b|\n', field_text):
                field = re.sub(r'\*\*|__|\[|\]', '', field).strip()
                if is_valid_field(field) and len(field) > 2:
                    fields.add(field)
        
        return list(fields)
    
    def _detect_date_format(self, instruction: str) -> Optional[str]:
        """Detect expected date format from instruction."""
        # Explicit format mentions
        if re.search(r'MM/DD/YYYY', instruction, re.IGNORECASE):
            return "MM/DD/YYYY"
        if re.search(r'MM/DD/YY(?![Y])', instruction, re.IGNORECASE):
            return "MM/DD/YY"
        if re.search(r'Month Day,?\s*Year', instruction, re.IGNORECASE):
            return "Month Day, Year"
        if re.search(r'YYYY-MM-DD', instruction, re.IGNORECASE):
            return "YYYY-MM-DD"
        
        # Check example dates
        if re.search(r'\b\d{2}/\d{2}/\d{4}\b', instruction):
            return "MM/DD/YYYY"
        if re.search(r'\b\d{2}/\d{2}/\d{2}\b', instruction):
            return "MM/DD/YY"
        if re.search(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b', instruction):
            return "Month Day, Year"
        
        return None
    
    def _detect_heading_level(self, instruction: str) -> int:
        """Detect expected heading level."""
        match = re.search(r'[Uu]se\s+(#{1,4})\s+for', instruction)
        if match:
            return len(match.group(1))
        
        match = re.search(r'[Hh]eading\s+(?:level\s+)?(\d)', instruction)
        if match:
            return int(match.group(1))
        
        return 2  # Default to H2
    
    def _detect_citation_style(self, instruction: str) -> Tuple[str, Optional[str]]:
        """Detect citation style and field."""
        instruction_lower = instruction.lower()
        
        # Check for consolidated citations
        if "source references" in instruction_lower:
            return "consolidated", "Source References"
        if "_source_references" in instruction_lower:
            return "consolidated", "_source_references"
        
        # Check for per-event citations
        if "at the end of each" in instruction_lower:
            return "per_event", None
        
        # Check for no citations
        if "without references" in instruction_lower or "no citations" in instruction_lower:
            return "none", None
        
        # Default to inline
        if "source" in instruction_lower or "citation" in instruction_lower:
            return "inline", None
        
        return "inline", None
    
    def _detect_output_style(self, instruction: str) -> str:
        """Detect output style (narrative, structured, table)."""
        instruction_lower = instruction.lower()
        
        if "table" in instruction_lower and "format" in instruction_lower:
            return "table"
        if "bullet" not in instruction_lower and "narrative" in instruction_lower:
            return "narrative"
        if "do not use bullet" in instruction_lower:
            return "narrative"
        if "prose" in instruction_lower or "paragraph" in instruction_lower:
            return "narrative"
        
        return "structured"
    
    def _detect_bullets_allowed(self, instruction: str) -> bool:
        """Detect if bullets are allowed."""
        if re.search(r'do\s+not\s+use\s+bullet', instruction, re.IGNORECASE):
            return False
        if re.search(r'no\s+bullet', instruction, re.IGNORECASE):
            return False
        return True
    
    def _detect_verbatim(self, instruction: str) -> bool:
        """Detect if verbatim extraction is required."""
        patterns = [
            r'verbatim',
            r'exactly\s+as\s+written',
            r'do\s+not\s+paraphrase',
            r'do\s+not\s+summarize',
            r'word\s+for\s+word',
        ]
        for pattern in patterns:
            if re.search(pattern, instruction, re.IGNORECASE):
                return True
        return False
    
    def _detect_entry_header_pattern(self, instruction: str) -> Optional[str]:
        """Detect entry header format pattern."""
        if "<u>" in instruction and "</u>" in instruction:
            return r'\*\*<u>.+?</u>\*\*'
        return None
    
    def _detect_omit_if_missing(self, instruction: str) -> bool:
        """Detect if missing values should be omitted."""
        patterns = [
            r'omit.*?(?:if|when).*?(?:not available|missing|N/A)',
            r'if.*?not\s+(?:available|specified|applicable).*?omit',
            r'should\s+be\s+omitted',
        ]
        for pattern in patterns:
            if re.search(pattern, instruction, re.IGNORECASE):
                return True
        return False
    
    def _build_heading_patterns(self, rules: Dict) -> List[str]:
        """Build heading regex patterns from rules."""
        patterns = []
        
        heading_pattern = rules.get("heading_pattern")
        if heading_pattern:
            # Convert description to regex if needed
            if "MM/DD/YYYY" in heading_pattern:
                patterns.append(r'^##\s+\d{2}/\d{2}/\d{4}')
            elif "MM/DD/YY" in heading_pattern:
                patterns.append(r'^##\s+\d{2}/\d{2}/\d{2}')
            else:
                patterns.append(heading_pattern)
        
        heading_level = rules.get("heading_level", 2)
        if heading_level and not patterns:
            hashes = '#' * heading_level
            patterns.append(rf'^{hashes}\s+.+$')
        
        return patterns
    
    def _get_high_risk_fields(self, rules: Dict) -> List[str]:
        """Get fields that require citation support."""
        # These fields typically need source verification
        default_high_risk = [
            "Diagnoses", "Diagnosis", "Impression",
            "Treatment Plan", "Plan", "Procedure",
            "Work Status", "Apportionment", "Impairment Rating",
        ]
        
        # Filter to only include fields that are in required_fields
        required = set(rules.get("required_fields", []))
        if not required:
            return default_high_risk
        
        return [f for f in default_high_risk if f in required or any(f.lower() in r.lower() for r in required)]


def parse_instruction(instruction: str, use_llm: bool = True) -> BenchmarkContract:
    """
    Convenience function to parse instruction into contract.
    
    Args:
        instruction: Natural language instruction text
        use_llm: If True, use LLM for complex rule extraction
        
    Returns:
        BenchmarkContract with extracted rules
    """
    parser = V1Parser(use_llm=use_llm)
    return parser.parse(instruction)
