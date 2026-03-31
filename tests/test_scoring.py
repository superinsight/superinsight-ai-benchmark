"""Tests for Scoring Calculator."""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.contracts.base import BenchmarkContract, SectionResult


class TestSectionResult:
    """Tests for SectionResult data class."""
    
    def test_section_result_creation(self):
        """Test creating a SectionResult."""
        result = SectionResult(
            section_name="Test Section",
            formatting_score=0.9,
            completeness_score=0.8,
            hallucination_score=0.95,
        )
        
        assert result.section_name == "Test Section"
        assert result.formatting_score == 0.9
        assert result.completeness_score == 0.8
        assert result.hallucination_score == 0.95
    
    def test_section_result_total_score(self):
        """Test total score calculation."""
        result = SectionResult(
            section_name="Test",
            formatting_score=0.9,
            completeness_score=0.8,
            hallucination_score=1.0,
            total_score=None,  # Should be calculated
        )
        
        # Calculate expected: 0.33 * 0.9 + 0.33 * 0.8 + 0.34 * 1.0
        expected = 0.33 * 0.9 + 0.33 * 0.8 + 0.34 * 1.0
        
        # Result can calculate its own total
        calculated = result.formatting_score * 0.33 + result.completeness_score * 0.33 + result.hallucination_score * 0.34
        
        assert abs(calculated - expected) < 0.001
    
    def test_section_result_to_dict(self):
        """Test converting SectionResult to dictionary."""
        result = SectionResult(
            section_name="Test",
            formatting_score=0.9,
            completeness_score=0.8,
            hallucination_score=1.0,
            total_score=0.896,
            formatting_errors=[],
            coverage_violations=[],
            unsupported_claims=[],
        )
        
        d = result.to_dict()
        
        assert d['section_name'] == "Test"
        assert d['scores']['formatting'] == 0.9
        assert d['scores']['completeness'] == 0.8
        assert d['scores']['traceability'] == 1.0
        assert 'errors' in d


class TestWeightedScoring:
    """Tests for weighted score calculation."""
    
    def test_weights_sum_to_one(self):
        """Test that weights sum to 1.0."""
        formatting_weight = 0.33
        completeness_weight = 0.33
        hallucination_weight = 0.34
        
        total = formatting_weight + completeness_weight + hallucination_weight
        assert abs(total - 1.0) < 0.001
    
    def test_perfect_scores(self):
        """Test that perfect scores yield 1.0 total."""
        formatting_score = 1.0
        completeness_score = 1.0
        hallucination_score = 1.0
        
        total = (
            formatting_score * 0.33 +
            completeness_score * 0.33 +
            hallucination_score * 0.34
        )
        
        assert abs(total - 1.0) < 0.001
    
    def test_zero_scores(self):
        """Test that zero scores yield 0.0 total."""
        formatting_score = 0.0
        completeness_score = 0.0
        hallucination_score = 0.0
        
        total = (
            formatting_score * 0.33 +
            completeness_score * 0.33 +
            hallucination_score * 0.34
        )
        
        assert total == 0.0
    
    def test_mixed_scores(self):
        """Test mixed scores calculation."""
        formatting_score = 0.8  # 0.8 * 0.33 = 0.264
        completeness_score = 0.7  # 0.7 * 0.33 = 0.231
        hallucination_score = 1.0  # 1.0 * 0.34 = 0.34
        
        expected = 0.264 + 0.231 + 0.34  # = 0.835
        
        total = (
            formatting_score * 0.33 +
            completeness_score * 0.33 +
            hallucination_score * 0.34
        )
        
        assert abs(total - expected) < 0.001


class TestBenchmarkContract:
    """Tests for BenchmarkContract."""
    
    def test_contract_creation_minimal(self):
        """Test creating a contract with minimal fields."""
        contract = BenchmarkContract(section_name="Test")
        
        assert contract.section_name == "Test"
        assert contract.required_fields == []
        assert contract.date_format is None
    
    def test_contract_creation_full(self):
        """Test creating a contract with all fields."""
        contract = BenchmarkContract(
            section_name="Medical Chronology",
            required_fields=["Facility Name", "Provider Name"],
            date_format="MM/DD/YYYY",
            citation_required=True,
            citation_style="consolidated",
            citation_field="Source References",
            entry_header_pattern=r'## \d{2}/\d{2}/\d{4}',
            and_rules=[("Facility Name", "Provider Name")],
        )
        
        assert contract.section_name == "Medical Chronology"
        assert len(contract.required_fields) == 2
        assert contract.date_format == "MM/DD/YYYY"
        assert contract.citation_required is True
        assert contract.citation_style == "consolidated"
        assert len(contract.and_rules) == 1
    
    def test_contract_to_dict(self):
        """Test converting contract to dictionary."""
        contract = BenchmarkContract(
            section_name="Test",
            required_fields=["Field1", "Field2"],
        )
        
        d = contract.to_dict()
        
        assert d['section_name'] == "Test"
        assert "Field1" in d['required_fields']
    
    def test_contract_from_dict(self):
        """Test creating contract from dictionary."""
        data = {
            'section_name': 'Test Section',
            'required_fields': ['A', 'B', 'C'],
            'date_format': 'MM/DD/YYYY',
        }
        
        contract = BenchmarkContract.from_dict(data)
        
        assert contract.section_name == 'Test Section'
        assert contract.required_fields == ['A', 'B', 'C']
        assert contract.date_format == 'MM/DD/YYYY'


