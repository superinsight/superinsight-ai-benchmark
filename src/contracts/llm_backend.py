"""
LLM Backend abstraction for rule extraction.

Supports multiple LLM providers:
- Google Gemini (via Vertex AI with GOOGLE_APPLICATION_CREDENTIALS)
- Nebius (OpenAI-compatible)

Features:
- Token limit configuration for input/output management
- Retry with exponential backoff
- Model fallback support

Environment Variables:
- GEMINI_MODEL: Primary Gemini model (default: gemini-2.0-flash)
- GEMINI_FALLBACK_MODELS: Comma-separated fallback models
- NEBIUS_MODEL: Primary Nebius model (default: deepseek-ai/DeepSeek-V3)
- NEBIUS_FALLBACK_MODELS: Comma-separated fallback models
- LLM_MAX_RETRIES: Max retry attempts (default: 3)
- LLM_RETRY_DELAY: Initial retry delay in seconds (default: 1.0)
"""

import os
import json
import time
from abc import ABC, abstractmethod
from typing import Optional, List


# Default token limits by backend
BACKEND_LIMITS = {
    "gemini": {
        "max_input_tokens": 1_000_000,
        "max_output_tokens": 8_192,
        "default_model": "gemini-2.0-flash",
        "fallback_models": ["gemini-2.0-flash", "gemini-1.5-flash"],
    },
    "nebius": {
        "max_input_tokens": 64_000,
        "max_output_tokens": 8_192,
        "default_model": "deepseek-ai/DeepSeek-V3",
        "fallback_models": ["deepseek-ai/DeepSeek-V3", "Qwen/Qwen3-235B-A22B-Instruct-2507"],
    },
}

# Retry configuration
DEFAULT_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
DEFAULT_RETRY_DELAY = float(os.getenv("LLM_RETRY_DELAY", "1.0"))


def is_retryable_error(error: Exception) -> bool:
    """Check if an error is retryable (rate limit, server error, etc.)."""
    error_str = str(error).lower()
    retryable_patterns = [
        '429', 'rate_limit', 'rate limit',
        'resource_exhausted', 'quota',
        '500', '502', '503', '504',
        'timeout', 'timed out',
        'connection', 'network',
    ]
    return any(pattern in error_str for pattern in retryable_patterns)


