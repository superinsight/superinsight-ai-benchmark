"""
Markdown Entry Parser for structured medical chronology output.

Parses markdown output (## / ### / * **Field:** value) into a list of
structured dictionaries, enabling the same entry-level validators
(DateCoverage, ClinicalCoverage, ChronologicalOrder, etc.) that
previously only worked with JSON output.

Supports the standard Medical Chronology format:
    ## Date of Medical Visit: MM/DD/YYYY
    ### MM/DD/YYYY
    * **Field Name:** value

Also handles JSON output wrapped in markdown code fences as a fallback.
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple

# Mapping from markdown field labels to canonical JSON keys
FIELD_MAP = {
    "type of visit": "visit_type",
    "facility name": "facility_name",
    "provider name": "provider_name",
    "subjective/hpi/cc/hospital course": "subjective",
    "objective/pe": "objective",
    "social": "social",
    "labs": "lab_results",
    "surgery/procedure": "procedures",
    "imaging": "imaging_findings",
    "diagnoses": "diagnoses",
    "plan/assessment": "plan",
    "mss": "mss",
    "medication(s)": "medications",
    "medications": "medications",
    "referrals": "referrals",
    "source references": "source_references",
    "procedure": "procedures",
    "hospital course": "subjective",
}

# Date patterns for extracting encounter_date from ### headers
_DATE_MMDDYYYY = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")
_DATE_MMYYYY = re.compile(r"(\d{1,2})/(\d{4})")
_DATE_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


def _normalize_date_to_iso(date_str: str) -> Optional[str]:
    """Convert MM/DD/YYYY or MM/YYYY to YYYY-MM-DD."""
    m = _DATE_MMDDYYYY.search(date_str)
    if m:
        mm, dd, yyyy = m.group(1), m.group(2), m.group(3)
        return f"{yyyy}-{mm.zfill(2)}-{dd.zfill(2)}"

    m = _DATE_ISO.search(date_str)
    if m:
        return m.group(0)

    m = _DATE_MMYYYY.search(date_str)
    if m:
        mm, yyyy = m.group(1), m.group(2)
        return f"{yyyy}-{mm.zfill(2)}-01"

    return None


def _try_parse_json(text: str) -> Optional[List[Dict[str, Any]]]:
    """Try to parse text as JSON (possibly wrapped in code fences)."""
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[len("```json"):].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:].strip()
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, list) and all(isinstance(e, dict) for e in data):
            return data
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def parse_markdown_entries(output_md: str) -> List[Dict[str, Any]]:
    """
    Parse markdown medical chronology into structured entries.

    Returns a list of dicts with keys matching the JSON schema:
      - include: bool (always True for markdown entries)
      - encounter_date: str (YYYY-MM-DD)
      - date_display: str (original date string)
      - facility_name, provider_name, visit_type, ...
    """
    # Fast path: if the output is actually JSON, parse it directly
    json_entries = _try_parse_json(output_md)
    if json_entries is not None:
        return json_entries

    entries: List[Dict[str, Any]] = []
    current_entry: Optional[Dict[str, Any]] = None
    current_h2_date: Optional[str] = None

    for line in output_md.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        # ## Date of Medical Visit: MM/DD/YYYY
        if stripped.startswith("## ") and not stripped.startswith("### "):
            date_str = _normalize_date_to_iso(stripped)
            if date_str:
                current_h2_date = date_str
            continue

        # ### MM/DD/YYYY — new entry under current H2
        if stripped.startswith("### ") and not stripped.startswith("#### "):
            header_content = stripped[4:].strip()
            date_str = _normalize_date_to_iso(header_content)
            if date_str:
                if current_entry is not None:
                    entries.append(current_entry)
                current_entry = {
                    "include": True,
                    "exclude_reason": None,
                    "encounter_date": date_str,
                    "date_display": header_content.split("*")[0].strip(),
                }
            continue

        # * **Field Name:** value  (handles variable whitespace like "*   **Field:**")
        if current_entry is not None and re.match(r'^[*\-]\s+\*\*', stripped):
            m = re.match(r"[*\-]\s+\*\*([^*:]+?):\*\*\s*(.*)", stripped)
            if m:
                field_label = m.group(1).strip()
                value = m.group(2).strip()
                key = FIELD_MAP.get(field_label.lower(), _slugify(field_label))
                if value:
                    current_entry[key] = value

    # Don't forget the last entry
    if current_entry is not None:
        entries.append(current_entry)

    return entries


def _slugify(label: str) -> str:
    """Convert a field label to a snake_case key."""
    s = label.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def extract_dates_from_markdown_entries(entries: List[Dict[str, Any]]) -> set:
    """Extract encounter_date values from parsed entries (markdown or JSON)."""
    dates = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("include") is False:
            continue
        date_val = entry.get("encounter_date")
        if date_val and isinstance(date_val, str):
            normalized = _normalize_date_to_iso(date_val)
            if normalized:
                dates.add(normalized)
    return dates
