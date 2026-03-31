"""Tests for V2 Parser (structured instruction parsing)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.contracts.v2_parser import V2Parser
from src.contracts.base import BenchmarkContract


MEDICAL_CHRONOLOGY_INSTRUCTION = r"""# Medical Chronology

## PRIORITY 0: SYSTEM OVERRIDE (CRITICAL RESTRICTIONS)
1. **NO HTML TAGS / NO CITATIONS**: You are STRICTLY FORBIDDEN from generating, copying, or appending `<!-- Source: ... -->` tags in ANY field.
2. **STRICT DATE FORMAT**: `encounter_date` MUST be strictly formatted as `YYYY-MM-DD` (e.g., "2023-05-12").
## Goal
Produce a strict chronological list of **clinical medical encounters** from the provided records.
## Schema Requirements
- **output_type**: list
- **sort_by**: encounter_date (ascending)
## CRITICAL: Schema Contract (MUST FOLLOW)

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| include | boolean | yes | Set true ONLY if valid clinical encounter. |
| exclude_reason | string | yes | If include=false, state why. |
| encounter_date | string | yes | MUST BE YYYY-MM-DD. |
| facility_name | string | yes | Facility name. |
| provider_name | string | yes | Clinician name with credentials. |
| visit_type | string | yes | Clinical type. |

### Template Example (MUST FOLLOW THIS PATTERN)
{% for date, group in safe_records | sort(attribute='encounter_date.value') | groupby('encounter_date.value') %}
## Date of Medical Visit: {{ date }}
### {{ date }}
* **Type of Visit:** {{ record.visit_type.value }}
* **Facility Name:** {{ record.facility_name.value }}
* **Provider Name:** {{ record.provider_name.value }}
* **Source References:** {{ combined_refs | source_comment(limit=5) }}
{% endfor %}
"""

VA_STYLE_INSTRUCTION = r"""# Veteran Information

## PRIORITY 0: SYSTEM OVERRIDE (CRITICAL RESTRICTIONS)
1. **MANDATORY SOURCE CITATIONS**: Append `<!-- Source: ... -->` tags at the end of each bullet point.
2. **SOURCE LIMIT RULE**: DO NOT include beyond 5 source references per bullet point.
3. **NO FILLER WORDS**: You are STRICTLY FORBIDDEN from writing "None", "N/A", "Unknown", or "Not specified".

## Goal
Extract veteran demographic and service information.

## Schema Requirements
- **output_type**: single

### Required Template Structure
## Veteran Information
### Military Service History
- **Branch:** [Value] <!-- Source: ... -->
- **Dates of Service:** [Value] <!-- Source: ... -->

### EMPTY STATE MESSAGE
No veteran information was found in the provided file. The file appears to contain only clinical treatment records.
"""

RED_FLAGS_INSTRUCTION = r"""# Red Flags

## PRIORITY 0: SYSTEM OVERRIDE (CRITICAL RESTRICTIONS)
1. **FULL SCOPE EXTRACTION (CRITICAL)**: Extract from ALL parts.
2. **NO INTRODUCTORY TEXT (CRITICAL)**: You MUST NOT write any general descriptions after Heading 1 or Heading 2.
3. **MANDATORY SOURCE CITATIONS**: Append `<!-- Source: ... -->` tags.
4. **EMPTY STATE PROTOCOL**: If no red flags exist, output ONLY the Empty State Message.

### ANTI-PATTERNS (DO NOT DO THESE)
- **BAD (Contains Intro Text)**: `## Contradictions` followed by `Here are the issues:`
- **BAD (Wrong Format)**: Using numbered lists instead of bullets

## Goal
Identify contradictions and red flags from earliest to latest date.

