"""
Multi-Provider LLM Distribution.

Distributes LLM requests across multiple providers for load balancing,
failover, and rate limit avoidance.
"""

from __future__ import annotations

import asyncio
import random
from enum import Enum
from typing import AsyncIterator, List, Optional

from llm.base import LLMProvider, LLMConfig, LLMResponse, Message, StreamChunk


class DistributionStrategy(Enum):
    """Strategy for distributing requests across providers."""
    ROUND_ROBIN = "round_robin"      # Cycle through providers in order
    RANDOM = "random"                 # Random selection
    FAILOVER = "failover"            # Use first provider, failover to others on error
    WEIGHTED = "weighted"            # Weighted random selection


class MultiProvider(LLMProvider):
    """
    Distributes LLM requests across multiple providers.
    
    Supports various distribution strategies:
    - ROUND_ROBIN: Cycle through providers evenly
    - RANDOM: Random selection for each request
    - FAILOVER: Primary provider with fallback chain
    - WEIGHTED: Weighted random selection
    
    Usage:
        from llm import NebiusProvider, BedrockProvider
        from llm.multi import MultiProvider, DistributionStrategy
        
        # Create individual providers
        providers = [
            NebiusProvider(),
            BedrockProvider(),
        ]
        
        # Create multi-provider with round-robin distribution
        multi = MultiProvider(
            providers=providers,
            strategy=DistributionStrategy.ROUND_ROBIN
        )
        
        # Use like any other provider
        response = await multi.generate("Hello!")
    """
    
    def __init__(
        self,
        providers: List[LLMProvider],
        strategy: DistributionStrategy = DistributionStrategy.ROUND_ROBIN,
        weights: Optional[List[float]] = None,
        retry_on_failure: bool = True,
        max_retries: int = 3,
    ):
        """
        Initialize multi-provider.
        
        Args:
            providers: List of LLM provider instances
            strategy: Distribution strategy (default: ROUND_ROBIN)
            weights: Optional weights for WEIGHTED strategy (must sum to 1.0)
            retry_on_failure: Whether to retry with other providers on failure
            max_retries: Maximum retry attempts across providers
        """
        if not providers:
            raise ValueError("At least one provider is required")
        
        self._providers = providers
        self._strategy = strategy
        self._weights = weights
        self._retry_on_failure = retry_on_failure
        self._max_retries = max_retries
        
        # Round-robin counter
        self._rr_counter = 0
        self._lock = asyncio.Lock()
        
        # Validate weights for WEIGHTED strategy
        if strategy == DistributionStrategy.WEIGHTED:
            if not weights or len(weights) != len(providers):
                raise ValueError("Weights must be provided for WEIGHTED strategy and match provider count")
            if abs(sum(weights) - 1.0) > 0.01:
                raise ValueError("Weights must sum to 1.0")
    
    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------
    
    @property
    def provider_name(self) -> str:
        provider_names = [p.provider_name for p in self._providers]
        return f"multi({'+'.join(provider_names)})"
    
    @property
    def default_model(self) -> str:
        return self._providers[0].default_model if self._providers else ""
    
    @property
    def providers(self) -> List[LLMProvider]:
        """Get list of underlying providers."""
        return self._providers
    
    # -------------------------------------------------------------------------
    # Provider Selection
    # -------------------------------------------------------------------------
    
    async def _select_provider(self) -> LLMProvider:
        """Select next provider based on strategy."""
        if self._strategy == DistributionStrategy.ROUND_ROBIN:
            async with self._lock:
                provider = self._providers[self._rr_counter % len(self._providers)]
                self._rr_counter += 1
                return provider
        
        elif self._strategy == DistributionStrategy.RANDOM:
            return random.choice(self._providers)
        
        elif self._strategy == DistributionStrategy.FAILOVER:
            return self._providers[0]  # Always return first, failover in execute
        
        elif self._strategy == DistributionStrategy.WEIGHTED:
            return random.choices(self._providers, weights=self._weights, k=1)[0]
        
        return self._providers[0]
    
    def _get_fallback_providers(self, exclude: LLMProvider) -> List[LLMProvider]:
        """Get providers to try after primary fails."""
        return [p for p in self._providers if p is not exclude]
    
    # -------------------------------------------------------------------------
    # Non-Streaming Methods
    # -------------------------------------------------------------------------
    
    async def generate(self, prompt: str, config: Optional[LLMConfig] = None) -> LLMResponse:
        """Generate text from a prompt, distributing across providers."""
        return await self.chat([Message(role="user", content=prompt)], config)
    
    async def chat(self, messages: List[Message], config: Optional[LLMConfig] = None) -> LLMResponse:
        """
        Generate text from conversation history with provider distribution.
        
        Retries with other providers on failure if retry_on_failure is enabled.
        """
        self._validate_messages(messages)
        
        # Select primary provider
        primary = await self._select_provider()
        tried_providers = set()
        last_error = None
        
        # Try primary provider
        for attempt in range(self._max_retries):
            # Get provider to try
            if attempt == 0:
                provider = primary
            elif self._retry_on_failure:
                # Try other providers
                fallbacks = self._get_fallback_providers(primary)
                available = [p for p in fallbacks if p.provider_name not in tried_providers]
                if not available:
                    break
                provider = available[0]
            else:
                break
            
            tried_providers.add(provider.provider_name)
            
            try:
                response = await provider.chat(messages, config)
                if attempt > 0:
                    print(f"   ✅ MultiProvider: Succeeded with fallback {provider.provider_name}")
                return response
                
            except Exception as e:
                last_error = e
                print(f"   ⚠️  MultiProvider: {provider.provider_name} failed ({e})")
                
                if not self._retry_on_failure:
                    raise
        
        # All providers failed
        raise RuntimeError(f"All providers failed. Last error: {last_error}")
    
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
        """
        Stream text generation with provider distribution.
        
        Note: Streaming cannot easily retry mid-stream, so only retries
        on initial connection failure.
        """
        self._validate_messages(messages)
        
        # Select primary provider
        primary = await self._select_provider()
        tried_providers = set()
        last_error = None
        
        for attempt in range(self._max_retries):
            if attempt == 0:
                provider = primary
            elif self._retry_on_failure:
                fallbacks = self._get_fallback_providers(primary)
                available = [p for p in fallbacks if p.provider_name not in tried_providers]
                if not available:
                    break
                provider = available[0]
            else:
                break
            
            tried_providers.add(provider.provider_name)
            
            try:
                async for chunk in provider.chat_stream(messages, config):
                    yield chunk
                return  # Successfully completed
                
            except Exception as e:
                last_error = e
                print(f"   ⚠️  MultiProvider: {provider.provider_name} streaming failed ({e})")
                
                if not self._retry_on_failure:
                    raise
        
        raise RuntimeError(f"All providers failed streaming. Last error: {last_error}")


# =============================================================================
# Factory Functions
# =============================================================================

def create_multi_provider(
    provider_names: List[str],
    strategy: str = "round_robin",
    weights: Optional[List[float]] = None,
) -> MultiProvider:
    """
    Create a MultiProvider from provider names.
    
    Args:
        provider_names: List of provider names (e.g., ["nebius", "bedrock"])
        strategy: Distribution strategy name
        weights: Optional weights for weighted strategy
    
    Returns:
        Configured MultiProvider instance
    
    Example:
        multi = create_multi_provider(
            provider_names=["nebius", "bedrock"],
            strategy="round_robin"
        )
    """
    from llm.client import LLMClient
    from llm.base import ProviderType
    
    providers = []
    for name in provider_names:
        provider_type = ProviderType(name.lower())
        provider = LLMClient._create_provider(provider_type)
        providers.append(provider)
    
    strategy_enum = DistributionStrategy(strategy.lower())
    
    return MultiProvider(
        providers=providers,
        strategy=strategy_enum,
        weights=weights,
    )