class LLMBackend(ABC):
    """Abstract base class for LLM backends with retry and fallback support."""
    
    def __init__(
        self,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        fallback_models: Optional[List[str]] = None,
    ):
        """
        Initialize base backend.
        
        Args:
            max_retries: Max retry attempts per model (default: 3)
            retry_delay: Initial delay between retries in seconds (default: 1.0)
            fallback_models: List of fallback models to try on failure
        """
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._fallback_models = fallback_models or []
    
    @abstractmethod
    def _generate_impl(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Internal generate implementation (to be overridden)."""
        pass
    
    @abstractmethod
    def _switch_model(self, model: str) -> None:
        """Switch to a different model."""
        pass
    
    def generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """
        Generate response from prompt with retry and fallback.
        
        Args:
            prompt: The prompt to send to the LLM
            max_tokens: Optional max output tokens (uses default if not specified)
            
        Returns:
            The generated text response
            
        Raises:
            Exception: If all retries and fallbacks fail
        """
        models_to_try = [self.model] + [m for m in self._fallback_models if m != self.model]
        last_exception = None
        
        for model_idx, current_model in enumerate(models_to_try):
            # Switch model if not the primary
            if model_idx > 0:
                try:
                    print(f"🔄 Switching to fallback model: {current_model}")
                    self._switch_model(current_model)
                except Exception as e:
                    print(f"⚠ Failed to switch to {current_model}: {e}")
                    continue
            
            # Retry loop for current model
            for attempt in range(self._max_retries):
                try:
                    return self._generate_impl(prompt, max_tokens)
                except Exception as e:
                    last_exception = e
                    
                    if not is_retryable_error(e):
                        # Non-retryable error, try next model
                        print(f"❌ Non-retryable error with {current_model}: {str(e)[:100]}")
                        break
                    
                    if attempt < self._max_retries - 1:
                        wait_time = self._retry_delay * (2 ** attempt)  # Exponential backoff
                        print(f"⚠ Retry {attempt + 1}/{self._max_retries} for {current_model}, waiting {wait_time:.1f}s: {str(e)[:50]}")
                        time.sleep(wait_time)
                    else:
                        print(f"❌ All {self._max_retries} retries failed for {current_model}")
        
        raise Exception(f"All models failed. Last error: {last_exception}")
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the backend name."""
        pass
    
    @property
    @abstractmethod
    def model(self) -> str:
        """Return the current model name."""
        pass
    
    @property
    @abstractmethod
    def max_input_tokens(self) -> int:
        """Return max input token limit."""
        pass
    
    @property
    @abstractmethod
    def max_output_tokens(self) -> int:
        """Return max output token limit."""
        pass


class GeminiBackend(LLMBackend):
    """
    Google Gemini backend via Vertex AI.
    
    Uses GOOGLE_APPLICATION_CREDENTIALS for authentication (same as research module).
    Supports retry with exponential backoff and model fallback.
    """
    
    def __init__(
        self,
        model: Optional[str] = None,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        max_output_tokens: Optional[int] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        fallback_models: Optional[List[str]] = None,
    ):
        """
        Initialize Gemini backend using Vertex AI.
        
        Args:
            model: Model name (defaults to GEMINI_MODEL env var or gemini-2.0-flash)
            project_id: GCP project ID (defaults to GCP_PROJECT_ID env var)
            location: GCP location (defaults to GCP_LOCATION env var or us-central1)
            max_output_tokens: Max output tokens (defaults to GEMINI_MAX_OUTPUT_TOKENS env var or 8192)
            max_retries: Max retry attempts (default: 3)
            retry_delay: Initial retry delay in seconds (default: 1.0)
            fallback_models: List of fallback models (defaults to GEMINI_FALLBACK_MODELS env var)
        
        Environment Variables:
            GOOGLE_APPLICATION_CREDENTIALS: Path to GCP credential JSON file
            GCP_PROJECT_ID: GCP project ID (required)
            GCP_LOCATION: GCP location (default: us-central1)
            GEMINI_MODEL: Primary model (default: gemini-2.0-flash)
            GEMINI_FALLBACK_MODELS: Comma-separated fallback models
        """
        # Parse fallback models from env if not provided
        if fallback_models is None:
            fallback_env = os.getenv("GEMINI_FALLBACK_MODELS", "")
            if fallback_env:
                fallback_models = [m.strip() for m in fallback_env.split(",") if m.strip()]
            else:
                fallback_models = BACKEND_LIMITS["gemini"]["fallback_models"]
        
        super().__init__(
            max_retries=max_retries,
            retry_delay=retry_delay,
            fallback_models=fallback_models,
        )
        
        try:
            from google import genai
            from google.genai import types
            self.types = types
            self.genai = genai
        except ImportError:
            raise ImportError("google-genai package required. Run: pip install google-genai")
        
        # Setup credentials from file if specified
        self._setup_credentials()
        
        # Get project and location
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        if not self.project_id:
            raise ValueError(
                "GCP_PROJECT_ID environment variable required. "
                "Set it to your Google Cloud project ID."
            )
        
        self.location = location or os.getenv("GCP_LOCATION", "us-central1")
        
        # Initialize client with Vertex AI mode
        self.client = genai.Client(
            vertexai=True,
            project=self.project_id,
            location=self.location,
        )
        
        # Set model (from arg, env, or default)
        self._model = model or os.getenv("GEMINI_MODEL", BACKEND_LIMITS["gemini"]["default_model"])
        self._max_output_tokens = max_output_tokens or int(
            os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "8192")
        )
        self._max_input_tokens = int(
            os.getenv("GEMINI_MAX_INPUT_TOKENS", "1000000")
        )
    
    def _setup_credentials(self):
        """Setup Google credentials from environment."""
        cert_location = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        cert_json = os.getenv("GOOGLE_CERT_JSON")
        
        # Check if credential file exists
        cert_exists = (
            cert_location is not None and
            os.path.exists(cert_location) and
            os.path.isfile(cert_location) and
            cert_location.endswith('.json')
        )
        
        if not cert_exists and cert_json:
            # Create credentials file from JSON secret (for deployment)
            json_cert = json.loads(cert_json)
            cert_path = cert_location or '/tmp/google-credentials.json'
            with open(cert_path, 'w') as json_file:
                json.dump(json_cert, json_file)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cert_path
        elif not cert_exists:
            raise ValueError(
                "GOOGLE_APPLICATION_CREDENTIALS environment variable required. "
                "Set it to the path of your GCP credential JSON file. "
                "Or set GOOGLE_CERT_JSON with the JSON content directly."
            )
    
    @property
    def name(self) -> str:
        return "gemini"
    
    @property
    def model(self) -> str:
        return self._model
    
    @property
    def max_input_tokens(self) -> int:
        return self._max_input_tokens
    
    @property
    def max_output_tokens(self) -> int:
        return self._max_output_tokens
    
    def _switch_model(self, model: str) -> None:
        """Switch to a different Gemini model."""
        self._model = model
    
    def _generate_impl(
        self, 
        prompt: str, 
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> str:
        """
        Internal generate implementation.
        
        Args:
            prompt: The prompt to send
            max_tokens: Max output tokens (optional)
            json_mode: If True, force JSON output format
        """
        config_params = {
            "max_output_tokens": max_tokens or self._max_output_tokens,
            "temperature": 0.1,
        }
        
        # Enable JSON mode if requested (Gemini 2.0+ supports this)
        if json_mode:
            config_params["response_mime_type"] = "application/json"
        
        config = self.types.GenerateContentConfig(**config_params)
        
        response = self.client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=config,
        )
        return response.text
    
    def generate_json(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """
        Generate response with JSON mode enabled.
        
        Uses Gemini's native JSON mode for more reliable structured output.
        Falls back to retry logic for model compatibility.
        
        Args:
            prompt: The prompt (should ask for JSON output)
            max_tokens: Optional max output tokens
            
        Returns:
            JSON string response
        """
        try:
            return self._generate_impl(prompt, max_tokens, json_mode=True)
        except Exception as e:
            # Fallback if JSON mode not supported (older models)
            if "response_mime_type" in str(e) or "unsupported" in str(e).lower():
                return self._generate_impl(prompt, max_tokens, json_mode=False)
            raise


class NebiusBackend(LLMBackend):
    """
    Nebius AI backend (OpenAI-compatible API).
    
    Supports retry with exponential backoff and model fallback.
    """
    
    def __init__(
        self, 
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_output_tokens: Optional[int] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        fallback_models: Optional[List[str]] = None,
    ):
        """
        Initialize Nebius backend.
        
        Args:
            model: Model name (defaults to NEBIUS_MODEL env var or deepseek-ai/DeepSeek-V3)
            api_key: API key (defaults to NEBIUS_API_KEY env var)
            base_url: API base URL (defaults to NEBIUS_API_BASE env var)
            max_output_tokens: Max output tokens (defaults to NEBIUS_MAX_OUTPUT_TOKENS env var or 8192)
            max_retries: Max retry attempts (default: 3)
            retry_delay: Initial retry delay in seconds (default: 1.0)
            fallback_models: List of fallback models (defaults to NEBIUS_FALLBACK_MODELS env var)
        
        Environment Variables:
            NEBIUS_API_KEY: API key (required)
            NEBIUS_API_BASE: API base URL
            NEBIUS_MODEL: Primary model (default: deepseek-ai/DeepSeek-V3)
            NEBIUS_FALLBACK_MODELS: Comma-separated fallback models
        """
        # Parse fallback models from env if not provided
        if fallback_models is None:
            fallback_env = os.getenv("NEBIUS_FALLBACK_MODELS", "")
            if fallback_env:
                fallback_models = [m.strip() for m in fallback_env.split(",") if m.strip()]
            else:
                fallback_models = BACKEND_LIMITS["nebius"]["fallback_models"]
        
        super().__init__(
            max_retries=max_retries,
            retry_delay=retry_delay,
            fallback_models=fallback_models,
        )
        
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package required. Run: pip install openai")
        
        self.api_key = api_key or os.getenv("NEBIUS_API_KEY")
        if not self.api_key:
            raise ValueError("NEBIUS_API_KEY environment variable required")
        
        self.base_url = base_url or os.getenv(
            "NEBIUS_API_BASE", 
            "https://api.studio.nebius.com/v1"
        )
        
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )
        
        # Set model (from arg, env, or default)
        self._model = model or os.getenv("NEBIUS_MODEL", BACKEND_LIMITS["nebius"]["default_model"])
        self._max_output_tokens = max_output_tokens or int(
            os.getenv("NEBIUS_MAX_OUTPUT_TOKENS", "8192")
        )
        self._max_input_tokens = int(
            os.getenv("NEBIUS_MAX_INPUT_TOKENS", "64000")
        )
    
    @property
    def name(self) -> str:
        return "nebius"
    
    @property
    def model(self) -> str:
        return self._model
    
    @property
    def max_input_tokens(self) -> int:
        return self._max_input_tokens
    
    @property
    def max_output_tokens(self) -> int:
        return self._max_output_tokens
    
    def _switch_model(self, model: str) -> None:
        """Switch to a different Nebius model."""
        self._model = model
    
    def _generate_impl(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Internal generate implementation."""
        response = self.client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=max_tokens or self._max_output_tokens,
        )
        return response.choices[0].message.content


class OpenAIBackend(LLMBackend):
    """
    OpenAI backend for GPT models (chat completions API).
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        max_output_tokens: Optional[int] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        fallback_models: Optional[List[str]] = None,
    ):
        super().__init__(
            max_retries=max_retries,
            retry_delay=retry_delay,
            fallback_models=fallback_models or [],
        )

        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package required. Run: pip install openai")

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable required")

        self.client = OpenAI(api_key=self.api_key)
        self._model = model or "gpt-5.4-mini"
        self._max_output_tokens = max_output_tokens or 8192
        self._max_input_tokens = 128000

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    @property
    def max_input_tokens(self) -> int:
        return self._max_input_tokens

    @property
    def max_output_tokens(self) -> int:
        return self._max_output_tokens

    def _switch_model(self, model: str) -> None:
        self._model = model

    def _generate_impl(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        response = self.client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_completion_tokens=max_tokens or self._max_output_tokens,
        )
        return response.choices[0].message.content or ""