class TestScoringCalculatorIntegration:
    """Integration tests for scoring calculator."""
    
    def test_calculate_with_fixture(self):
        """Test calculating score with fixture files."""
        # Skip this test if boto3 is not importable (sandbox mode)
        pytest.importorskip("boto3")
        
        # Load fixtures
        output_path = Path(__file__).parent / "fixtures" / "sample_output.md"
        source_path = Path(__file__).parent / "fixtures" / "sample_source.txt"
        
        output = output_path.read_text()
        source = source_path.read_text()
        
        contract = BenchmarkContract(
            section_name="Medical Chronology",
            date_format="MM/DD/YYYY",
            required_fields=["Facility Name", "Provider Name", "Diagnoses", "Plan"],
            citation_required=True,
            citation_style="consolidated",
            citation_field="Source References",
        )
        
        # Import scoring calculator
        from src.scoring.calculator import ScoringCalculator
        
        calculator = ScoringCalculator(contract)
        
        # Calculate without LLM judges
        result = calculator.calculate(output, source, skip_llm_judge=True)
        
        # Verify result structure
        assert result.section_name == "Medical Chronology"
        assert 0.0 <= result.formatting_score <= 1.0
        assert 0.0 <= result.completeness_score <= 1.0
        assert 0.0 <= result.total_score <= 1.0


class TestErrorTracking:
    """Tests for error tracking in scoring."""
    
    def test_formatting_errors_tracked(self):
        """Test that formatting errors are tracked."""
        result = SectionResult(
            section_name="Test",
            formatting_score=0.7,
            completeness_score=1.0,
            hallucination_score=1.0,
            formatting_errors=[
                {"code": "DATE_FORMAT", "message": "Wrong date format", "line": 5},
            ],
        )
        
        assert len(result.formatting_errors) == 1
        assert result.formatting_errors[0]['code'] == "DATE_FORMAT"
    
    def test_coverage_violations_tracked(self):
        """Test that coverage violations are tracked."""
        result = SectionResult(
            section_name="Test",
            formatting_score=1.0,
            completeness_score=0.8,
            hallucination_score=1.0,
            coverage_violations=[
                {"entry": "Visit 2", "missing_field": "Provider Name"},
            ],
        )
        
        assert len(result.coverage_violations) == 1
        assert result.coverage_violations[0]['missing_field'] == "Provider Name"
    
    def test_unsupported_claims_tracked(self):
        """Test that unsupported claims are tracked."""
        result = SectionResult(
            section_name="Test",
            formatting_score=1.0,
            completeness_score=1.0,
            hallucination_score=0.9,
            unsupported_claims=[
                {
                    "claim": "Patient had surgery",
                    "citation": "page 10",
                    "verdict": "UNSUPPORTED",
                },
            ],
        )
        
        assert len(result.unsupported_claims) == 1
        assert result.unsupported_claims[0]['verdict'] == "UNSUPPORTED"


