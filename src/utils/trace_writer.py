"""
Trace Writer for saving benchmark results and intermediate data.

This module provides functionality to save benchmark traces including:
- benchmark_result.json: Complete evaluation results
- claims.json: All extracted claims
- verdicts.json: All hallucination verification results
- contract.json: The parsed contract used for evaluation
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class TraceMetadata:
    """Metadata for trace files."""
    benchmark_version: str = "1.0.0"
    created_at: str = ""
    research_id: str = ""
    output_file: str = ""
    instruction_file: str = ""
    source_file: str = ""
    llm_backend: str = ""
    deep_check: bool = False
    max_claims: int = 50
    batch_size: int = 10
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat() + "Z"


class TraceWriter:
    """
    Write benchmark traces to a directory.
    
    Creates a directory structure with:
    - benchmark_result.json: Complete evaluation results with scores
    - claims.json: All extracted claims (before verification)
    - verdicts.json: All hallucination verification results
    - contract.json: The parsed benchmark contract
    - metadata.json: Run metadata and configuration
    """
    
    def __init__(self, output_dir: str, auto_create: bool = True):
        """
        Initialize TraceWriter.
        
        Args:
            output_dir: Directory to write trace files
            auto_create: Create directory if it doesn't exist
        """
        self.output_dir = Path(output_dir)
        if auto_create:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self._metadata: Optional[TraceMetadata] = None
        self._benchmark_result: Optional[Dict] = None
        self._claims: List[Dict] = []
        self._verdicts: List[Dict] = []
        self._contract: Optional[Dict] = None
        self._hallucination_result: Optional[Dict] = None
        self._completeness_details: Optional[Dict] = None
    
    def set_metadata(
        self,
        research_id: str = "",
        output_file: str = "",
        instruction_file: str = "",
        source_file: str = "",
        llm_backend: str = "",
        deep_check: bool = False,
        max_claims: int = 50,
        batch_size: int = 10,
    ):
        """Set trace metadata."""
        self._metadata = TraceMetadata(
            research_id=research_id,
            output_file=output_file,
            instruction_file=instruction_file,
            source_file=source_file,
            llm_backend=llm_backend,
            deep_check=deep_check,
            max_claims=max_claims,
            batch_size=batch_size,
        )
    
    def set_contract(self, contract_dict: Dict):
        """Set the benchmark contract."""
        self._contract = contract_dict
    
    def set_benchmark_result(self, result_dict: Dict):
        """Set the final benchmark result."""
        self._benchmark_result = result_dict
    
    def set_claims(self, claims: List[Dict]):
        """Set extracted claims."""
        self._claims = claims
    
    def set_verdicts(self, verdicts: List[Dict]):
        """Set hallucination verdicts."""
        self._verdicts = verdicts
    
    def set_hallucination_result(self, result: Dict):
        """Set full hallucination result including timing stats."""
        self._hallucination_result = result
    
    def set_completeness_details(self, details: Dict):
        """Set completeness check details."""
        self._completeness_details = details
    
    def write_all(self):
        """Write all trace files to the output directory."""
        
        # Always write metadata
        if self._metadata:
            self._write_json("metadata.json", asdict(self._metadata))
        
        # Write contract if available
        if self._contract:
            self._write_json("contract.json", self._contract)
        
        # Write benchmark result
        if self._benchmark_result:
            self._write_json("benchmark_result.json", self._benchmark_result)
        
        # Write claims
        if self._claims:
            self._write_json("claims.json", {
                "total_claims": len(self._claims),
                "claims": self._claims,
            })
        
        # Write verdicts
        if self._verdicts:
            self._write_json("verdicts.json", {
                "total_verdicts": len(self._verdicts),
                "verdicts": self._verdicts,
            })
        
        # Write hallucination result (detailed)
        if self._hallucination_result:
            self._write_json("hallucination_details.json", self._hallucination_result)
        
        # Write completeness details
        if self._completeness_details:
            self._write_json("completeness_details.json", self._completeness_details)
        
        return self.output_dir
    
    def _write_json(self, filename: str, data: Any):
        """Write data to a JSON file."""
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    def get_output_dir(self) -> Path:
        """Get the output directory path."""
        return self.output_dir
    
    @classmethod
    def create_with_timestamp(cls, base_dir: str, prefix: str = "trace") -> "TraceWriter":
        """
        Create a TraceWriter with a timestamped subdirectory.
        
        Args:
            base_dir: Base directory for traces
            prefix: Prefix for the trace directory name
            
        Returns:
            TraceWriter instance
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(base_dir, f"{prefix}_{timestamp}")
        return cls(output_dir)


def write_trace(
    output_dir: str,
    benchmark_result: Dict,
    claims: List[Dict] = None,
    verdicts: List[Dict] = None,
    contract: Dict = None,
    metadata: Dict = None,
) -> str:
    """
    Convenience function to write a complete trace.
    
    Args:
        output_dir: Directory to write trace files
        benchmark_result: The benchmark result dictionary
        claims: Optional list of claim dictionaries
        verdicts: Optional list of verdict dictionaries
        contract: Optional contract dictionary
        metadata: Optional metadata dictionary
        
    Returns:
        Path to the output directory
    """
    writer = TraceWriter(output_dir)
    
    if metadata:
        writer.set_metadata(**metadata)
    
    writer.set_benchmark_result(benchmark_result)
    
    if claims:
        writer.set_claims(claims)
    
    if verdicts:
        writer.set_verdicts(verdicts)
    
    if contract:
        writer.set_contract(contract)
    
    writer.write_all()
    return str(writer.get_output_dir())