class AnthropicBackend(LLMBackend):
    """
    Anthropic backend for Claude models.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        max_output_tokens: Optional[int] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        fallback_models: Optional[List[str]] = None,
    ):
        super().__init__(
            max_retries=max_retries,
            retry_delay=retry_delay,
            fallback_models=fallback_models or [],
        )

        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropic package required. Run: pip install anthropic")

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable required")

        self._anthropic = anthropic
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self._model = model or "claude-opus-4-5-20251101"
        self._max_output_tokens = max_output_tokens or 8192
        self._max_input_tokens = 200000

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def model(self) -> str:
        return self._model

    @property
    def max_input_tokens(self) -> int:
        return self._max_input_tokens

    @property
    def max_output_tokens(self) -> int:
        return self._max_output_tokens

    def _switch_model(self, model: str) -> None:
        self._model = model

    def _generate_impl(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        message = self.client.messages.create(
            model=self._model,
            max_tokens=max_tokens or self._max_output_tokens,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text if message.content else ""


def get_backend(
    backend_name: Optional[str] = None,
    model: Optional[str] = None,
    max_output_tokens: Optional[int] = None,
    project_id: Optional[str] = None,
    location: Optional[str] = None,
    max_retries: Optional[int] = None,
    retry_delay: Optional[float] = None,
    fallback_models: Optional[List[str]] = None,
) -> LLMBackend:
    """
    Factory function to get LLM backend.
    
    Args:
        backend_name: "gemini" or "nebius" (defaults to LLM_BACKEND env var)
        model: Optional model override (defaults to GEMINI_MODEL or NEBIUS_MODEL env var)
        max_output_tokens: Optional max output tokens override
        project_id: GCP project ID (for Gemini only)
        location: GCP location (for Gemini only)
        max_retries: Max retry attempts (defaults to LLM_MAX_RETRIES env var or 3)
        retry_delay: Initial retry delay in seconds (defaults to LLM_RETRY_DELAY env var or 1.0)
        fallback_models: List of fallback models to try on failure
        
    Returns:
        LLMBackend instance
    """
    backend_name = backend_name or os.getenv("LLM_BACKEND", "gemini")
    backend_name = backend_name.lower()
    
    # Common kwargs
    common_kwargs = {}
    if max_retries is not None:
        common_kwargs["max_retries"] = max_retries
    if retry_delay is not None:
        common_kwargs["retry_delay"] = retry_delay
    if fallback_models is not None:
        common_kwargs["fallback_models"] = fallback_models
    
    if backend_name == "nebius":
        kwargs = {**common_kwargs}
        if model:
            kwargs["model"] = model
        if max_output_tokens:
            kwargs["max_output_tokens"] = max_output_tokens
        return NebiusBackend(**kwargs)
    elif backend_name == "gemini":
        kwargs = {**common_kwargs}
        if model:
            kwargs["model"] = model
        if max_output_tokens:
            kwargs["max_output_tokens"] = max_output_tokens
        if project_id:
            kwargs["project_id"] = project_id
        if location:
            kwargs["location"] = location
        return GeminiBackend(**kwargs)
    elif backend_name == "openai":
        kwargs = {**common_kwargs}
        if model:
            kwargs["model"] = model
        if max_output_tokens:
            kwargs["max_output_tokens"] = max_output_tokens
        return OpenAIBackend(**kwargs)
    elif backend_name == "anthropic":
        kwargs = {**common_kwargs}
        if model:
            kwargs["model"] = model
        if max_output_tokens:
            kwargs["max_output_tokens"] = max_output_tokens
        return AnthropicBackend(**kwargs)
    else:
        raise ValueError(f"Unknown backend: {backend_name}. Use 'gemini', 'nebius', 'openai', or 'anthropic'")
