"""Tests for V2 Validators (ForbiddenWords, SourceLimit, Chronological)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.contracts.base import BenchmarkContract
from src.validators.forbidden_words import ForbiddenWordsValidator
from src.validators.source_limit import SourceLimitValidator
from src.validators.chronological import ChronologicalValidator


def make_contract(**kwargs) -> BenchmarkContract:
    """Helper to create a BenchmarkContract with overrides."""
    defaults = dict(section_name="Test")
    defaults.update(kwargs)
    return BenchmarkContract(**defaults)


# ── ForbiddenWordsValidator ──────────────────────────────────────

class TestForbiddenWordsValidator:
    def test_no_forbidden_words_configured(self):
        contract = make_contract(forbidden_words=[])
        score, errors = ForbiddenWordsValidator(contract).validate("Some text with None in it")
        assert score == 1.0
        assert errors == []

    def test_clean_output(self):
        contract = make_contract(forbidden_words=["None", "N/A", "Unknown"])
        output = "### Claimant Name\n* John Doe\n### Date of Birth\n* 01/15/1980\n"
        score, errors = ForbiddenWordsValidator(contract).validate(output)
        assert score == 1.0
        assert errors == []

    def test_single_violation(self):
        contract = make_contract(forbidden_words=["None", "N/A"])
        output = "### Claimant Name\n* None\n### Date of Birth\n* 01/15/1980\n"
        score, errors = ForbiddenWordsValidator(contract).validate(output)
        assert score < 1.0
        assert len(errors) == 1
        assert errors[0].code == "FORBIDDEN_WORD"

    def test_multiple_violations(self):
        contract = make_contract(forbidden_words=["None", "N/A", "Unknown"])
        output = "### Field1\n* None\n### Field2\n* N/A\n### Field3\n* Unknown\n"
        score, errors = ForbiddenWordsValidator(contract).validate(output)
        assert score < 1.0
        assert len(errors) == 3

    def test_forbidden_word_in_citation_ignored(self):
        contract = make_contract(forbidden_words=["None"])
        output = "### Field\n* Value <!-- Source: None.pdf, Page 1 -->\n"
        score, errors = ForbiddenWordsValidator(contract).validate(output)
        assert score == 1.0
        assert errors == []

    def test_forbidden_word_partial_match_ignored(self):
        contract = make_contract(forbidden_words=["None"])
        output = "### Field\n* Nonetheless, the patient improved.\n"
        score, errors = ForbiddenWordsValidator(contract).validate(output)
        assert score == 1.0
        assert errors == []


# ── SourceLimitValidator ─────────────────────────────────────────

class TestSourceLimitValidator:
    def test_no_limit_configured(self):
        contract = make_contract(source_citation_limit=None)
        output = "Text <!-- Source: a --> <!-- Source: b --> <!-- Source: c -->"
        score, errors = SourceLimitValidator(contract).validate(output)
        assert score == 1.0
        assert errors == []

    def test_within_limit(self):
        contract = make_contract(source_citation_limit=3)
        output = "### Entry\n* Value <!-- Source: a.pdf, Page 1 --> <!-- Source: b.pdf, Page 2 -->\n"
        score, errors = SourceLimitValidator(contract).validate(output)
        assert score == 1.0
        assert errors == []

    def test_exceeds_limit(self):
        contract = make_contract(source_citation_limit=2)
        citations = " ".join(f"<!-- Source: file{i}.pdf, Page {i} -->" for i in range(5))
        output = f"### Entry\n* Value {citations}\n"
        score, errors = SourceLimitValidator(contract).validate(output)
        assert score < 1.0
        assert len(errors) == 1
        assert errors[0].code == "SOURCE_LIMIT_EXCEEDED"

    def test_limit_of_one(self):
        contract = make_contract(source_citation_limit=1)
        output = "### Entry\n* Value <!-- Source: a.pdf --> <!-- Source: b.pdf -->\n"
        score, errors = SourceLimitValidator(contract).validate(output)
        assert score < 1.0

    def test_multiple_sections_mixed(self):
        contract = make_contract(source_citation_limit=2)
        output = (
            "### Entry1\n* Value <!-- Source: a --> <!-- Source: b -->\n"
            "### Entry2\n* Value <!-- Source: c --> <!-- Source: d --> <!-- Source: e -->\n"
        )
        score, errors = SourceLimitValidator(contract).validate(output)
        assert 0.0 < score < 1.0
        assert len(errors) == 1

    def test_no_citations_at_all(self):
        contract = make_contract(source_citation_limit=5)
        output = "### Entry\n* Just plain text\n"
        score, errors = SourceLimitValidator(contract).validate(output)
        assert score == 1.0


# ── ChronologicalValidator ───────────────────────────────────────

class TestChronologicalValidator:
    def test_no_chronological_requirement(self):
        contract = make_contract(chronological_order=False)
        output = "## 2024-01-01\n## 2020-01-01\n"
        score, errors = ChronologicalValidator(contract).validate(output)
        assert score == 1.0
        assert errors == []

    def test_ascending_correct(self):
        contract = make_contract(chronological_order=True, chronological_direction="ascending")
        output = (
            "## Date of Medical Visit: 01/15/2020\n"
            "### 01/15/2020\n"
            "* **Type:** Office Visit\n\n"
            "## Date of Medical Visit: 03/20/2020\n"
            "### 03/20/2020\n"
            "* **Type:** Follow-up\n\n"
            "## Date of Medical Visit: 06/10/2021\n"
            "### 06/10/2021\n"
            "* **Type:** Surgery\n"
        )
        score, errors = ChronologicalValidator(contract).validate(output)
        assert score == 1.0
        assert errors == []

    def test_ascending_violation(self):
        contract = make_contract(chronological_order=True, chronological_direction="ascending")
        output = (
            "## Date of Medical Visit: 06/10/2021\n"
            "### 06/10/2021\n\n"
            "## Date of Medical Visit: 01/15/2020\n"
            "### 01/15/2020\n"
        )
        score, errors = ChronologicalValidator(contract).validate(output)
        assert score < 1.0
        assert len(errors) >= 1
        assert errors[0].code == "OUT_OF_ORDER"

    def test_descending_correct(self):
        contract = make_contract(chronological_order=True, chronological_direction="descending")
        output = (
            "## 2023\n* Some finding\n\n"
            "## 2022\n* Another finding\n\n"
            "## 2021\n* Earlier finding\n"
        )
        score, errors = ChronologicalValidator(contract).validate(output)
        assert score == 1.0

    def test_descending_violation(self):
        contract = make_contract(chronological_order=True, chronological_direction="descending")
        output = (
            "## 2021\n* Earlier\n\n"
            "## 2023\n* Later\n"
        )
        score, errors = ChronologicalValidator(contract).validate(output)
        assert score < 1.0

    def test_iso_dates_ascending(self):
        contract = make_contract(chronological_order=True, chronological_direction="ascending")
        output = (
            "## Date of Medical Visit: 2020-01-15\n"
            "### 2020-01-15\n\n"
            "## Date of Medical Visit: 2020-03-20\n"
            "### 2020-03-20\n\n"
            "## Date of Medical Visit: 2021-06-10\n"
            "### 2021-06-10\n"
        )
        score, errors = ChronologicalValidator(contract).validate(output)
        assert score == 1.0

    def test_single_date_always_passes(self):
        contract = make_contract(chronological_order=True, chronological_direction="ascending")
        output = "## Date of Medical Visit: 01/15/2020\n### 01/15/2020\n"
        score, errors = ChronologicalValidator(contract).validate(output)
        assert score == 1.0
        assert errors == []

    def test_equal_dates_pass(self):
        contract = make_contract(chronological_order=True, chronological_direction="ascending")
        output = (
            "## Date of Medical Visit: 01/15/2020\n"
            "### 01/15/2020\n\n"
            "## Date of Medical Visit: 01/15/2020\n"
            "### 01/15/2020\n"
        )
        score, errors = ChronologicalValidator(contract).validate(output)
        assert score == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
