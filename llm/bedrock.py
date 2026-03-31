"""
AWS Bedrock LLM Provider.

Uses AWS Bedrock's Converse API for text generation with streaming support.
Supports Claude, Llama, and other models available on Bedrock.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Dict, List, Optional, TYPE_CHECKING

from llm.base import LLMProvider, LLMConfig, LLMResponse, Message, StreamChunk
from environment import Environment

if TYPE_CHECKING:
    from mypy_boto3_bedrock_runtime import BedrockRuntimeClient

# =============================================================================
# Module Setup
# =============================================================================

try:
    import boto3
    from botocore.config import Config as BotoConfig
    BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None
    BotoConfig = None
    BOTO3_AVAILABLE = False


# =============================================================================
# Provider Implementation
# =============================================================================

class BedrockProvider(LLMProvider):
    """
    AWS Bedrock LLM provider using Converse API.
    
    Supports both standard and streaming responses.
    Uses asyncio.to_thread for async operations since boto3 is synchronous.
    
    Usage:
        provider = BedrockProvider()
        
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
        region: Optional[str] = None,
        model: Optional[str] = None,
        models: Optional[List[str]] = None
    ):
        """
        Initialize Bedrock provider.
        
        Args:
            region: AWS region (default: from environment)
            model: Single model ID (convenience parameter, added to models list)
            models: List of model IDs to try in order on failure (default: from environment)
        """
        if not BOTO3_AVAILABLE:
            raise ImportError("boto3 required. Install: pip install boto3")
        
        self._region = region or Environment.bedrock_region
        
        # Handle model parameter - if single model provided, use it; otherwise use models list
        if model:
            self._models = [model]
        elif models:
            self._models = models
        else:
            self._models = Environment.bedrock_models
        
        self._timeout = Environment.bedrock_timeout
        self._client: Optional[BedrockRuntimeClient] = None
        
        if not self._models:
            raise ValueError("BEDROCK_MODELS required. Set environment variable or pass models.")
    
    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------
    
    @property
    def provider_name(self) -> str:
        return "bedrock"
    
    @property
    def default_model(self) -> str:
        return self._models[0] if self._models else ""
    
    @property
    def client(self) -> BedrockRuntimeClient:
        """Lazily initialize Bedrock runtime client with timeout."""
        if self._client is None:
            boto_config = BotoConfig(
                read_timeout=self._timeout,
                connect_timeout=60,
                retries={'max_attempts': 3, 'mode': 'standard'}
            )
            self._client = boto3.client(
                'bedrock-runtime',
                region_name=self._region,
                config=boto_config
            )
        return self._client
    
    # -------------------------------------------------------------------------
    # Rate Limit Handling
    # -------------------------------------------------------------------------
    
    async def _with_throttle_retry(self, sync_func, max_retries: int = 5):
        """
        Execute sync function with exponential backoff retry for throttling errors.
        
        Args:
            sync_func: Synchronous function to execute
            max_retries: Maximum retry attempts for throttling errors
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return await asyncio.to_thread(sync_func)
            except Exception as e:
                error_str = str(e).lower()
                # Check for throttling/rate limit errors
                if "throttl" in error_str or "rate" in error_str or "too many" in error_str:
                    last_error = e
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        print(f"   ⏳ Bedrock throttled, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})...")
                        await asyncio.sleep(wait_time)
                    continue
                # Non-throttling error, re-raise immediately
                raise
        
        # All retries exhausted
        raise last_error
    
    # -------------------------------------------------------------------------
    # Message Conversion
    # -------------------------------------------------------------------------
    
    def _convert_messages(self, messages: List[Message]) -> tuple[Optional[str], List[Dict[str, Any]]]:
        """
        Convert Message objects to Bedrock Converse API format.
        
        Returns:
            Tuple of (system_prompt, conversation_messages)
        """
        system_prompt = None
        conversation = []
        
        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            elif msg.role in ["user", "assistant"]:
                conversation.append({
                    "role": msg.role,
                    "content": [{"text": msg.content}]
                })
        
        return system_prompt, conversation
    
    # -------------------------------------------------------------------------
    # Non-Streaming Methods
    # -------------------------------------------------------------------------
    
    async def generate(self, prompt: str, config: Optional[LLMConfig] = None) -> LLMResponse:
        """Generate text from a prompt."""
        return await self.chat([Message(role="user", content=prompt)], config)
    
    async def chat(self, messages: List[Message], config: Optional[LLMConfig] = None) -> LLMResponse:
        """
        Generate text from conversation history with model fallback on failure.
        """
        self._validate_messages(messages)
        cfg = self._apply_defaults(self._merge_config(config))
        
        # Determine which models to try
        if cfg.model:
            models_to_try = [cfg.model]
        else:
            models_to_try = self._models
        
        system_prompt, conversation = self._convert_messages(messages)
        last_error = None
        
        for i, model in enumerate(models_to_try):
            try:
                def make_request():
                    request_params = {
                        "modelId": model,
                        "messages": conversation,
                        "inferenceConfig": {
                            "temperature": cfg.temperature,
                            "maxTokens": cfg.max_tokens,
                            "topP": cfg.top_p,
                        }
                    }
                    if system_prompt:
                        request_params["system"] = [{"text": system_prompt}]
                    
                    return self.client.converse(**request_params)
                
                response = await self._with_throttle_retry(make_request)
                
                if i > 0:
                    print(f"   ✅ Bedrock: Succeeded with fallback model {i+1}/{len(models_to_try)}: {model}")
                
                return self._parse_response(response, model)
                
            except Exception as e:
                last_error = e
                if i < len(models_to_try) - 1:
                    print(f"   ⚠️  Bedrock: Model {model} failed ({e}), trying next model...")
                else:
                    print(f"   ❌ Bedrock: All {len(models_to_try)} models failed")
        
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
        
        # Determine which models to try
        if cfg.model:
            models_to_try = [cfg.model]
        else:
            models_to_try = self._models
        
        system_prompt, conversation = self._convert_messages(messages)
        last_error = None
        
        for i, model in enumerate(models_to_try):
            # Throttle retry for streaming
            for throttle_attempt in range(5):
                try:
                    # Build request params
                    request_params = {
                        "modelId": model,
                        "messages": conversation,
                        "inferenceConfig": {
                            "temperature": cfg.temperature,
                            "maxTokens": cfg.max_tokens,
                            "topP": cfg.top_p,
                        }
                    }
                    if system_prompt:
                        request_params["system"] = [{"text": system_prompt}]
                    
                    # Start streaming (sync call, we'll iterate in thread)
                    response = await asyncio.to_thread(
                        self.client.converse_stream,
                        **request_params
                    )
                    
                    if i > 0:
                        print(f"   ✅ Bedrock: Streaming with fallback model {i+1}/{len(models_to_try)}: {model}")
                    
                    # Process stream
                    stream = response.get("stream", [])
                    
                    # Iterate through stream events
                    for event in stream:
                        if "contentBlockDelta" in event:
                            delta = event["contentBlockDelta"].get("delta", {})
                            text = delta.get("text", "")
                            if text:
                                yield StreamChunk(content=text, is_final=False)
                        
                        elif "messageStop" in event:
                            stop_reason = event["messageStop"].get("stopReason")
                            yield StreamChunk(content="", is_final=True, finish_reason=stop_reason)
                    
                    # Successfully completed streaming
                    return
                    
                except Exception as e:
                    error_str = str(e).lower()
                    # Check for throttling errors
                    if ("throttl" in error_str or "rate" in error_str or "too many" in error_str) and throttle_attempt < 4:
                        wait_time = 2 ** throttle_attempt
                        print(f"   ⏳ Bedrock throttled, waiting {wait_time}s (attempt {throttle_attempt + 1}/5)...")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    last_error = e
                    if i < len(models_to_try) - 1:
                        print(f"   ⚠️  Bedrock: Model {model} failed ({e}), trying next model...")
                    else:
                        print(f"   ❌ Bedrock: All {len(models_to_try)} models failed")
                    break  # Exit throttle retry loop, try next model
        
        raise last_error
    
    # -------------------------------------------------------------------------
    # Private Methods
    # -------------------------------------------------------------------------
    
    def _apply_defaults(self, config: LLMConfig) -> LLMConfig:
        """
        Apply Bedrock-specific defaults from environment.
        
        Only overrides values that are at the generic LLMConfig defaults,
        allowing users to explicitly set custom values.
        """
        if config.temperature == self._CONFIG_DEFAULTS.temperature:
            config.temperature = Environment.bedrock_temperature
        if config.max_tokens == self._CONFIG_DEFAULTS.max_tokens:
            config.max_tokens = Environment.bedrock_max_tokens
        if config.timeout_seconds == self._CONFIG_DEFAULTS.timeout_seconds:
            config.timeout_seconds = Environment.bedrock_timeout
        return config
    
    def _parse_response(self, response: Dict[str, Any], model: str) -> LLMResponse:
        """Parse Bedrock Converse response to standard format."""
        # Extract content
        output = response.get("output", {})
        message_data = output.get("message", {})
        content_blocks = message_data.get("content", [])
        
        content = ""
        for block in content_blocks:
            if "text" in block:
                content += block["text"]
        
        # Extract usage
        usage = response.get("usage", {})
        
        return LLMResponse(
            content=content,
            prompt_tokens=usage.get("inputTokens", 0),
            completion_tokens=usage.get("outputTokens", 0),
            total_tokens=usage.get("totalTokens", 0),
            model=model,
            finish_reason=response.get("stopReason"),
            provider=self.provider_name,
            raw_response=response,
        )

