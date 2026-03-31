"""Tests for V1 Parser (Regex-only mode)."""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.contracts.v1_parser import V1Parser
from src.contracts.base import BenchmarkContract


class TestV1ParserSectionName:
    """Tests for section name extraction."""
    
    def test_extract_section_name_medical_chronology(self):
        """Test extracting 'Medical Chronology' section name."""
        instruction = "Create a section of a report call Medical Chronology..."
        parser = V1Parser(use_llm=False)
        contract = parser.parse(instruction)
        
        assert contract.section_name == "Medical Chronology"
    
    def test_extract_section_name_review_of_records(self):
        """Test extracting 'Review of Records' section name."""
        instruction = "Create a Review of Records section..."
        parser = V1Parser(use_llm=False)
        contract = parser.parse(instruction)
        
        assert "review of records" in contract.section_name.lower()
    
    def test_extract_section_name_history_of_illness(self):
        """Test extracting 'HISTORY OF ILLNESS' section name."""
        instruction = "Create a section called HISTORY OF ILLNESS..."
        parser = V1Parser(use_llm=False)
        contract = parser.parse(instruction)
        
        assert "HISTORY OF ILLNESS" in contract.section_name.upper()


class TestV1ParserFields:
    """Tests for field extraction."""
    
    def test_extract_bold_fields(self):
        """Test extracting **Field:** format fields."""
        instruction = "Include: **Facility Name:**, **Provider Name:**, **Diagnoses:**"
        parser = V1Parser(use_llm=False)
        contract = parser.parse(instruction)
        
        assert "Facility Name" in contract.required_fields
        assert "Provider Name" in contract.required_fields
        assert "Diagnoses" in contract.required_fields
    
    def test_extract_bracket_fields(self):
        """Test extracting [Field] format fields."""
        instruction = "Include [Claimant Name], [Date of Birth], [Claim Type]"
        parser = V1Parser(use_llm=False)
        contract = parser.parse(instruction)
        
        assert "Claimant Name" in contract.required_fields
        assert "Date of Birth" in contract.required_fields
        assert "Claim Type" in contract.required_fields
    
    def test_no_duplicate_fields(self):
        """Test that duplicate fields are not added."""
        instruction = "Include **Name:** and also **Name:** again"
        parser = V1Parser(use_llm=False)
        contract = parser.parse(instruction)
        
        name_count = sum(1 for f in contract.required_fields if f == "Name")
        assert name_count <= 1


class TestV1ParserDateFormat:
    """Tests for date format detection."""
    
    def test_detect_mm_dd_yyyy(self):
        """Test detecting MM/DD/YYYY format."""
        instruction = "Use date format MM/DD/YYYY for all dates"
        parser = V1Parser(use_llm=False)
        contract = parser.parse(instruction)
        
        assert contract.date_format == "MM/DD/YYYY"
    
    def test_detect_mm_dd_yy(self):
        """Test detecting MM/DD/YY format."""
        instruction = "Dates should be in MM/DD/YY format"
        parser = V1Parser(use_llm=False)
        contract = parser.parse(instruction)
        
        assert contract.date_format == "MM/DD/YY"
    
    def test_detect_month_day_year(self):
        """Test detecting Month Day, Year format."""
        instruction = "Format dates as Month Day, Year (e.g., January 15, 2023)"
        parser = V1Parser(use_llm=False)
        contract = parser.parse(instruction)
        
        assert contract.date_format == "Month Day, Year"
    
    def test_detect_from_example_date(self):
        """Test detecting format from example date."""
        instruction = "Example: 01/15/2023 was the visit date"
        parser = V1Parser(use_llm=False)
        contract = parser.parse(instruction)
        
        assert contract.date_format == "MM/DD/YYYY"


class TestV1ParserCitationStyle:
    """Tests for citation style detection."""
    
    def test_detect_consolidated_citation(self):
        """Test detecting consolidated citation style."""
        instruction = "Add Source References at the end of each visit"
        parser = V1Parser(use_llm=False)
        contract = parser.parse(instruction)
        
        assert contract.citation_style == "consolidated"
        assert contract.citation_field == "Source References"
    
    def test_detect_no_citation(self):
        """Test detecting no citation requirement."""
        instruction = "Create output without references or footnotes"
        parser = V1Parser(use_llm=False)
        contract = parser.parse(instruction)
        
        # Should detect "without references" - citation_required should be False
        # because citation_style detected as "none"
        assert contract.citation_required is False or contract.citation_style == "none"


class TestV1ParserOutputStyle:
    """Tests for output style detection."""
    
    def test_detect_narrative_style(self):
        """Test detecting narrative (no bullets) style."""
        instruction = "Do not use bullet points. Write in prose paragraphs."
        parser = V1Parser(use_llm=False)
        contract = parser.parse(instruction)
        
        # Check via internal method
        style = parser._detect_output_style(instruction)
        assert style == "narrative"
    
    def test_detect_bullets_not_allowed(self):
        """Test detecting bullets not allowed."""
        instruction = "Do not use bullet points in the output"
        parser = V1Parser(use_llm=False)
        contract = parser.parse(instruction)
        
        bullets_allowed = parser._detect_bullets_allowed(instruction)
        assert bullets_allowed is False


class TestV1ParserVerbatim:
    """Tests for verbatim requirement detection."""
    
    def test_detect_verbatim_required(self):
        """Test detecting verbatim extraction requirement."""
        instruction = "Extract information verbatim from the source"
        parser = V1Parser(use_llm=False)
        contract = parser.parse(instruction)
        
        assert contract.verbatim_required is True
    
    def test_detect_no_paraphrase(self):
        """Test detecting 'do not paraphrase' requirement."""
        instruction = "Do not paraphrase. Use exact wording from source."
        parser = V1Parser(use_llm=False)
        contract = parser.parse(instruction)
        
        assert contract.verbatim_required is True


class TestV1ParserOmitIfMissing:
    """Tests for omit if missing detection."""
    
    def test_detect_omit_if_missing(self):
        """Test detecting omit if missing rule."""
        instruction = "If the value is not available, omit the heading for that field"
        parser = V1Parser(use_llm=False)
        contract = parser.parse(instruction)
        
        assert contract.omit_if_missing is True


class TestV1ParserIntegration:
    """Integration tests with fixture file."""
    
    def test_parse_sample_instruction(self):
        """Test parsing the sample instruction fixture."""
        fixture_path = Path(__file__).parent / "fixtures" / "sample_instruction.txt"
        instruction = fixture_path.read_text()
        
        parser = V1Parser(use_llm=False)
        contract = parser.parse(instruction)
        
        # Check section name
        assert "Medical Chronology" in contract.section_name
        
        # Check fields
        assert "Facility Name" in contract.required_fields
        assert "Provider Name" in contract.required_fields
        
        # Check date format
        assert contract.date_format == "MM/DD/YYYY"
        
        # Check citation style
        assert contract.citation_style == "consolidated"
        assert contract.citation_field == "Source References"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
