"""
Base classes and interfaces for LLM providers.

This module defines the abstract interface that all LLM providers must implement,
ensuring consistent behavior across different providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional


# =============================================================================
# Enums
# =============================================================================

class ProviderType(Enum):
    """Supported LLM provider types."""
    GEMINI = "gemini"
    NEBIUS = "nebius"
    BEDROCK = "bedrock"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class LLMConfig:
    """
    Provider-agnostic configuration for LLM operations.
    
    Attributes:
        model: Model name (provider uses default if None)
        temperature: Sampling temperature (0.0 - 1.0)
        max_tokens: Maximum tokens to generate
        top_p: Nucleus sampling parameter
        timeout_seconds: Request timeout
        max_retries: Number of retry attempts
        extra: Additional provider-specific options
    """
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 0.95
    timeout_seconds: int = 300
    max_retries: int = 3
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """
    Standardized response from LLM providers.
    
    Attributes:
        content: Generated text content
        prompt_tokens: Number of tokens in the prompt
        completion_tokens: Number of tokens in the completion
        total_tokens: Total tokens used
        model: Model that generated the response
        finish_reason: Why generation stopped (e.g., "stop", "length")
        provider: Name of the provider
        raw_response: Original provider response for debugging
    """
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    finish_reason: Optional[str] = None
    provider: str = ""
    raw_response: Optional[Any] = None


@dataclass
class StreamChunk:
    """
    A single chunk from a streaming response.
    
    Attributes:
        content: Text content of this chunk
        is_final: Whether this is the last chunk
        finish_reason: Why generation stopped (only on final chunk)
    """
    content: str
    is_final: bool = False
    finish_reason: Optional[str] = None


@dataclass
class Message:
    """
    A single message in a conversation.
    
    Attributes:
        role: Message role ("system", "user", or "assistant")
        content: Message content
    """
    role: str
    content: str
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary format for API calls."""
        return {"role": self.role, "content": self.content}


# =============================================================================
# Abstract Base Class
# =============================================================================

class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    All providers must implement:
        - provider_name: Return provider identifier
        - default_model: Return default model name
        - generate(): Generate text from a prompt
        - chat(): Generate text from message history
        - generate_stream(): Stream text from a prompt
        - chat_stream(): Stream text from message history
    """
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'gemini', 'nebius')."""
        pass
    
    @property
    @abstractmethod
    def default_model(self) -> str:
        """Return the default model for this provider."""
        pass
    
    # -------------------------------------------------------------------------
    # Non-Streaming Methods
    # -------------------------------------------------------------------------
    
    @abstractmethod
    async def generate(self, prompt: str, config: Optional[LLMConfig] = None) -> LLMResponse:
        """
        Generate text from a single prompt.
        
        Args:
            prompt: The prompt text
            config: Optional configuration overrides
            
        Returns:
            LLMResponse with generated content
        """
        pass
    
    @abstractmethod
    async def chat(self, messages: List[Message], config: Optional[LLMConfig] = None) -> LLMResponse:
        """
        Generate text from a conversation history.
        
        Args:
            messages: List of Message objects
            config: Optional configuration overrides
            
        Returns:
            LLMResponse with generated content
        """
        pass
    
    # -------------------------------------------------------------------------
    # Streaming Methods
    # -------------------------------------------------------------------------
    
    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None
    ) -> AsyncIterator[StreamChunk]:
        """
        Stream text generation from a prompt.
        
        Args:
            prompt: The prompt text
            config: Optional configuration overrides
            
        Yields:
            StreamChunk objects as they arrive
        """
        pass
    
    @abstractmethod
    async def chat_stream(
        self,
        messages: List[Message],
        config: Optional[LLMConfig] = None
    ) -> AsyncIterator[StreamChunk]:
        """
        Stream text generation from a conversation history.
        
        Args:
            messages: List of Message objects
            config: Optional configuration overrides
            
        Yields:
            StreamChunk objects as they arrive
        """
        pass
    
    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    
    def _merge_config(self, config: Optional[LLMConfig]) -> LLMConfig:
        """Return provided config or create default."""
        return config if config is not None else LLMConfig()
    
    def _validate_messages(self, messages: List[Message]) -> None:
        """
        Validate message list.
        
        Raises:
            ValueError: If messages are invalid
        """
        if not messages:
            raise ValueError("Messages list cannot be empty")
        
        valid_roles = {"system", "user", "assistant"}
        for msg in messages:
            if msg.role not in valid_roles:
                raise ValueError(f"Invalid role '{msg.role}'. Must be one of: {valid_roles}")
