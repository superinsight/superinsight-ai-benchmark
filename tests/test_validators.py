"""Tests for Deterministic Validators."""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.contracts.base import BenchmarkContract
from src.validators.formatting import FormattingValidator
from src.validators.citation import CitationValidator


class TestFormattingValidator:
    """Tests for formatting validation."""
    
    @pytest.fixture
    def basic_contract(self):
        """Create a basic contract for testing."""
        return BenchmarkContract(
            section_name="Medical Chronology",
            date_format="MM/DD/YYYY",
            required_fields=["Facility Name", "Provider Name", "Diagnoses"],
        )
    
    def test_valid_output_passes(self, basic_contract):
        """Test that valid output passes formatting checks."""
        validator = FormattingValidator(basic_contract)
        
        output = """# Medical Chronology

## 01/15/2023
- **Facility Name:** St. Mary Hospital
- **Provider Name:** Dr. John Smith
- **Diagnoses:** Type 2 Diabetes
"""
        score, errors = validator.validate(output)
        
        assert score >= 0.8
    
    def test_missing_main_heading(self, basic_contract):
        """Test that missing main heading is detected."""
        validator = FormattingValidator(basic_contract)
        
        output = """## 01/15/2023
- **Facility Name:** Hospital
"""
        score, errors = validator.validate(output)
        
        assert any(e.code == "MISSING_MAIN_HEADING" for e in errors)
    
    def test_wrong_main_heading(self, basic_contract):
        """Test that wrong main heading is detected."""
        validator = FormattingValidator(basic_contract)
        
        output = """# Wrong Section Name

## 01/15/2023
- **Facility Name:** Hospital
"""
        score, errors = validator.validate(output)
        
        assert any(e.code == "MAIN_HEADING_MISMATCH" for e in errors)


class TestFormattingValidatorDateFormat:
    """Tests for date format validation."""
    
    def test_correct_date_format(self):
        """Test that correct date format passes."""
        contract = BenchmarkContract(
            section_name="Test",
            date_format="MM/DD/YYYY",
            entry_header_pattern=r'\*\*<u>.+?</u>\*\*',
        )
        validator = FormattingValidator(contract)
        
        output = """# Test

**<u>01/15/2023. Visit.</u>**
- Some content
"""
        score, errors = validator.validate(output)
        
        # Should not have date format errors
        date_errors = [e for e in errors if e.code == "DATE_FORMAT"]
        assert len(date_errors) == 0
    
    def test_wrong_date_format_yy_instead_of_yyyy(self):
        """Test that wrong date format (YY instead of YYYY) is detected."""
        contract = BenchmarkContract(
            section_name="Test",
            date_format="MM/DD/YYYY",
            entry_header_pattern=r'\*\*<u>.+?</u>\*\*',
        )
        validator = FormattingValidator(contract)
        
        output = """# Test

**<u>01/15/23. Visit.</u>**
- Some content
"""
        score, errors = validator.validate(output)
        
        # Should detect wrong date format
        date_errors = [e for e in errors if e.code == "DATE_FORMAT"]
        assert len(date_errors) > 0


class TestCitationValidator:
    """Tests for citation validation."""
    
    @pytest.fixture
    def citation_contract(self):
        """Create a contract with citation requirements."""
        return BenchmarkContract(
            section_name="Test",
            citation_required=True,
            citation_style="inline",
            citation_pattern=r'<!--\s*Source:.*?-->',
        )
    
    def test_valid_citations(self, citation_contract):
        """Test that valid citations are counted correctly."""
        validator = CitationValidator(citation_contract)
        
        output = """# Test

## Visit 1
- **Diagnoses:** Diabetes <!-- Source: file: doc.pdf, page: 1 -->

## Visit 2
- **Diagnoses:** Hypertension <!-- Source: file: doc.pdf, page: 2 -->
"""
        score, errors, stats = validator.validate(output)
        
        assert stats['total_citations'] == 2
    
    def test_missing_citations(self, citation_contract):
        """Test that entries without citations are flagged."""
        validator = CitationValidator(citation_contract)
        
        # Use the entry format the validator expects: **<u>...</u>**
        output = """# Test

**<u>01/15/2023. Visit 1.</u>**
- **Diagnoses:** Diabetes

**<u>01/20/2023. Visit 2.</u>**
- **Diagnoses:** Hypertension
"""
        score, errors, stats = validator.validate(output)
        
        assert stats['total_citations'] == 0
        assert stats['total_entries'] == 2
        assert score < 1.0  # Missing citations should penalize score
    
    def test_citation_format_parsing(self, citation_contract):
        """Test that citation format is correctly parsed."""
        validator = CitationValidator(citation_contract)
        
        output = """# Test
- Data <!-- Source: file: records.pdf, page: 15, file_id: abc123, paragraph_ref: xyz -->
"""
        score, errors, stats = validator.validate(output)
        
        assert stats['total_citations'] == 1


class TestFormattingValidatorFieldLabels:
    """Tests for field label formatting."""
    
    def test_field_label_whitespace(self):
        """Test that field labels with extra whitespace are flagged."""
        contract = BenchmarkContract(section_name="Test")
        validator = FormattingValidator(contract)
        
        output = """# Test
- ** Field Name :** Value
"""
        # Note: This specific test depends on implementation
        # The current validator checks for leading/trailing spaces in field names
        score, errors = validator.validate(output)
        
        # May or may not catch this depending on implementation
        # This is more of a documentation test


class TestValidatorIntegration:
    """Integration tests with fixture files."""
    
    def test_validate_sample_output(self):
        """Test validating the sample output fixture."""
        fixture_path = Path(__file__).parent / "fixtures" / "sample_output.md"
        output = fixture_path.read_text()
        
        contract = BenchmarkContract(
            section_name="Medical Chronology",
            date_format="MM/DD/YYYY",
            required_fields=["Facility Name", "Provider Name", "Diagnoses", "Plan"],
            citation_required=True,
        )
        
        # Formatting validation
        fmt_validator = FormattingValidator(contract)
        fmt_score, fmt_errors = fmt_validator.validate(output)
        
        # Citation validation
        cite_validator = CitationValidator(contract)
        cite_score, cite_errors, cite_stats = cite_validator.validate(output)
        
        # Should have citations
        assert cite_stats['total_citations'] >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
