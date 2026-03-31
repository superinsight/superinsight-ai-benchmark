"""
Multi-Section Report Evaluator.

Evaluates reports containing multiple sections, each with its own
output file and instruction. Produces a unified BenchmarkReport
with per-section scores and an overall score.

Config JSON format:
{
  "report_name": "Medical Legal Report",
  "source": "path/to/source.txt",  // optional, can be per-section
  "sections": [
    {
      "name": "Medical Chronology",
      "output": "section1_output.md",
      "instruction": "instruction1.txt",
      "source": "source1.txt"  // optional, overrides global
    },
    ...
  ]
}
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Any

from ..contracts.base import BenchmarkContract, BenchmarkReport, SectionResult
from ..contracts.v1_parser import V1Parser
from ..contracts.llm_backend import get_backend, LLMBackend
from .calculator import ScoringCalculator


@dataclass
class SectionConfig:
    """Configuration for a single section."""
    name: str
    output: str
    instruction: Optional[str] = None
    contract: Optional[str] = None  # Pre-built contract JSON
    source: Optional[str] = None    # Section-specific source
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SectionConfig":
        return cls(
            name=data.get("name", "Unknown Section"),
            output=data["output"],
            instruction=data.get("instruction"),
            contract=data.get("contract"),
            source=data.get("source"),
        )


@dataclass
class ReportConfig:
    """Configuration for a multi-section report."""
    report_name: str = "Benchmark Report"
    source: Optional[str] = None  # Global source file
    base_path: str = ""  # Base path for relative paths
    sections: List[SectionConfig] = field(default_factory=list)
    
    # Evaluation settings
    deep_check: bool = False
    max_claims: int = 50
    batch_size: int = 10
    max_workers: int = 5  # Max concurrent API calls
    parallel: bool = True  # Use parallel processing
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], base_path: str = "") -> "ReportConfig":
        sections = [SectionConfig.from_dict(s) for s in data.get("sections", [])]
        return cls(
            report_name=data.get("report_name", "Benchmark Report"),
            source=data.get("source"),
            base_path=base_path,
            sections=sections,
            deep_check=data.get("deep_check", False),
            max_claims=data.get("max_claims", 50),
            batch_size=data.get("batch_size", 10),
            max_workers=data.get("max_workers", 5),
            parallel=data.get("parallel", True),
        )
    
    @classmethod
    def from_json_file(cls, path: str) -> "ReportConfig":
        """Load config from JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        base_path = str(Path(path).parent)
        return cls.from_dict(data, base_path)
    
    def resolve_path(self, path: str) -> str:
        """Resolve relative path against base_path."""
        if not path:
            return path
        if path.startswith("s3://") or os.path.isabs(path):
            return path
        return os.path.join(self.base_path, path)


