"""
LLM Package - Provider-based abstraction for LLM operations.

This package provides a unified interface for working with different LLM providers
(Google Gemini, Nebius, AWS Bedrock) through a common abstraction layer.

Supports both standard and streaming responses.

Quick Start:
    >>> from llm import LLMClient
    >>> 
    >>> client = LLMClient()
    >>> response = await client.generate("Hello, world!")
    >>> print(response.content)

Streaming:
    >>> async for chunk in client.generate_stream("Tell me a story"):
    ...     print(chunk.content, end="", flush=True)

With specific provider:
    >>> from llm import LLMClient, GeminiProvider
    >>> 
    >>> provider = GeminiProvider(project_id="my-project")
    >>> client = LLMClient(provider=provider)

Using factory method:
    >>> client = LLMClient.create(provider_type="bedrock", model="anthropic.claude-3-5-sonnet-20241022-v2:0")
"""

from llm.base import (
    LLMProvider,
    LLMConfig,
    LLMResponse,
    Message,
    ProviderType,
    StreamChunk,
)
from llm.client import LLMClient
from llm.gemini import GeminiProvider
from llm.nebius import NebiusProvider
from llm.bedrock import BedrockProvider
from llm.multi import MultiProvider, DistributionStrategy, create_multi_provider

__all__ = [
    # Core classes
    "LLMClient",
    "LLMProvider",
    "LLMConfig",
    "LLMResponse",
    "Message",
    "ProviderType",
    "StreamChunk",
    # Providers
    "GeminiProvider",
    "NebiusProvider",
    "BedrockProvider",
    # Multi-Provider
    "MultiProvider",
    "DistributionStrategy",
    "create_multi_provider",
]
