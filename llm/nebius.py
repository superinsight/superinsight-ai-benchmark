"""
Nebius LLM Provider.

Uses Nebius AI's OpenAI-compatible API for text generation with streaming support.
Internally uses streaming for all requests to avoid read timeout issues.
"""

from __future__ import annotations

from typing import Any, AsyncIterator, List, Optional, TYPE_CHECKING

from llm.base import LLMProvider, LLMConfig, LLMResponse, Message, StreamChunk
from environment import Environment

if TYPE_CHECKING:
    from openai import AsyncOpenAI

# =============================================================================
# Module Setup
# =============================================================================

try:
    from openai import AsyncOpenAI as _AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    _AsyncOpenAI = None
    OPENAI_AVAILABLE = False


# =============================================================================
# Provider Implementation
# =============================================================================

class NebiusProvider(LLMProvider):
    """
    Nebius AI LLM provider using OpenAI-compatible API.
    
    Supports both standard and streaming responses.
    Internally uses streaming for all requests to avoid read timeout issues.
    
    Usage:
        provider = NebiusProvider()
        
        # Standard
        response = await provider.generate("Hello!")
        
        # Streaming
        async for chunk in provider.generate_stream("Hello!"):
            print(chunk.content, end="")
    """
    
    # LLMConfig defaults (for detecting if user customized values)
    _CONFIG_DEFAULTS = LLMConfig()
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        models: Optional[List[str]] = None
    ):
        """
        Initialize Nebius provider.
        
        Args:
            api_key: Nebius API key (default: from environment)
            base_url: API base URL (default: from environment)
            models: List of models to try in order on failure (default: from environment)
        """
        if not OPENAI_AVAILABLE:
            raise ImportError("openai required. Install: pip install openai")
        
        self._api_key = api_key or Environment.nebius_api_key
        self._base_url = base_url or Environment.nebius_base_url
        self._models = models or Environment.nebius_models
        self._timeout = Environment.nebius_timeout
        self._client: Optional[AsyncOpenAI] = None
        
        if not self._api_key:
            raise ValueError("NEBIUS_API_KEY required. Set environment variable or pass api_key.")
        if not self._models:
            raise ValueError("NEBIUS_MODEL required. Set environment variable or pass models.")
    
    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------
    
    @property
    def provider_name(self) -> str:
        return "nebius"
    
    @property
    def default_model(self) -> str:
        return self._models[0] if self._models else ""
    
    @property
    def client(self) -> AsyncOpenAI:
        """Lazily initialize async OpenAI client with timeout."""
        if self._client is None:
            self._client = _AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                timeout=self._timeout,  # Set timeout at client level for proper httpx configuration
            )
        return self._client
    
    # -------------------------------------------------------------------------
    # Non-Streaming Methods (internally uses streaming to avoid read timeout)
    # -------------------------------------------------------------------------
    
    async def generate(self, prompt: str, config: Optional[LLMConfig] = None) -> LLMResponse:
        """Generate text from a prompt."""
        return await self.chat([Message(role="user", content=prompt)], config)
    
    async def chat(self, messages: List[Message], config: Optional[LLMConfig] = None) -> LLMResponse:
        """
        Generate text from conversation history with model fallback on failure.
        
        Internally uses streaming to avoid read timeout issues while maintaining
        the same external API (returns LLMResponse).
        """
        self._validate_messages(messages)
        cfg = self._apply_defaults(self._merge_config(config))
        
        # Truncate input if exceeds max input tokens
        messages = self._truncate_messages_to_fit(messages, Environment.nebius_max_input_tokens)
        
        # Cap max_tokens to available context space
        effective_max_tokens = self._calculate_effective_max_tokens(messages, cfg.max_tokens)
        
        # Determine which models to try
        if cfg.model:
            # If specific model requested in config, only try that
            models_to_try = [cfg.model]
        else:
            # Otherwise use the fallback list
            models_to_try = self._models
        
        last_error = None
        
        for i, model in enumerate(models_to_try):
            try:
                # Use streaming internally to avoid read timeout
                stream = await self.client.chat.completions.create(
                    model=model,
                    messages=[msg.to_dict() for msg in messages],
                    temperature=cfg.temperature,
                    max_tokens=effective_max_tokens,
                    top_p=cfg.top_p,
                    stream=True,  # Use streaming to keep connection alive
                    stream_options={"include_usage": True},  # Request usage info
                )
                
                # Collect all chunks
                content_parts = []
                finish_reason = None
                usage_info = None
                
                async for chunk in stream:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if delta and delta.content:
                            content_parts.append(delta.content)
                        if chunk.choices[0].finish_reason:
                            finish_reason = chunk.choices[0].finish_reason
                    
                    # Capture usage info if available (usually in the last chunk)
                    if hasattr(chunk, 'usage') and chunk.usage:
                        usage_info = chunk.usage
                
                if i > 0:
                    print(f"   ✅ Nebius: Succeeded with fallback model {i+1}/{len(models_to_try)}: {model}")
                
                # Return LLMResponse (same as before, API unchanged)
                return LLMResponse(
                    content="".join(content_parts),
                    prompt_tokens=usage_info.prompt_tokens if usage_info else 0,
                    completion_tokens=usage_info.completion_tokens if usage_info else 0,
                    total_tokens=usage_info.total_tokens if usage_info else 0,
                    model=model,
                    finish_reason=finish_reason,
                    provider=self.provider_name,
                    raw_response=None,
                )
                
            except Exception as e:
                last_error = e
                if i < len(models_to_try) - 1:
                    print(f"   ⚠️  Nebius: Model {model} failed ({e}), trying next model...")
                else:
                    print(f"   ❌ Nebius: All {len(models_to_try)} models failed")
        
        # All models failed
        raise last_error
    
    # -------------------------------------------------------------------------
    # Streaming Methods
    # -------------------------------------------------------------------------
    
    async def generate_stream(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None
    ) -> AsyncIterator[StreamChunk]:
        """Stream text generation from a prompt."""
        async for chunk in self.chat_stream([Message(role="user", content=prompt)], config):
            yield chunk
    
    async def chat_stream(
        self,
        messages: List[Message],
        config: Optional[LLMConfig] = None
    ) -> AsyncIterator[StreamChunk]:
        """Stream text generation from conversation history with model fallback."""
        self._validate_messages(messages)
        cfg = self._apply_defaults(self._merge_config(config))
        
        # Truncate input if exceeds max input tokens
        messages = self._truncate_messages_to_fit(messages, Environment.nebius_max_input_tokens)
        
        # Cap max_tokens to available context space
        effective_max_tokens = self._calculate_effective_max_tokens(messages, cfg.max_tokens)
        
        # Determine which models to try
        if cfg.model:
            models_to_try = [cfg.model]
        else:
            models_to_try = self._models
        
        last_error = None
        
        for i, model in enumerate(models_to_try):
            try:
                stream = await self.client.chat.completions.create(
                    model=model,
                    messages=[msg.to_dict() for msg in messages],
                    temperature=cfg.temperature,
                    max_tokens=effective_max_tokens,
                    top_p=cfg.top_p,
                    stream=True,
                )
                
                if i > 0:
                    print(f"   ✅ Nebius: Streaming with fallback model {i+1}/{len(models_to_try)}: {model}")
                
                async for chunk in stream:
                    # Extract content from delta
                    content = ""
                    finish_reason = None
                    
                    if chunk.choices:
                        choice = chunk.choices[0]
                        if choice.delta and choice.delta.content:
                            content = choice.delta.content
                        finish_reason = choice.finish_reason
                    
                    yield StreamChunk(
                        content=content,
                        is_final=finish_reason is not None,
                        finish_reason=finish_reason,
                    )
                
                # Successfully completed streaming
                return
                
            except Exception as e:
                last_error = e
                if i < len(models_to_try) - 1:
                    print(f"   ⚠️  Nebius: Model {model} failed ({e}), trying next model...")
                else:
                    print(f"   ❌ Nebius: All {len(models_to_try)} models failed")
        
        # All models failed
        raise last_error
    
    # -------------------------------------------------------------------------
    # Private Methods
    # -------------------------------------------------------------------------
    
    def _apply_defaults(self, config: LLMConfig) -> LLMConfig:
        """
        Apply Nebius-specific defaults from environment.
        
        Only overrides values that are at the generic LLMConfig defaults,
        allowing users to explicitly set custom values.
        """
        if config.temperature == self._CONFIG_DEFAULTS.temperature:
            config.temperature = Environment.nebius_temperature
        if config.max_tokens == self._CONFIG_DEFAULTS.max_tokens:
            config.max_tokens = Environment.nebius_max_tokens
        if config.timeout_seconds == self._CONFIG_DEFAULTS.timeout_seconds:
            config.timeout_seconds = Environment.nebius_timeout
        return config
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (~3 chars per token is conservative for most models)."""
        return len(text) // 3
    
    def _truncate_messages_to_fit(self, messages: List[Message], max_input_tokens: int) -> List[Message]:
        """
        Truncate message content to fit within max input tokens.
        Preserves system messages and truncates user/assistant content from the end.
        
        Args:
            messages: List of messages
            max_input_tokens: Maximum allowed input tokens
            
        Returns:
            Truncated messages list
        """
        total_tokens = sum(self._estimate_tokens(msg.content) for msg in messages)
        
        if total_tokens <= max_input_tokens:
            return messages
        
        # Need to truncate
        tokens_to_remove = total_tokens - max_input_tokens
        print(f"   ⚠️  Nebius: Input too large (~{total_tokens:,} tokens), truncating to ~{max_input_tokens:,} tokens")
        
        # Convert to chars (multiply by 3 to be safe)
        chars_to_remove = tokens_to_remove * 3
        
        # Work through non-system messages to truncate content
        truncated_messages = []
        for msg in messages:
            if msg.role == "system":
                # Preserve system messages fully
                truncated_messages.append(msg)
            else:
                content = msg.content
                if chars_to_remove > 0 and len(content) > 1000:
                    # Truncate this message's content from the end
                    truncate_amount = min(chars_to_remove, len(content) - 500)  # Keep at least 500 chars
                    content = content[:len(content) - truncate_amount] + "\n\n[... content truncated due to length ...]"
                    chars_to_remove -= truncate_amount
                truncated_messages.append(Message(role=msg.role, content=content))
        
        return truncated_messages
    
    def _calculate_effective_max_tokens(self, messages: List[Message], requested_max_tokens: int) -> int:
        """
        Calculate effective max_tokens based on available context space.
        
        Args:
            messages: List of messages (after any truncation)
            requested_max_tokens: The requested max_tokens from config
            
        Returns:
            Capped max_tokens that fits within context limit
        """
        input_text = "".join(msg.content for msg in messages)
        estimated_input = self._estimate_tokens(input_text)
        
        # Calculate available tokens (with 100 token safety margin)
        available = Environment.nebius_context_limit - estimated_input - 100
        effective_max_tokens = min(requested_max_tokens, max(1000, available))
        
        if effective_max_tokens < requested_max_tokens:
            print(f"   ⚠️  Nebius: Capping max_tokens {requested_max_tokens:,} → {effective_max_tokens:,} (input ~{estimated_input:,} tokens)")
        
        return effective_max_tokens
    
    def _parse_response(self, response: Any, model: str) -> LLMResponse:
        """Parse OpenAI response to standard format."""
        choice = response.choices[0] if response.choices else None
        usage = response.usage
        
        return LLMResponse(
            content=choice.message.content if choice else "",
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
            model=model,
            finish_reason=choice.finish_reason if choice else None,
            provider=self.provider_name,
            raw_response=response,
        )
