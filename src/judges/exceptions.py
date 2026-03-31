"""
Custom exceptions for benchmark judges.

This module defines specific exception types to enable:
- Better error handling and debugging
- Distinguishing retryable vs non-retryable errors
- More informative error messages
"""


class BenchmarkError(Exception):
    """
    Base exception for all benchmark errors.
    
    All custom exceptions inherit from this class.
    """
    pass


class APIError(BenchmarkError):
    """
    Error communicating with LLM API.
    
    This is typically a retryable error (timeout, rate limit, connection error).
    
    Examples:
    - API timeout
    - Rate limit exceeded  
    - Network connection error
    - Service unavailable
    """
    def __init__(self, message: str, retryable: bool = True, original_error: Exception = None):
        super().__init__(message)
        self.retryable = retryable
        self.original_error = original_error


class ParsingError(BenchmarkError):
    """
    Error parsing LLM response or input data.
    
    This is typically NOT retryable - the response format is invalid.
    
    Examples:
    - Invalid JSON in response
    - Missing required fields in JSON
    - Unexpected response format
    """
    def __init__(self, message: str, raw_content: str = "", original_error: Exception = None):
        super().__init__(message)
        self.raw_content = raw_content[:500] if raw_content else ""  # Truncate for safety
        self.original_error = original_error


class SourceLookupError(BenchmarkError):
    """
    Error looking up source text for verification.
    
    Examples:
    - Citation not found in source index
    - Source file not accessible
    - Invalid citation format
    """
    def __init__(self, message: str, citation: dict = None):
        super().__init__(message)
        self.citation = citation or {}


class TokenLimitError(BenchmarkError):
    """
    Error due to token/context window limits.
    
    Examples:
    - Input too long for model context window
    - Output truncated due to max_tokens limit
    - Combined prompt + response exceeds limit
    """
    def __init__(
        self, 
        message: str, 
        requested_tokens: int = 0, 
        max_tokens: int = 0,
        truncated: bool = False,
    ):
        super().__init__(message)
        self.requested_tokens = requested_tokens
        self.max_tokens = max_tokens
        self.truncated = truncated


class ClaimExtractionError(BenchmarkError):
    """
    Error extracting claims from output.
    
    Examples:
    - No claims found in output
    - Invalid output format
    - Regex pattern matching failure
    """
    def __init__(self, message: str, output_snippet: str = ""):
        super().__init__(message)
        self.output_snippet = output_snippet[:200] if output_snippet else ""


class ContractValidationError(BenchmarkError):
    """
    Error validating against benchmark contract.
    
    Examples:
    - Missing required fields in contract
    - Invalid contract format
    - Incompatible contract version
    """
    def __init__(self, message: str, contract_field: str = ""):
        super().__init__(message)
        self.contract_field = contract_field