## Schema Requirements
- **output_type**: single
- **sort_by**: year (descending, numeric)
"""


class TestV2ParserSectionName:
    def test_extract_medical_chronology(self):
        contract = V2Parser().parse(MEDICAL_CHRONOLOGY_INSTRUCTION)
        assert contract.section_name == "Medical Chronology"

    def test_extract_veteran_information(self):
        contract = V2Parser().parse(VA_STYLE_INSTRUCTION)
        assert contract.section_name == "Veteran Information"

    def test_extract_red_flags(self):
        contract = V2Parser().parse(RED_FLAGS_INSTRUCTION)
        assert contract.section_name == "Red Flags"


class TestV2ParserForbiddenWords:
    def test_va_forbidden_words(self):
        contract = V2Parser().parse(VA_STYLE_INSTRUCTION)
        assert "None" in contract.forbidden_words
        assert "N/A" in contract.forbidden_words
        assert "Unknown" in contract.forbidden_words

    def test_no_forbidden_words_when_absent(self):
        contract = V2Parser().parse(MEDICAL_CHRONOLOGY_INSTRUCTION)
        assert contract.forbidden_words == []


class TestV2ParserSourceLimit:
    def test_source_comment_limit(self):
        contract = V2Parser().parse(MEDICAL_CHRONOLOGY_INSTRUCTION)
        assert contract.source_citation_limit == 5

    def test_do_not_include_beyond(self):
        contract = V2Parser().parse(VA_STYLE_INSTRUCTION)
        assert contract.source_citation_limit == 5


class TestV2ParserChronological:
    def test_ascending(self):
        contract = V2Parser().parse(MEDICAL_CHRONOLOGY_INSTRUCTION)
        assert contract.chronological_order is True
        assert contract.chronological_direction == "ascending"

    def test_descending(self):
        contract = V2Parser().parse(RED_FLAGS_INSTRUCTION)
        assert contract.chronological_order is True
        assert contract.chronological_direction == "descending"

    def test_no_chronological(self):
        instruction = "# Simple Section\n## Goal\nJust extract data.\n## Schema Requirements\n- **output_type**: single\n"
        contract = V2Parser().parse(instruction)
        assert contract.chronological_order is False


class TestV2ParserOutputType:
    def test_list_type(self):
        contract = V2Parser().parse(MEDICAL_CHRONOLOGY_INSTRUCTION)
        assert contract.output_type == "list"

    def test_single_type(self):
        contract = V2Parser().parse(VA_STYLE_INSTRUCTION)
        assert contract.output_type == "single"


class TestV2ParserSortBy:
    def test_sort_by_encounter_date(self):
        contract = V2Parser().parse(MEDICAL_CHRONOLOGY_INSTRUCTION)
        assert contract.sort_by == "encounter_date"

    def test_sort_by_year(self):
        contract = V2Parser().parse(RED_FLAGS_INSTRUCTION)
        assert contract.sort_by == "year"


class TestV2ParserRequiredFields:
    def test_schema_table_fields(self):
        contract = V2Parser().parse(MEDICAL_CHRONOLOGY_INSTRUCTION)
        assert "include" in contract.required_fields
        assert "encounter_date" in contract.required_fields
        assert "facility_name" in contract.required_fields
        assert "provider_name" in contract.required_fields
        assert "visit_type" in contract.required_fields


class TestV2ParserEmptyState:
    def test_empty_state_extracted(self):
        contract = V2Parser().parse(VA_STYLE_INSTRUCTION)
        assert contract.empty_state_message is not None
        assert "veteran information" in contract.empty_state_message.lower()

    def test_no_empty_state(self):
        contract = V2Parser().parse(MEDICAL_CHRONOLOGY_INSTRUCTION)
        assert contract.empty_state_message is None


class TestV2ParserDateFormat:
    def test_yyyy_mm_dd(self):
        contract = V2Parser().parse(MEDICAL_CHRONOLOGY_INSTRUCTION)
        assert contract.date_format == "YYYY-MM-DD"


class TestV2ParserAntiPatterns:
    def test_anti_patterns_extracted(self):
        contract = V2Parser().parse(RED_FLAGS_INSTRUCTION)
        assert len(contract.anti_patterns) >= 1

    def test_no_anti_patterns(self):
        contract = V2Parser().parse(MEDICAL_CHRONOLOGY_INSTRUCTION)
        assert contract.anti_patterns == []


class TestV2ParserCitationInfo:
    def test_citations_forbidden(self):
        contract = V2Parser().parse(MEDICAL_CHRONOLOGY_INSTRUCTION)
        assert contract.citation_style == "none"
        assert contract.citation_required is False

    def test_citations_consolidated(self):
        instruction = "# Test\n## Goal\nExtract.\n* **Source References:** refs\n"
        contract = V2Parser().parse(instruction)
        assert contract.citation_style == "consolidated"

    def test_citations_inline(self):
        contract = V2Parser().parse(VA_STYLE_INSTRUCTION)
        assert contract.citation_style == "inline"


class TestV2ParserOmitIfMissing:
    def test_field_deletion_rule(self):
        instruction = "# Test\nFIELD DELETION RULE: If missing, omit the heading.\n"
        contract = V2Parser().parse(instruction)
        assert contract.omit_if_missing is True


class TestV2ParserInstructionHash:
    def test_hash_generated(self):
        contract = V2Parser().parse(MEDICAL_CHRONOLOGY_INSTRUCTION)
        assert contract.instruction_hash != ""
        assert len(contract.instruction_hash) == 16

    def test_version_matches_hash(self):
        contract = V2Parser().parse(MEDICAL_CHRONOLOGY_INSTRUCTION)
        assert contract.instruction_version == contract.instruction_hash


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
