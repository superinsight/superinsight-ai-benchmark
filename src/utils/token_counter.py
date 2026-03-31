"""
Token counting utilities for input/output limit management.

Provides two methods:
1. Local approximation using tiktoken (fast, free)
2. Character-based estimation (fastest, rougher)

Note: For exact Gemini token counts, use the Vertex AI count_tokens API,
but for benchmark purposes the local approximation is sufficient.
"""

import os
from typing import Optional


# Token limits by model
MODEL_LIMITS = {
    # Gemini models
    "gemini-2.0-flash": {"input": 1_000_000, "output": 8_192},
    "gemini-2.0-flash-exp": {"input": 1_000_000, "output": 8_192},
    "gemini-2.5-pro": {"input": 1_000_000, "output": 65_536},
    "gemini-2.5-flash": {"input": 1_000_000, "output": 65_536},
    # Nebius/DeepSeek models
    "deepseek-ai/DeepSeek-V3": {"input": 64_000, "output": 8_192},
    "Qwen/Qwen3-235B-A22B": {"input": 131_072, "output": 8_192},
}

# Default limits
DEFAULT_INPUT_TOKENS = 100_000
DEFAULT_OUTPUT_TOKENS = 8_192


def count_tokens_tiktoken(text: str, encoding: str = "cl100k_base") -> int:
    """
    Count tokens using tiktoken (GPT-4 compatible tokenizer).
    
    This provides a good approximation for Gemini tokens.
    Actual Gemini tokens may differ slightly.
    
    Args:
        text: Text to count tokens for
        encoding: Tiktoken encoding name (default: cl100k_base for GPT-4)
        
    Returns:
        Estimated token count
    """
    if not text:
        return 0
    
    try:
        import tiktoken
        enc = tiktoken.get_encoding(encoding)
        return len(enc.encode(text))
    except ImportError:
        # Fallback to character-based estimation
        return estimate_tokens_from_chars(text)


def estimate_tokens_from_chars(text: str, chars_per_token: float = 4.0) -> int:
    """
    Estimate tokens from character count.
    
    Rule of thumb: 1 token ≈ 4 characters for English text.
    This is the fastest method but least accurate.
    
    Args:
        text: Text to estimate tokens for
        chars_per_token: Characters per token ratio (default: 4.0)
        
    Returns:
        Estimated token count
    """
    if not text:
        return 0
    return int(len(text) / chars_per_token)


def get_model_limits(model: str) -> dict:
    """
    Get token limits for a model.
    
    Args:
        model: Model name
        
    Returns:
        Dict with 'input' and 'output' token limits
    """
    # Check exact match first
    if model in MODEL_LIMITS:
        return MODEL_LIMITS[model]
    
    # Check partial match
    for model_name, limits in MODEL_LIMITS.items():
        if model_name in model or model in model_name:
            return limits
    
    # Return defaults
    return {"input": DEFAULT_INPUT_TOKENS, "output": DEFAULT_OUTPUT_TOKENS}


def truncate_to_token_limit(
    text: str,
    max_tokens: int,
    method: str = "tiktoken",
) -> str:
    """
    Truncate text to fit within token limit.
    
    Args:
        text: Text to truncate
        max_tokens: Maximum tokens allowed
        method: Counting method ('tiktoken' or 'chars')
        
    Returns:
        Truncated text that fits within limit
    """
    if not text:
        return text
    
    # Count current tokens
    if method == "tiktoken":
        current_tokens = count_tokens_tiktoken(text)
    else:
        current_tokens = estimate_tokens_from_chars(text)
    
    if current_tokens <= max_tokens:
        return text
    
    # Binary search for the right truncation point
    # Estimate characters to keep based on ratio
    ratio = max_tokens / current_tokens
    estimated_chars = int(len(text) * ratio * 0.95)  # 5% safety margin
    
    # Truncate and verify
    truncated = text[:estimated_chars]
    
    # Add truncation marker
    truncated = truncated.rstrip() + "\n... (truncated to fit token limit)"
    
    return truncated


def validate_input_size(
    text: str,
    model: str,
    raise_on_exceed: bool = False,
) -> dict:
    """
    Validate if input text is within model limits.
    
    Args:
        text: Input text to validate
        model: Model name
        raise_on_exceed: If True, raise ValueError when limit exceeded
        
    Returns:
        Dict with validation results:
        - 'valid': bool
        - 'tokens': int (estimated)
        - 'limit': int
        - 'ratio': float (tokens/limit)
    """
    tokens = count_tokens_tiktoken(text)
    limits = get_model_limits(model)
    input_limit = limits["input"]
    
    valid = tokens <= input_limit
    ratio = tokens / input_limit
    
    result = {
        "valid": valid,
        "tokens": tokens,
        "limit": input_limit,
        "ratio": ratio,
        "exceeded_by": max(0, tokens - input_limit),
    }
    
    if not valid and raise_on_exceed:
        raise ValueError(
            f"Input exceeds model limit: {tokens:,} tokens > {input_limit:,} limit "
            f"({ratio:.1%} of limit)"
        )
    
    return result


class TokenBudget:
    """
    Manage token budget for multi-part prompts.
    
    Useful for batch prompts where you need to fit multiple items
    within the model's input limit.
    
    Example:
        budget = TokenBudget(model="gemini-2.0-flash", reserve_output=2000)
        
        # Add fixed parts
        budget.add("system_prompt", system_prompt)
        budget.add("instructions", instructions)
        
        # Check remaining budget
        remaining = budget.remaining_tokens()
        
        # Truncate variable content to fit
        source_text = budget.truncate_to_fit(source_text, "source")
    """
    
    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        reserve_output: int = 2000,
        safety_margin: float = 0.95,
    ):
        """
        Initialize token budget.
        
        Args:
            model: Model name for limits
            reserve_output: Tokens to reserve for output
            safety_margin: Safety margin (0.95 = use 95% of limit)
        """
        limits = get_model_limits(model)
        self.total_budget = int(limits["input"] * safety_margin) - reserve_output
        self.used_tokens = 0
        self.parts: dict = {}
    
    def add(self, name: str, text: str) -> int:
        """
        Add a part to the budget.
        
        Args:
            name: Name of the part (for tracking)
            text: Text content
            
        Returns:
            Tokens used by this part
        """
        tokens = count_tokens_tiktoken(text)
        self.parts[name] = tokens
        self.used_tokens += tokens
        return tokens
    
    def remaining_tokens(self) -> int:
        """Get remaining token budget."""
        return max(0, self.total_budget - self.used_tokens)
    
    def truncate_to_fit(self, text: str, name: str = "content") -> str:
        """
        Truncate text to fit remaining budget.
        
        Args:
            text: Text to truncate
            name: Name for tracking
            
        Returns:
            Truncated text
        """
        remaining = self.remaining_tokens()
        truncated = truncate_to_token_limit(text, remaining)
        self.add(name, truncated)
        return truncated
    
    def summary(self) -> dict:
        """Get budget summary."""
        return {
            "total_budget": self.total_budget,
            "used_tokens": self.used_tokens,
            "remaining_tokens": self.remaining_tokens(),
            "parts": self.parts,
            "utilization": self.used_tokens / self.total_budget if self.total_budget > 0 else 0,
        }
