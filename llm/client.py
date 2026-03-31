"""
LLM Client - High-level interface for LLM operations.

Provides a unified interface that works with any LLM provider,
including support for streaming responses and request/response logging.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime
from typing import Any, AsyncIterator, List, Optional, Union

from llm.base import LLMProvider, LLMConfig, LLMResponse, Message, ProviderType, StreamChunk
from environment import Environment


class LLMClient:
    """
    High-level LLM client with provider abstraction.
    
    Supports both standard and streaming responses.
    Automatically logs all LLM requests/responses to JSON files.
    
    Usage:
        # Standard generation
        client = LLMClient()
        response = await client.generate("Hello!")
        print(response.content)
        
        # With custom logs directory
        client = LLMClient(logs_dir="/path/to/logs")
        
        # Streaming generation
        async for chunk in client.generate_stream("Hello!"):
            print(chunk.content, end="", flush=True)
    """
    
    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        config: Optional[LLMConfig] = None,
        logs_dir: Optional[str] = None
    ):
        """
        Initialize the LLM client.
        
        Args:
            provider: LLM provider instance (auto-detected if not provided)
            config: Default configuration for all requests
            logs_dir: Directory for LLM logs (auto-created temp dir if None)
        """
        self._provider = provider
        self._config = config or LLMConfig()
        self._call_count = 0
        
        # Setup logs directory
        if logs_dir:
            self._logs_dir = logs_dir
        else:
            self._logs_dir = tempfile.mkdtemp(prefix="llm-logs-")
        os.makedirs(self._logs_dir, exist_ok=True)
        print(f"   📁 LLM logs directory: {self._logs_dir}")
    
    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------
    
    @property
    def provider(self) -> LLMProvider:
        """Get or create the LLM provider."""
        if self._provider is None:
            self._provider = self._create_default_provider()
        return self._provider
    
    @property
    def provider_name(self) -> str:
        """Get the current provider name."""
        return self.provider.provider_name
    
    @property
    def logs_dir(self) -> str:
        """Get the logs directory path."""
        return self._logs_dir
    
    @property
    def call_count(self) -> int:
        """Get the number of LLM calls made."""
        return self._call_count
    
    # -------------------------------------------------------------------------
    # Factory Method
    # -------------------------------------------------------------------------
    
    @classmethod
    def create(
        cls,
        provider_type: Union[str, ProviderType, None] = None,
        model: Optional[str] = None,
        config: Optional[LLMConfig] = None,
        logs_dir: Optional[str] = None,
        **provider_kwargs
    ) -> LLMClient:
        """
        Create LLMClient with specific provider.
        
        Args:
            provider_type: "gemini" or "nebius" (uses env default if None)
            model: Model name (uses provider default if None)
            config: Default LLM configuration
            logs_dir: Directory for LLM logs
            **provider_kwargs: Provider-specific arguments
            
        Returns:
            Configured LLMClient instance
        """
        # Resolve provider type
        if provider_type is None:
            provider_type = Environment.llm_default_provider
        if isinstance(provider_type, str):
            provider_type = ProviderType(provider_type.lower())
        
        # Create provider
        provider = cls._create_provider(provider_type, model, **provider_kwargs)
        return cls(provider=provider, config=config, logs_dir=logs_dir)
    
    # -------------------------------------------------------------------------
    # Non-Streaming Methods
    # -------------------------------------------------------------------------
    
    async def generate(self, prompt: str, config: Optional[LLMConfig] = None) -> LLMResponse:
        """
        Generate text from a prompt.
        
        Args:
            prompt: The prompt text
            config: Optional configuration overrides
            
        Returns:
            LLMResponse with generated content
        """
        start_time = time.perf_counter()
        response = await self.provider.generate(prompt, self._effective_config(config))
        duration = time.perf_counter() - start_time
        self._log_call(prompt=prompt, response=response, duration=duration)
        return response
    
    async def chat(self, messages: List[Message], config: Optional[LLMConfig] = None) -> LLMResponse:
        """
        Generate text from conversation history.
        
        Args:
            messages: List of Message objects
            config: Optional configuration overrides
            
        Returns:
            LLMResponse with generated content
        """
        start_time = time.perf_counter()
        response = await self.provider.chat(messages, self._effective_config(config))
        duration = time.perf_counter() - start_time
        # Convert messages to string for logging
        prompt = "\n".join([f"[{m.role}]: {m.content}" for m in messages])
        self._log_call(prompt=prompt, response=response, messages=messages, duration=duration)
        return response
    
    # -------------------------------------------------------------------------
    # Streaming Methods
    # -------------------------------------------------------------------------
    
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
            
        Example:
            async for chunk in client.generate_stream("Tell me a story"):
                print(chunk.content, end="", flush=True)
        """
        start_time = time.perf_counter()
        full_content = ""
        finish_reason = None
        
        async for chunk in self.provider.generate_stream(prompt, self._effective_config(config)):
            if chunk.content:
                full_content += chunk.content
            if chunk.finish_reason:
                finish_reason = chunk.finish_reason
            yield chunk
        
        # Log after streaming completes
        duration = time.perf_counter() - start_time
        response = LLMResponse(
            content=full_content,
            provider=self.provider.provider_name,
            model=self._effective_config(config).model or self.provider.default_model,
            finish_reason=finish_reason,
            prompt_tokens=0,  # Not available in streaming
            completion_tokens=0,
            total_tokens=0,
        )
        self._log_call(prompt=prompt, response=response, duration=duration)
    
    async def chat_stream(
        self,
        messages: List[Message],
        config: Optional[LLMConfig] = None
    ) -> AsyncIterator[StreamChunk]:
        """
        Stream text generation from conversation history.
        
        Args:
            messages: List of Message objects
            config: Optional configuration overrides
            
        Yields:
            StreamChunk objects as they arrive
            
        Example:
            messages = [Message(role="user", content="Hello!")]
            async for chunk in client.chat_stream(messages):
                print(chunk.content, end="", flush=True)
        """
        start_time = time.perf_counter()
        full_content = ""
        finish_reason = None
        
        async for chunk in self.provider.chat_stream(messages, self._effective_config(config)):
            if chunk.content:
                full_content += chunk.content
            if chunk.finish_reason:
                finish_reason = chunk.finish_reason
            yield chunk
        
        # Log after streaming completes
        duration = time.perf_counter() - start_time
        prompt = "\n".join([f"[{m.role}]: {m.content}" for m in messages])
        response = LLMResponse(
            content=full_content,
            provider=self.provider.provider_name,
            model=self._effective_config(config).model or self.provider.default_model,
            finish_reason=finish_reason,
            prompt_tokens=0,  # Not available in streaming
            completion_tokens=0,
            total_tokens=0,
        )
        self._log_call(prompt=prompt, response=response, messages=messages, duration=duration)
    
    # -------------------------------------------------------------------------
    # Logging Methods
    # -------------------------------------------------------------------------
    
    def _log_call(
        self,
        prompt: str,
        response: LLMResponse,
        messages: Optional[List[Message]] = None,
        duration: Optional[float] = None
    ) -> str:
        """
        Log an LLM request/response to a JSON file.
        
        Args:
            prompt: The prompt or formatted messages
            response: The LLMResponse object
            messages: Optional original messages (for chat calls)
            duration: Optional duration in seconds
            
        Returns:
            Path to the saved log file
        """
        self._call_count += 1
        
        # Calculate tokens per second
        tokens_per_second = None
        if duration and duration > 0 and response.completion_tokens > 0:
            tokens_per_second = round(response.completion_tokens / duration, 2)
        
        # Build log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "call_number": self._call_count,
            "provider": response.provider,
            "model": response.model,
            "request": {
                "prompt": prompt,
                "prompt_length": len(prompt),
            },
            "response": {
                "content": response.content,
                "content_length": len(response.content),
                "finish_reason": response.finish_reason,
            },
            "tokens": {
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens,
                "total_tokens": response.total_tokens,
            },
            "performance": {
                "duration_seconds": round(duration, 3) if duration else None,
                "tokens_per_second": tokens_per_second,
            },
        }
        
        
        # Add messages if provided
        if messages:
            log_entry["request"]["messages"] = [m.to_dict() for m in messages]
        
        # Generate filename
        filename = f"{self._call_count:04d}_{response.provider}.json"
        filepath = os.path.join(self._logs_dir, filename)
        
        # Write to file
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(log_entry, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"   ⚠️  Warning: Failed to save LLM log: {e}")
            return ""
        
        return filepath
    
    # -------------------------------------------------------------------------
    # Private Methods
    # -------------------------------------------------------------------------
    
    @staticmethod
    def _create_provider(
        provider_type: ProviderType,
        model: Optional[str] = None,
        **kwargs
    ) -> LLMProvider:
        """Create provider instance by type."""
        if provider_type == ProviderType.GEMINI:
            from llm.gemini import GeminiProvider
            return GeminiProvider(model=model, **kwargs)
        
        if provider_type == ProviderType.NEBIUS:
            from llm.nebius import NebiusProvider
            return NebiusProvider(model=model, **kwargs)
        
        if provider_type == ProviderType.BEDROCK:
            from llm.bedrock import BedrockProvider
            return BedrockProvider(model=model, **kwargs)
        
        raise ValueError(f"Unknown provider type: {provider_type}")
    
    def _create_default_provider(self) -> LLMProvider:
        """Create provider based on environment configuration."""
        
        # Check for multi-provider configuration first
        if Environment.llm_multi_providers:
            return self._create_multi_provider()
        
        default = Environment.llm_default_provider.lower()
        
        # Try configured default first
        provider = self._try_create_provider(default)
        if provider:
            return provider
        
        # Fallback: try all available providers
        for provider_name in ["gemini", "nebius", "bedrock"]:
            if provider_name != default:
                provider = self._try_create_provider(provider_name)
                if provider:
                    return provider
        
        raise RuntimeError(
            "No LLM provider configured. Set one of:\n"
            "  - GCP_PROJECT_ID (for Gemini)\n"
            "  - NEBIUS_API_KEY (for Nebius)\n"
            "  - AWS credentials (for Bedrock)\n"
            "  - LLM_MULTI_PROVIDERS (for multi-provider distribution)"
        )
    
    def _create_multi_provider(self) -> LLMProvider:
        """Create multi-provider from environment configuration."""
        from llm.multi import MultiProvider, DistributionStrategy
        
        provider_names = Environment.llm_multi_providers
        strategy_str = Environment.llm_multi_strategy
        
        print(f"   🔀 Creating MultiProvider: {', '.join(provider_names)} ({strategy_str})")
        
        # Create individual providers
        providers = []
        for name in provider_names:
            provider = self._try_create_provider(name.lower())
            if provider:
                providers.append(provider)
                print(f"      ✓ {name} provider initialized")
            else:
                print(f"      ✗ {name} provider failed to initialize (skipped)")
        
        if not providers:
            raise RuntimeError(
                f"No providers could be initialized from: {provider_names}\n"
                "Check that required credentials are set for each provider."
            )
        
        # Parse strategy
        try:
            strategy = DistributionStrategy(strategy_str.lower())
        except ValueError:
            print(f"   ⚠️  Unknown strategy '{strategy_str}', using round_robin")
            strategy = DistributionStrategy.ROUND_ROBIN
        
        return MultiProvider(providers=providers, strategy=strategy)
    
    def _try_create_provider(self, provider_name: str) -> Optional[LLMProvider]:
        """Try to create a provider, return None if not configured."""
        try:
            if provider_name == "gemini" and Environment.gcp_project_id:
                from llm.gemini import GeminiProvider
                return GeminiProvider()
            if provider_name == "nebius" and Environment.nebius_api_key:
                from llm.nebius import NebiusProvider
                return NebiusProvider()
            if provider_name == "bedrock" and Environment.bedrock_models:
                from llm.bedrock import BedrockProvider
                return BedrockProvider()
        except ImportError as e:
            print(f"   ⚠️  {provider_name} provider unavailable - missing dependency: {e}")
        except Exception as e:
            print(f"   ⚠️  Failed to create {provider_name} provider: {e}")
        return None
    
    def _effective_config(self, config: Optional[LLMConfig]) -> LLMConfig:
        """Merge provided config with defaults."""
        if config is None:
            return self._config
        
        return LLMConfig(
            model=config.model or self._config.model,
            temperature=self._pick(config.temperature, self._config.temperature, 0.7),
            max_tokens=self._pick(config.max_tokens, self._config.max_tokens, 4096),
            top_p=self._pick(config.top_p, self._config.top_p, 0.95),
            timeout_seconds=self._pick(config.timeout_seconds, self._config.timeout_seconds, 300),
            max_retries=self._pick(config.max_retries, self._config.max_retries, 3),
            extra={**self._config.extra, **config.extra}
        )
    
    @staticmethod
    def _pick(value: Any, fallback: Any, default: Any) -> Any:
        """Pick non-default value, preferring the first argument."""
        return fallback if value == default else value