class TestBenchmarkContractV2Fields:
    """Tests for V2 fields added to BenchmarkContract."""

    def test_v2_fields_defaults(self):
        """New V2 fields have correct defaults."""
        c = BenchmarkContract(section_name="Test")
        assert c.forbidden_words == []
        assert c.source_citation_limit is None
        assert c.chronological_order is False
        assert c.chronological_direction == "ascending"
        assert c.empty_state_message is None
        assert c.output_type == "single"
        assert c.sort_by is None
        assert c.heading_hierarchy == []
        assert c.scope_filters == []
        assert c.dedup_required is False
        assert c.anti_patterns == []
        assert c.instruction_version == ""

    def test_v2_fields_roundtrip_dict(self):
        """to_dict -> from_dict preserves all V2 fields."""
        c = BenchmarkContract(
            section_name="Medical Chronology",
            forbidden_words=["None", "N/A", "Unknown"],
            source_citation_limit=5,
            heading_hierarchy=["## Condition", "### YYYY", "- **DD MMM**"],
            chronological_order=True,
            chronological_direction="ascending",
            empty_state_message="No medical records found in the file.",
            output_type="list",
            sort_by="encounter_date",
            scope_filters=["Section F only", "exclude administrative"],
            dedup_required=True,
            anti_patterns=["Do not add introductory text after headings"],
            instruction_version="abc123",
        )
        d = c.to_dict()
        c2 = BenchmarkContract.from_dict(d)

        assert c2.forbidden_words == ["None", "N/A", "Unknown"]
        assert c2.source_citation_limit == 5
        assert c2.heading_hierarchy == ["## Condition", "### YYYY", "- **DD MMM**"]
        assert c2.chronological_order is True
        assert c2.chronological_direction == "ascending"
        assert c2.empty_state_message == "No medical records found in the file."
        assert c2.output_type == "list"
        assert c2.sort_by == "encounter_date"
        assert c2.scope_filters == ["Section F only", "exclude administrative"]
        assert c2.dedup_required is True
        assert c2.anti_patterns == ["Do not add introductory text after headings"]
        assert c2.instruction_version == "abc123"

    def test_v2_fields_roundtrip_json(self):
        """to_json -> from_json preserves V2 fields."""
        c = BenchmarkContract(
            section_name="Test",
            forbidden_words=["N/A"],
            source_citation_limit=3,
            chronological_order=True,
        )
        json_str = c.to_json()
        c2 = BenchmarkContract.from_json(json_str)
        assert c2.forbidden_words == ["N/A"]
        assert c2.source_citation_limit == 3
        assert c2.chronological_order is True

    def test_backward_compat_from_dict_missing_v2_fields(self):
        """Old dicts without V2 fields load with correct defaults."""
        old_data = {
            "section_name": "Legacy",
            "required_fields": ["Field1"],
            "date_format": "MM/DD/YYYY",
        }
        c = BenchmarkContract.from_dict(old_data)
        assert c.section_name == "Legacy"
        assert c.forbidden_words == []
        assert c.source_citation_limit is None
        assert c.chronological_order is False
        assert c.output_type == "single"

    def test_v2_fields_in_to_dict_keys(self):
        """to_dict output contains all V2 field keys."""
        c = BenchmarkContract(section_name="Test")
        d = c.to_dict()
        v2_keys = [
            "forbidden_words", "source_citation_limit", "heading_hierarchy",
            "chronological_order", "chronological_direction", "empty_state_message",
            "output_type", "sort_by", "scope_filters", "dedup_required",
            "anti_patterns", "instruction_version",
        ]
        for key in v2_keys:
            assert key in d, f"Missing key: {key}"


class TestSectionResultV2Scores:
    """Tests for V2 score fields on SectionResult."""

    def test_v2_scores_default_to_one(self):
        """V2 scores default to 1.0 (no violations)."""
        r = SectionResult(section_name="Test")
        assert r.forbidden_words_score == 1.0
        assert r.source_limit_score == 1.0
        assert r.chronological_score == 1.0
        assert r.heading_hierarchy_score == 1.0
        assert r.empty_state_score == 1.0
        assert r.field_completeness_score == 1.0

    def test_v2_scores_in_to_dict(self):
        """to_dict includes V2 scores that are active."""
        from src.contracts.base import ValidationError as VErr
        r = SectionResult(
            section_name="Test",
            forbidden_words_score=0.8,
            chronological_score=0.9,
            forbidden_words_violations=[
                VErr(code="FORBIDDEN_WORD", message="Found 'N/A'"),
            ],
        )
        d = r.to_dict()
        assert d["scores"]["forbidden_words"] == 0.8
        assert d["scores"]["chronological"] == 0.9
        assert d["scores"]["clinical_coverage"] == 0.0
        assert d["scores"]["date_coverage"] == 1.0

    def test_v2_violations_in_to_dict(self):
        """to_dict includes V2 violation lists."""
        from src.contracts.base import ValidationError
        r = SectionResult(
            section_name="Test",
            forbidden_words_violations=[
                ValidationError(code="FORBIDDEN_WORD", message="Found 'N/A' at line 15", line=15),
            ],
            chronological_violations=[
                ValidationError(code="OUT_OF_ORDER", message="Date 03/20 before 03/15", line=42),
            ],
        )
        d = r.to_dict()
        assert len(d["errors"]["forbidden_words"]) == 1
        assert d["errors"]["forbidden_words"][0]["code"] == "FORBIDDEN_WORD"
        assert len(d["errors"]["chronological"]) == 1
        assert d["errors"]["chronological"][0]["code"] == "OUT_OF_ORDER"

    def test_v2_empty_violations_in_to_dict(self):
        """to_dict has empty lists for core V2 violation keys when none exist."""
        r = SectionResult(section_name="Test")
        d = r.to_dict()
        for key in ["formatting", "chronological", "date_coverage"]:
            assert key in d["errors"]
            assert d["errors"][key] == []
        assert "forbidden_words" not in d["errors"]


