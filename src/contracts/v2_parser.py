"""
V2 Parser for extracting validation rules from structured instructions.

Unlike V1Parser (regex + LLM), V2Parser is purely deterministic and designed
for instructions that follow the structured format with PRIORITY 0, Schema
Requirements, Output Generation Rules, EMPTY STATE MESSAGE, etc.

Zero LLM cost, millisecond-level parsing.
"""

import re
import hashlib
from typing import List, Optional, Tuple, Dict, Any
from .base import BenchmarkContract


class V2Parser:
    """
    Extract BenchmarkContract from structured instructions.

    Handles instructions with known structural patterns:
    - ## PRIORITY 0: SYSTEM OVERRIDE
    - ## Schema Requirements
    - ## Output Generation Rules
    - ### EMPTY STATE MESSAGE / EMPTY STATE PROTOCOL
    - ### ANTI-PATTERNS
    - Schema Contract tables (| Field | Type | Required | Rules |)
    """

    def parse(self, instruction: str) -> BenchmarkContract:
        """Parse structured instruction into a BenchmarkContract."""
        section_name = self._extract_section_name(instruction)
        forbidden_words = self._extract_forbidden_words(instruction)
        source_limit = self._extract_source_limit(instruction)
        heading_hierarchy = self._extract_heading_hierarchy(instruction)
        chrono_order, chrono_dir = self._extract_chronological(instruction)
        empty_state = self._extract_empty_state(instruction)
        output_type = self._extract_output_type(instruction)
        sort_by = self._extract_sort_by(instruction)
        required_fields = self._extract_required_fields(instruction)
        date_format = self._extract_date_format(instruction)
        anti_patterns = self._extract_anti_patterns(instruction)
        scope_filters = self._extract_scope_filters(instruction)
        citation_style, citation_field = self._extract_citation_info(instruction)

        inst_hash = hashlib.sha256(instruction.encode("utf-8")).hexdigest()[:16]

        return BenchmarkContract(
            section_name=section_name,
            required_fields=required_fields,
            date_format=date_format,
            forbidden_words=forbidden_words,
            source_citation_limit=source_limit,
            heading_hierarchy=heading_hierarchy,
            chronological_order=chrono_order,
            chronological_direction=chrono_dir,
            empty_state_message=empty_state,
            output_type=output_type,
            sort_by=sort_by,
            anti_patterns=anti_patterns,
            scope_filters=scope_filters,
            citation_required=citation_style != "none",
            citation_style=citation_style,
            citation_field=citation_field,
            omit_if_missing=self._detect_omit_if_missing(instruction),
            raw_instruction=instruction,
            instruction_hash=inst_hash,
            instruction_version=inst_hash,
        )

    # ── Section Name ──────────────────────────────────────────────

    def _extract_section_name(self, text: str) -> str:
        match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if match:
            name = match.group(1).strip()
            if 2 < len(name) < 60:
                return name
        return "Unknown Section"

    # ── Forbidden Words ───────────────────────────────────────────

    def _extract_forbidden_words(self, text: str) -> List[str]:
        """
        Patterns:
          - 'STRICTLY FORBIDDEN from writing "None", "N/A", "Unknown"'
          - 'DO NOT write "Unknown" or "None"'
          - 'Do NOT use: Unknown, Not specified'
          - 'Value is "None", "Unknown", "N/A"' (from kill lists)
        """
        words = set()

        patterns = [
            r'FORBIDDEN\s+from\s+writing\s+(.+?)(?:\.|$)',
            r'(?:DO\s+NOT|NEVER)\s+(?:write|output|use)[:\s]+(.+?)(?:\.|$)',
            r'(?:DO\s+NOT|NEVER)\s+(?:write|output)\s+"([^"]+)"',
        ]
        for pat in patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                fragment = m.group(1)
                for w in re.findall(r'"([^"]+)"', fragment):
                    cleaned = w.strip()
                    if cleaned and len(cleaned) < 30:
                        words.add(cleaned)

        common_forbidden = ["None", "N/A", "Unknown", "Not specified", "Not available"]
        for w in common_forbidden:
            pattern = re.compile(
                r'(?:forbidden|prohibited|do\s+not|never).*?' + re.escape(w),
                re.IGNORECASE | re.DOTALL,
            )
            if pattern.search(text[:3000]):
                words.add(w)

        return sorted(words)

    # ── Source Citation Limit ─────────────────────────────────────

    def _extract_source_limit(self, text: str) -> Optional[int]:
        """
        Patterns:
          - 'do not include beyond 5 source reference'
          - 'source_comment(limit=5)'
          - 'maximum 3 source citations'
          - 'AT MOST ONE citation'
        """
        patterns = [
            r'source_comment\(limit=(\d+)\)',
            r'(?:do\s+not\s+include\s+beyond|not\s+.*?beyond)\s+(\d+)\s+source',
            r'(?:maximum|max|up\s+to|limit\s+to)\s+(\d+)\s+source',
            r'AT\s+MOST\s+(\w+)\s+citation',
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                val = m.group(1)
                if val.upper() == "ONE":
                    return 1
                try:
                    return int(val)
                except ValueError:
                    continue
        return None

    # ── Heading Hierarchy ─────────────────────────────────────────

    def _extract_heading_hierarchy(self, text: str) -> List[str]:
        hierarchy = []
        template_section = self._get_section(text, "Required Template Structure")
        if not template_section:
            template_section = self._get_section(text, "Template Example")
        if not template_section:
            return hierarchy

        for line in template_section.split("\n"):
            stripped = line.strip()
            if re.match(r"^#{1,4}\s+", stripped):
                hierarchy.append(stripped)
            elif stripped.startswith("* **") or stripped.startswith("- **"):
                hierarchy.append(stripped)

        return hierarchy[:20]

    # ── Chronological Order ───────────────────────────────────────

    def _extract_chronological(self, text: str) -> Tuple[bool, str]:
        if re.search(r"sort_by.*?\(.*?descending", text, re.IGNORECASE):
            return True, "descending"
        if re.search(r"sort_by.*?ascending|sort_by.*?encounter_date", text, re.IGNORECASE):
            return True, "ascending"
        if re.search(r"most\s+recent\s+first|latest\s+to\s+earliest|newest\s+first", text, re.IGNORECASE):
            return True, "descending"
        if re.search(r"earliest\s+to\s+(?:the\s+)?latest|chronological|oldest\s+first", text, re.IGNORECASE):
            return True, "ascending"
        return False, "ascending"

    # ── Empty State Message ───────────────────────────────────────

    def _extract_empty_state(self, text: str) -> Optional[str]:
        patterns = [
            r"###?\s*\[?EMPTY\s+STATE\s+(?:MESSAGE|PROTOCOL|FALLBACK)\]?\s*\n+(.*?)(?:\n\n|\n#|\Z)",
            r"Statement\s+of\s+Negative\s+Findings[:\s]*\n+(.*?)(?:\n\n|\n#|\Z)",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
            if m:
                msg = m.group(1).strip()
                msg = re.sub(r"^[>*\-]\s*", "", msg).strip()
                if msg and len(msg) > 10:
                    return msg
        return None

    # ── Output Type ───────────────────────────────────────────────

    def _extract_output_type(self, text: str) -> str:
        m = re.search(r"\*\*output_type\*\*\s*:\s*(\w+)", text, re.IGNORECASE)
        if m:
            return m.group(1).lower()
        if re.search(r"output_type.*?list", text, re.IGNORECASE):
            return "list"
        return "single"

    # ── Sort By ───────────────────────────────────────────────────

    def _extract_sort_by(self, text: str) -> Optional[str]:
        m = re.search(r"\*\*sort_by\*\*\s*:\s*(\w+)", text, re.IGNORECASE)
        if m:
            return m.group(1)
        m = re.search(r"sort_by[:\s]+(\w+)", text, re.IGNORECASE)
        if m:
            return m.group(1)
        return None

    # ── Required Fields ───────────────────────────────────────────

    def _extract_required_fields(self, text: str) -> List[str]:
        fields = []

        for m in re.finditer(
            r"^\|\s*(\w[\w\s_]*?)\s*\|\s*(\w+)\s*\|\s*(yes|no)\s*\|",
            text,
            re.MULTILINE | re.IGNORECASE,
        ):
            field_name = m.group(1).strip()
            required = m.group(3).strip().lower()
            if required == "yes" and field_name.lower() not in ("field", "---"):
                fields.append(field_name)

        if not fields:
            for m in re.finditer(r"\*\s+\*\*([^*:]+?):\*\*", text):
                field = m.group(1).strip()
                if field and len(field) < 50:
                    fields.append(field)

        return fields

    # ── Date Format ───────────────────────────────────────────────

    def _extract_date_format(self, text: str) -> Optional[str]:
        if re.search(r"YYYY-MM-DD", text):
            return "YYYY-MM-DD"
        if re.search(r"MM/DD/YYYY", text):
            return "MM/DD/YYYY"
        if re.search(r"MM/DD/YY(?!Y)", text):
            return "MM/DD/YY"
        return None

    # ── Anti-Patterns ─────────────────────────────────────────────

    def _extract_anti_patterns(self, text: str) -> List[str]:
        section = self._get_section(text, "ANTI-PATTERNS")
        if not section:
            return []

        patterns = []
        for m in re.finditer(r"\*\*BAD\s*(?:\([^)]*\))?\s*\*\*\s*:\s*(.+)", section):
            patterns.append(m.group(1).strip())
        return patterns

    # ── Scope Filters ─────────────────────────────────────────────

    def _extract_scope_filters(self, text: str) -> List[str]:
        filters = []
        scope_patterns = [
            (r"ONLY\s+(?:from|extract\s+from)\s+(Section\s+\w+)", "ONLY from {}"),
            (r"ABSOLUTE\s+.*?BAN.*?(Section\s+\w+)", "EXCLUDE {}"),
            (r"STRICTLY\s+EXCLUDE.*?(Section\s+\w+)", "EXCLUDE {}"),
        ]
        for pat, fmt in scope_patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                filters.append(fmt.format(m.group(1)))
        return filters

    # ── Citation Info ─────────────────────────────────────────────

    def _extract_citation_info(self, text: str) -> Tuple[str, Optional[str]]:
        if re.search(r"FORBIDDEN.*?Source.*?tags|FORBIDDEN.*?generating.*?Source", text, re.IGNORECASE):
            return "none", None
        if re.search(r"Source\s+References", text):
            return "consolidated", "Source References"
        if re.search(r"<!--\s*Source:", text):
            return "inline", None
        return "inline", None

    # ── Omit If Missing ───────────────────────────────────────────

    def _detect_omit_if_missing(self, text: str) -> bool:
        patterns = [
            r"omit.*?(?:if|when).*?(?:not available|missing|N/A)",
            r"if.*?missing.*?(?:omit|delete|remove)",
            r"completely\s+omit\s+both",
            r"FIELD\s+DELETION\s+RULE",
        ]
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE):
                return True
        return False

    # ── Helpers ────────────────────────────────────────────────────

    def _get_section(self, text: str, heading_keyword: str) -> Optional[str]:
        pattern = re.compile(
            rf"^###?\s+.*?{re.escape(heading_keyword)}.*$",
            re.MULTILINE | re.IGNORECASE,
        )
        m = pattern.search(text)
        if not m:
            return None

        start = m.end()
        next_heading = re.search(r"^#{1,3}\s+", text[start:], re.MULTILINE)
        end = start + next_heading.start() if next_heading else len(text)
        return text[start:end]