class MultiSectionEvaluator:
    """
    Evaluate multiple sections of a report.
    
    Each section can have its own:
    - Output file
    - Instruction (or pre-built contract)
    - Source file (optional, falls back to global)
    
    Example:
        config = ReportConfig.from_json_file("report_config.json")
        evaluator = MultiSectionEvaluator(config)
        report = evaluator.evaluate(verbose=True)
        print(report.to_json())
    """
    
    def __init__(
        self,
        config: ReportConfig,
        llm_backend: Optional[LLMBackend] = None,
        use_llm: bool = True,
    ):
        """
        Initialize evaluator.
        
        Args:
            config: Report configuration
            llm_backend: LLM backend for parsing (optional)
            use_llm: Whether to use LLM for instruction parsing
        """
        self.config = config
        self.llm_backend = llm_backend
        self.use_llm = use_llm
        self._file_cache: Dict[str, str] = {}
    
    def _read_file(self, path: str) -> str:
        """Read file with caching."""
        resolved = self.config.resolve_path(path)
        
        if resolved in self._file_cache:
            return self._file_cache[resolved]
        
        # Check for S3 path
        if resolved.startswith("s3://"):
            from ..utils.s3_utils import S3Client, S3Path
            s3 = S3Client()
            s3_path = S3Path.parse(resolved)
            content = s3.read_text(s3_path.bucket, s3_path.key)
        else:
            with open(resolved, 'r', encoding='utf-8') as f:
                content = f.read()
        
        self._file_cache[resolved] = content
        return content
    
    def _load_contract(self, section: SectionConfig) -> BenchmarkContract:
        """Load or generate contract for a section."""
        if section.contract:
            # Load pre-built contract
            contract_text = self._read_file(section.contract)
            return BenchmarkContract.from_json(contract_text)
        
        if section.instruction:
            # Parse instruction to generate contract
            instruction_text = self._read_file(section.instruction)
            parser = V1Parser(backend=self.llm_backend, use_llm=self.use_llm)
            contract = parser.parse(instruction_text)
            # Override section name if provided
            if section.name:
                contract.section_name = section.name
            return contract
        
        # Minimal contract with just the section name
        return BenchmarkContract(section_name=section.name)
    
    def _get_source_text(self, section: SectionConfig) -> Optional[str]:
        """Get source text for a section."""
        source_path = section.source or self.config.source
        if source_path:
            return self._read_file(source_path)
        return None
    
    def evaluate_section(
        self,
        section: SectionConfig,
        verbose: bool = False,
    ) -> SectionResult:
        """
        Evaluate a single section.
        
        Args:
            section: Section configuration
            verbose: Print progress
            
        Returns:
            SectionResult with scores
        """
        if verbose:
            print(f"\n📄 Evaluating section: {section.name}")
        
        # Load contract
        contract = self._load_contract(section)
        if verbose:
            print(f"   Contract: {contract.section_name}")
            print(f"   Required fields: {len(contract.required_fields)}")
        
        # Load output
        output_md = self._read_file(section.output)
        if verbose:
            print(f"   Output: {len(output_md):,} chars")
        
        # Load source
        source_text = self._get_source_text(section)
        if verbose and source_text:
            print(f"   Source: {len(source_text):,} chars")
        
        # Calculate scores
        calculator = ScoringCalculator(contract)
        result = calculator.calculate(
            output_md,
            source_text,
            skip_llm_judge=not self.config.deep_check,
            max_claims=self.config.max_claims,
            batch_size=self.config.batch_size,
            max_workers=self.config.max_workers,
            parallel=self.config.parallel,
            verbose=verbose,
        )
        
        # Ensure section name is set
        result.section_name = section.name
        
        return result
    
    def evaluate(self, verbose: bool = False) -> BenchmarkReport:
        """
        Evaluate all sections in the report.
        
        Args:
            verbose: Print progress
            
        Returns:
            BenchmarkReport with all section results
        """
        if verbose:
            print(f"📊 Evaluating report: {self.config.report_name}")
            print(f"   Sections: {len(self.config.sections)}")
            if self.config.deep_check:
                print(f"   Deep check: enabled (max {self.config.max_claims} claims, batch {self.config.batch_size})")
        
        report = BenchmarkReport(
            mode="v1",
        )
        
        # Evaluate each section
        for section in self.config.sections:
            try:
                result = self.evaluate_section(section, verbose=verbose)
                report.sections.append(result)
                
                if verbose:
                    print(f"   ✓ {section.name}: {result.total_score:.2%}")
            except Exception as e:
                if verbose:
                    print(f"   ✗ {section.name}: Error - {e}")
                # Add error result
                error_result = SectionResult(
                    section_name=section.name,
                    formatting_score=0.0,
                    completeness_score=0.0,
                    hallucination_score=0.0,
                    total_score=0.0,
                )
                report.sections.append(error_result)
        
        # Compute overall score
        report.compute_overall_score()
        
        if verbose:
            print(f"\n📈 Overall Score: {report.overall_score:.2%}")
        
        return report


def evaluate_report_config(
    config_path: str,
    llm_backend: Optional[str] = None,
    use_llm: bool = True,
    verbose: bool = False,
) -> BenchmarkReport:
    """
    Convenience function to evaluate a report from config file.
    
    Args:
        config_path: Path to report config JSON
        llm_backend: LLM backend name ('gemini' or 'nebius')
        use_llm: Whether to use LLM for parsing
        verbose: Print progress
        
    Returns:
        BenchmarkReport with all results
    """
    config = ReportConfig.from_json_file(config_path)
    
    backend = None
    if use_llm and llm_backend:
        backend = get_backend(llm_backend)
    
    evaluator = MultiSectionEvaluator(config, llm_backend=backend, use_llm=use_llm)
    return evaluator.evaluate(verbose=verbose)
