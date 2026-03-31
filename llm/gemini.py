"""
Google Gemini LLM Provider.

Uses Google's Vertex AI Gemini API for text generation with streaming support.
Supports model fallback and rate limit retry with exponential backoff.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, AsyncIterator, List, Optional, TYPE_CHECKING, Tuple

from llm.base import LLMProvider, LLMConfig, LLMResponse, Message, StreamChunk
from environment import Environment

if TYPE_CHECKING:
    from google.genai import types as genai_types

# =============================================================================
# Module Setup
# =============================================================================

def _setup_credentials() -> None:
    """Setup Google credentials from environment variables."""
    cert_path = Environment.google_cert_location
    cert_exists = (
        cert_path is not None
        and os.path.exists(cert_path)
        and os.path.isfile(cert_path)
        and cert_path.endswith('.json')
    )
    
    if not cert_exists and Environment.google_cert_json:
        cert_path = cert_path or '/tmp/google-credentials.json'
        with open(cert_path, 'w') as f:
            json.dump(json.loads(Environment.google_cert_json), f)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cert_path


_setup_credentials()

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    types = None
    GENAI_AVAILABLE = False


# =============================================================================
# Provider Implementation
# =============================================================================

class GeminiProvider(LLMProvider):
    """
    Google Gemini LLM provider using Vertex AI.
    
    Supports both standard and streaming responses with model fallback
    and rate limit retry with exponential backoff.
    
    Usage:
        provider = GeminiProvider()
        
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
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        model: Optional[str] = None,
        models: Optional[List[str]] = None
    ):
        """
        Initialize Gemini provider.
        
        Args:
            project_id: GCP project ID (default: from environment)
            location: GCP region (default: from environment)
            model: Single model name (convenience parameter, added to models list)
            models: List of models to try in order on failure (default: from environment)
        """
        if not GENAI_AVAILABLE:
            raise ImportError("google-genai required. Install: pip install google-genai")
        
        self._project_id = project_id or Environment.gcp_project_id
        self._location = location or Environment.gcp_location
        
        # Handle model parameter - if single model provided, use it; otherwise use models list
        if model:
            self._models = [model]
        elif models:
            self._models = models
        else:
            self._models = Environment.gemini_models
        
        self._client = None
        
        if not self._project_id:
            raise ValueError("GCP_PROJECT_ID required. Set environment variable or pass project_id.")
        if not self._models:
            raise ValueError("GEMINI_MODELS required. Set environment variable or pass models.")
    
    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------
    
    @property
    def provider_name(self) -> str:
        return "gemini"
    
    @property
    def default_model(self) -> str:
        return self._models[0] if self._models else ""
    
    @property
    def client(self):
        """Lazily initialize Gemini client."""
        if self._client is None:
            self._client = genai.Client(
                vertexai=True,
                project=self._project_id,
                location=self._location,
            )
        return self._client
    
    # -------------------------------------------------------------------------
    # Rate Limit Handling
    # -------------------------------------------------------------------------
    
    async def _with_rate_limit_retry(self, sync_func, max_retries: int = 5):
        """
        Execute sync function with exponential backoff retry for rate/quota errors.
        
        Args:
            sync_func: Synchronous function to execute in thread
            max_retries: Maximum retry attempts for rate limit errors
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return await asyncio.to_thread(sync_func)
            except Exception as e:
                error_str = str(e).lower()
                # Check for rate limit / quota errors
                if "quota" in error_str or "rate" in error_str or "429" in error_str or "resource_exhausted" in error_str:
                    last_error = e
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        print(f"   ⏳ Gemini rate limited, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})...")
                        await asyncio.sleep(wait_time)
                    continue
                # Non-rate-limit error, re-raise immediately
                raise
        
        # All retries exhausted
        raise last_error
    
    # -------------------------------------------------------------------------
    # Non-Streaming Methods
    # -------------------------------------------------------------------------
    
    async def generate(self, prompt: str, config: Optional[LLMConfig] = None) -> LLMResponse:
        """Generate text from a prompt."""
        return await self.chat([Message(role="user", content=prompt)], config)
    
    async def chat(self, messages: List[Message], config: Optional[LLMConfig] = None) -> LLMResponse:
        """
        Generate text from conversation history with model fallback on failure.
        
        Internally uses streaming API to avoid timeout issues with long responses,
        but returns a complete LLMResponse (same interface as non-streaming).
        
        Includes rate limit retry with exponential backoff.
        """
        self._validate_messages(messages)
        cfg = self._apply_defaults(self._merge_config(config))
        
        system_prompt, contents = self._convert_messages(messages)
        gen_config = self._build_config(cfg, system_prompt)
        
        # Determine which models to try
        if cfg.model:
            models_to_try = [cfg.model]
        else:
            models_to_try = self._models
        
        import queue
        import threading
        
        last_error = None
        
        for i, model in enumerate(models_to_try):
            # Rate limit retry for streaming
            for rate_attempt in range(5):
                try:
                    chunk_queue: queue.Queue = queue.Queue()
                    error_holder: List[Exception] = []
                    usage_holder: List[Any] = []  # To capture usage metadata from final chunk
                    
                    def _stream():
                        try:
                            stream = self.client.models.generate_content_stream(
                                model=model,
                                contents=contents,
                                config=gen_config,
                            )
                            for chunk in stream:
                                chunk_queue.put(chunk)
                                # Capture usage metadata if available
                                if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                                    usage_holder.clear()
                                    usage_holder.append(chunk.usage_metadata)
                            chunk_queue.put(None)  # Signal completion
                        except Exception as e:
                            error_holder.append(e)
                            chunk_queue.put(None)
                    
                    # Start streaming thread
                    thread = threading.Thread(target=_stream)
                    thread.start()
                    
                    if i > 0:
                        print(f"   ✅ Gemini: Succeeded with fallback model {i+1}/{len(models_to_try)}: {model}")
                    
                    # Collect all chunks into a single response
                    collected_text = []
                    finish_reason = None
                    
                    while True:
                        while chunk_queue.empty():
                            await asyncio.sleep(0.01)
                        
                        chunk = chunk_queue.get()
                        
                        if chunk is None:
                            if error_holder:
                                raise error_holder[0]
                            break
                        
                        # Extract text from chunk
                        if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                            for part in chunk.candidates[0].content.parts:
                                if hasattr(part, 'text') and part.text:
                                    collected_text.append(part.text)
                        
                        # Capture finish reason from final chunk
                        if chunk.candidates and hasattr(chunk.candidates[0], 'finish_reason'):
                            if chunk.candidates[0].finish_reason:
                                finish_reason = str(chunk.candidates[0].finish_reason).lower()
                    
                    thread.join()
                    
                    # Build LLMResponse from collected chunks
                    content = "".join(collected_text)
                    
                    # Extract token usage if available
                    prompt_tokens = 0
                    completion_tokens = 0
                    total_tokens = 0
                    
                    if usage_holder:
                        usage = usage_holder[0]
                        prompt_tokens = getattr(usage, 'prompt_token_count', 0) or 0
                        completion_tokens = getattr(usage, 'candidates_token_count', 0) or 0
                        total_tokens = getattr(usage, 'total_token_count', 0) or (prompt_tokens + completion_tokens)
                    
                    return LLMResponse(
                        content=content,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        model=model,
                        finish_reason=finish_reason,
                        provider=self.provider_name,
                        raw_response=None,  # No single raw response when streaming
                    )
                    
                except Exception as e:
                    error_str = str(e).lower()
                    # Check for rate limit / quota errors
                    if ("quota" in error_str or "rate" in error_str or "429" in error_str or "resource_exhausted" in error_str) and rate_attempt < 4:
                        wait_time = 2 ** rate_attempt
                        print(f"   ⏳ Gemini rate limited, waiting {wait_time}s (attempt {rate_attempt + 1}/5)...")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    last_error = e
                    if i < len(models_to_try) - 1:
                        print(f"   ⚠️  Gemini: Model {model} failed ({e}), trying next model...")
                    else:
                        print(f"   ❌ Gemini: All {len(models_to_try)} models failed")
                    break  # Exit rate limit retry, try next model
        
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
        """Stream text generation from conversation history with model fallback and rate limit retry."""
        self._validate_messages(messages)
        cfg = self._apply_defaults(self._merge_config(config))
        
        system_prompt, contents = self._convert_messages(messages)
        gen_config = self._build_config(cfg, system_prompt)
        
        # Determine which models to try
        if cfg.model:
            models_to_try = [cfg.model]
        else:
            models_to_try = self._models
        
        import queue
        import threading
        
        last_error = None
        
        for i, model in enumerate(models_to_try):
            # Rate limit retry for streaming
            for rate_attempt in range(5):
                try:
                    chunk_queue: queue.Queue = queue.Queue()
                    error_holder: List[Exception] = []
                    
                    def _stream():
                        try:
                            stream = self.client.models.generate_content_stream(
                                model=model,
                                contents=contents,
                                config=gen_config,
                            )
                            for chunk in stream:
                                chunk_queue.put(chunk)
                            chunk_queue.put(None)  # Signal completion
                        except Exception as e:
                            error_holder.append(e)
                            chunk_queue.put(None)
                    
                    # Start streaming thread
                    thread = threading.Thread(target=_stream)
                    thread.start()
                    
                    if i > 0:
                        print(f"   ✅ Gemini: Streaming with fallback model {i+1}/{len(models_to_try)}: {model}")
                    
                    # Yield chunks as they arrive
                    while True:
                        while chunk_queue.empty():
                            await asyncio.sleep(0.01)
                        
                        chunk = chunk_queue.get()
                        
                        if chunk is None:
                            if error_holder:
                                raise error_holder[0]
                            break
                        
                        text = ""
                        finish_reason = None
                        
                        if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                            for part in chunk.candidates[0].content.parts:
                                if hasattr(part, 'text') and part.text:
                                    text += part.text
                        
                        if chunk.candidates and hasattr(chunk.candidates[0], 'finish_reason'):
                            if chunk.candidates[0].finish_reason:
                                finish_reason = str(chunk.candidates[0].finish_reason).lower()
                        
                        yield StreamChunk(
                            content=text,
                            is_final=finish_reason is not None,
                            finish_reason=finish_reason,
                        )
                    
                    thread.join()
                    return  # Successfully completed
                    
                except Exception as e:
                    error_str = str(e).lower()
                    # Check for rate limit / quota errors
                    if ("quota" in error_str or "rate" in error_str or "429" in error_str or "resource_exhausted" in error_str) and rate_attempt < 4:
                        wait_time = 2 ** rate_attempt
                        print(f"   ⏳ Gemini rate limited, waiting {wait_time}s (attempt {rate_attempt + 1}/5)...")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    last_error = e
                    if i < len(models_to_try) - 1:
                        print(f"   ⚠️  Gemini: Model {model} streaming failed ({e}), trying next model...")
                    else:
                        print(f"   ❌ Gemini: All {len(models_to_try)} models failed")
                    break  # Exit rate limit retry, try next model
        
        raise last_error
    
    # -------------------------------------------------------------------------
    # Private Methods
    # -------------------------------------------------------------------------
    
    def _apply_defaults(self, config: LLMConfig) -> LLMConfig:
        """
        Apply Gemini-specific defaults from environment.
        
        Only overrides values that are at the generic LLMConfig defaults,
        allowing users to explicitly set custom values.
        """
        if config.temperature == self._CONFIG_DEFAULTS.temperature:
            config.temperature = Environment.gemini_temperature
        if config.max_tokens == self._CONFIG_DEFAULTS.max_tokens:
            config.max_tokens = Environment.gemini_max_tokens
        if config.timeout_seconds == self._CONFIG_DEFAULTS.timeout_seconds:
            config.timeout_seconds = Environment.gemini_timeout
        return config
    
    def _convert_messages(self, messages: List[Message]) -> Tuple[Optional[str], List]:
        """Convert messages to Gemini format."""
        system_prompt = None
        contents = []
        
        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            else:
                role = "model" if msg.role == "assistant" else "user"
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part(text=msg.content)]
                ))
        
        return system_prompt, contents
    
    def _build_config(self, config: LLMConfig, system_prompt: Optional[str]) -> genai_types.GenerateContentConfig:
        """Build Gemini generation config."""
        thinking_budget = config.extra.get("thinking_budget") if config.extra else None
        thinking_label = f", thinking_budget={thinking_budget}" if thinking_budget is not None else ""
        print(f"   🔧 Gemini config: max_output_tokens={config.max_tokens}, temperature={config.temperature}{thinking_label}")
        
        gen_config = types.GenerateContentConfig(
            temperature=config.temperature,
            top_p=config.top_p,
            max_output_tokens=config.max_tokens,
            safety_settings=[
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
            ],
        )
        
        if thinking_budget is not None:
            if thinking_budget == 0:
                gen_config.thinking_config = types.ThinkingConfig(thinking_budget=0)
            else:
                gen_config.thinking_config = types.ThinkingConfig(thinking_budget=thinking_budget)
        
        if system_prompt:
            gen_config.system_instruction = system_prompt
        
        return gen_config
    
    def _parse_response(self, response: Any, model: str) -> LLMResponse:
        """Parse Gemini response to standard format."""
        content = getattr(response, 'text', "") or ""
        
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            usage = response.usage_metadata
            prompt_tokens = getattr(usage, 'prompt_token_count', 0) or 0
            completion_tokens = getattr(usage, 'candidates_token_count', 0) or 0
            total_tokens = getattr(usage, 'total_token_count', 0) or (prompt_tokens + completion_tokens)
        
        finish_reason = None
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'finish_reason'):
                finish_reason = str(candidate.finish_reason).lower()
        
        return LLMResponse(
            content=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            model=model,
            finish_reason=finish_reason,
            provider=self.provider_name,
            raw_response=response,
        )