class TestComputeTotalScoreV2:
    """Tests for compute_total_score_v2 dynamic weight allocation."""

    def test_core_only_no_contract(self):
        """Without contract, only core dimensions are used (no hallucination when has_entries=False)."""
        r = SectionResult(
            section_name="Test",
            formatting_score=0.9,
            completeness_score=0.8,
            hallucination_score=1.0,
        )
        r.compute_total_score_v2()
        # has_entries=False (completeness=0.8>0 → actually True), so hallucination included
        # weights: formatting=0.10, completeness=0.25, hallucination=0.20 → sum=0.55
        expected = (0.9 * 0.10 + 0.8 * 0.25 + 1.0 * 0.20) / 0.55
        assert abs(r.total_score - expected) < 0.001

    def test_all_dimensions_perfect(self):
        """All dimensions active with perfect scores yields 1.0."""
        c = BenchmarkContract(
            section_name="Full",
            forbidden_words=["N/A"],
            source_citation_limit=5,
            chronological_order=True,
            heading_hierarchy=["## H2"],
            empty_state_message="No data.",
            required_fields=["Field1"],
        )
        r = SectionResult(
            section_name="Full",
            formatting_score=1.0,
            completeness_score=1.0,
            hallucination_score=1.0,
            forbidden_words_score=1.0,
            source_limit_score=1.0,
            chronological_score=1.0,
            heading_hierarchy_score=1.0,
            empty_state_score=1.0,
            field_completeness_score=1.0,
        )
        r.compute_total_score_v2(c)
        assert abs(r.total_score - 1.0) < 0.001

    def test_all_dimensions_zero(self):
        """All dimensions active with zero scores yields 0.0."""
        c = BenchmarkContract(
            section_name="Zero",
            forbidden_words=["N/A"],
            source_citation_limit=5,
            chronological_order=True,
            heading_hierarchy=["## H2"],
            empty_state_message="No data.",
            required_fields=["Field1"],
        )
        r = SectionResult(
            section_name="Zero",
            formatting_score=0.0,
            completeness_score=0.0,
            hallucination_score=0.0,
            forbidden_words_score=0.0,
            source_limit_score=0.0,
            chronological_score=0.0,
            heading_hierarchy_score=0.0,
            empty_state_score=0.0,
            field_completeness_score=0.0,
        )
        r.compute_total_score_v2(c)
        assert r.total_score == 0.0

    def test_partial_dimensions_weight_redistribution(self):
        """Only some V2 rules active: weights redistribute correctly."""
        c = BenchmarkContract(
            section_name="Partial",
            forbidden_words=["None"],
            chronological_order=True,
        )
        r = SectionResult(
            section_name="Partial",
            formatting_score=0.9,
            completeness_score=0.8,
            hallucination_score=1.0,
            forbidden_words_score=1.0,
            chronological_score=0.7,
        )
        r.compute_total_score_v2(c)
        # has_entries = completeness_score > 0 → True
        # active: formatting=0.10, completeness=0.25, hallucination=0.20,
        #         forbidden_words=0.05, chronological=0.10 → sum=0.70
        expected = (0.9 * 0.10 + 0.8 * 0.25 + 1.0 * 0.20 + 1.0 * 0.05 + 0.7 * 0.10) / 0.70
        assert abs(r.total_score - expected) < 0.001

    def test_legacy_compute_total_score_unchanged(self):
        """Legacy compute_total_score still works with 3-weight tuple."""
        r = SectionResult(
            section_name="Legacy",
            formatting_score=0.9,
            completeness_score=0.8,
            hallucination_score=1.0,
        )
        r.compute_total_score()
        expected = 0.9 * 0.33 + 0.8 * 0.33 + 1.0 * 0.34
        assert abs(r.total_score - expected) < 0.001

    def test_legacy_compute_total_score_custom_weights(self):
        """Legacy compute_total_score works with custom weight tuple."""
        r = SectionResult(
            section_name="Custom",
            formatting_score=1.0,
            completeness_score=0.5,
            hallucination_score=0.0,
        )
        r.compute_total_score((0.5, 0.3, 0.2))
        expected = 1.0 * 0.5 + 0.5 * 0.3 + 0.0 * 0.2
        assert abs(r.total_score - expected) < 0.001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
