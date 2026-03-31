"""
Base LLM Judge for benchmark validation.

This module provides the base class for LLM-based judges
that evaluate output quality using Gemini API.
"""

import os
import json
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from enum import Enum


class Verdict(str, Enum):
    """Verdict from LLM judge."""
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    PARTIAL = "PARTIAL"
    ERROR = "ERROR"
    INCONCLUSIVE = "INCONCLUSIVE"  # Cannot determine - source was truncated or citation lookup failed


@dataclass
class JudgeVerdict:
    """Result from LLM judge evaluation."""
    verdict: Verdict
    confidence: float  # 0.0 to 1.0
    reason: str
    claim: str = ""
    source_excerpt: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "confidence": self.confidence,
            "reason": self.reason,
            "claim": self.claim,
            "source_excerpt": self.source_excerpt[:200] if self.source_excerpt else "",
        }


class LLMJudge:
    """
    Base class for LLM-based judges.
    
    Uses Google Cloud Gemini API (via google-genai SDK) for evaluation.
    """
    
    def __init__(
        self,
        model: str = "gemini-2.5-pro",
        temperature: float = 0.1,
        max_tokens: int = 1024,
        project_id: Optional[str] = None,
        location: str = "us-central1",
    ):
        """
        Initialize LLM Judge.
        
        Args:
            model: Gemini model name
            temperature: Sampling temperature (low for consistent judging)
            max_tokens: Max output tokens
            project_id: GCP project ID
            location: GCP location
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        self.location = location
        
        self._client = None
    
    @property
    def client(self):
        """Lazy load Gemini client."""
        if self._client is None:
            self._client = self._create_client()
        return self._client
    
    def _create_client(self):
        """Create Gemini client."""
        try:
            from google import genai
            
            # Setup credentials if needed
            self._setup_credentials()
            
            return genai.Client(
                vertexai=True,
                project=self.project_id,
                location=self.location,
            )
        except ImportError:
            raise ImportError(
                "google-genai package is required. "
                "Install it with: pip install google-genai"
            )
    
    def _setup_credentials(self):
        """Setup Google credentials from environment."""
        google_cert_json = os.getenv("GOOGLE_CERT_JSON", "")
        google_cert_location = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        # Check if credentials file exists
        cert_exists = (
            google_cert_location is not None and 
            os.path.exists(google_cert_location) and 
            os.path.isfile(google_cert_location)
        )
        
        # Create credentials file from JSON if needed
        if not cert_exists and google_cert_json:
            json_cert = json.loads(google_cert_json)
            cert_path = google_cert_location or '/tmp/google-credentials.json'
            with open(cert_path, 'w') as f:
                json.dump(json_cert, f)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cert_path
    
    def generate(self, prompt: str) -> str:
        """
        Generate response from LLM.
        
        Args:
            prompt: The prompt to send
            
        Returns:
            Generated text response
        """
        from google.genai import types
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
            )
        )
        
        return response.text if response.text else ""
    
    def evaluate(self, claim: str, source_excerpt: str) -> JudgeVerdict:
        """
        Evaluate if a claim is supported by source text.
        
        Override this in subclasses for specific evaluation logic.
        
        Args:
            claim: The claim to verify
            source_excerpt: Source text that should support the claim
            
        Returns:
            JudgeVerdict with evaluation result
        """
        raise NotImplementedError("Subclasses must implement evaluate()")
    
    def parse_verdict(self, response: str, claim: str, source_excerpt: str) -> JudgeVerdict:
        """
        Parse LLM response into JudgeVerdict.
        
        Args:
            response: Raw LLM response text
            claim: Original claim
            source_excerpt: Original source excerpt
            
        Returns:
            Parsed JudgeVerdict
        """
        # Try to parse structured response
        response_lower = response.lower()
        
        # Determine verdict
        if "supported" in response_lower and "unsupported" not in response_lower:
            verdict = Verdict.SUPPORTED
        elif "unsupported" in response_lower:
            verdict = Verdict.UNSUPPORTED
        elif "partial" in response_lower:
            verdict = Verdict.PARTIAL
        else:
            verdict = Verdict.UNSUPPORTED  # Default to unsupported if unclear
        
        # Extract confidence
        confidence = 0.5  # Default
        import re
        conf_match = re.search(r'confidence[:\s]*([0-9.]+)', response_lower)
        if conf_match:
            try:
                confidence = float(conf_match.group(1))
                confidence = min(1.0, max(0.0, confidence))
            except ValueError:
                pass
        
        # Extract reason
        reason = response[:500] if response else "No reason provided"
        reason_match = re.search(r'reason[:\s]*(.+?)(?:\n|$)', response, re.IGNORECASE)
        if reason_match:
            reason = reason_match.group(1).strip()
        
        return JudgeVerdict(
            verdict=verdict,
            confidence=confidence,
            reason=reason,
            claim=claim,
            source_excerpt=source_excerpt,
        )
