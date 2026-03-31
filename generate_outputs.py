#!/usr/bin/env python3
"""
Generate benchmark outputs from multiple LLM models.

Uses the bundled LLMClient to call each model with the same
instruction + source document, producing one output per model for
subsequent comparison via `python main.py --compare`.

Usage:
    # Generate outputs for all default models
    python generate_outputs.py \
        -i examples/medical_chronology_instruction.txt \
        -s examples/benchmark_source_small.txt \
        -o outputs/medical_chronology

    # Use a models config file for custom model list
    python generate_outputs.py \
        -i examples/medical_chronology_instruction.txt \
        -s examples/benchmark_source_small.txt \
        -o outputs/medical_chronology \
        --models-config models.json

    # Generate for a single model only
    python generate_outputs.py \
        -i examples/medical_chronology_instruction.txt \
        -s examples/source.txt \
        -o outputs/medical_chronology_full \
        --model gemini:gemini-2.5-pro:gemini-2.5-pro

    # List available models without running
    python generate_outputs.py --list-models

Environment:
    Requires env vars for LLM providers (GCP credentials, NEBIUS_API_KEY, etc.)
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(override=True)

sys.path.insert(0, str(Path(__file__).parent))

from llm import LLMClient
from llm.base import LLMConfig


# ── Default Models ──────────────────────────────────────────────────────────

DEFAULT_MODELS = [
    {"provider": "gemini", "model": "gemini-2.5-pro", "label": "gemini-2.5-pro"},
    {"provider": "gemini", "model": "gemini-2.5-flash", "label": "gemini-2.5-flash"},
    {"provider": "nebius", "model": None, "label": "qwen3-235b"},
]


# ── Provider Helpers ────────────────────────────────────────────────────────

def _create_client(
    provider: str,
    model,
    config: LLMConfig,
    logs_dir: str,
) -> LLMClient:
    """Create LLMClient for a given provider, handling provider-specific quirks."""
    if provider == "nebius":
        from llm.nebius import NebiusProvider
        p = NebiusProvider()
        if model:
            config.model = model
        return LLMClient(provider=p, config=config, logs_dir=logs_dir)

    if provider == "openai":
        if model and "pro" in model.lower():
            return _create_openai_responses_client(model, config, logs_dir)
        return _create_openai_client(model, config, logs_dir)

    if provider == "anthropic":
        return _create_anthropic_client(model, config, logs_dir)

    if provider == "genai":
        return _create_genai_client(model, config, logs_dir)

    if provider == "bedrock":
        from llm.bedrock import BedrockProvider
        p = BedrockProvider(model=model) if model else BedrockProvider()
        return LLMClient(provider=p, config=config, logs_dir=logs_dir)

    # Default: gemini or any provider supported by LLMClient.create
    config.model = model
    return LLMClient.create(
        provider_type=provider,
        model=model,
        config=config,
        logs_dir=logs_dir,
    )


# ── OpenAI (direct, streaming) ────────────────────────────────────────────

class _OpenAIProvider:
    """OpenAI API provider using httpx streaming."""

    def __init__(self, api_key: str, model: str):
        import httpx
        self._model = model
        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(600.0, connect=30.0),
        )

    async def generate(self, prompt: str, max_tokens: int, temperature: float) -> dict:
        import json as _json

        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "max_completion_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        chunks = []
        finish_reason = "unknown"
        model_name = self._model
        usage = {}

        async with self._client.stream(
            "POST",
            "https://api.openai.com/v1/chat/completions",
            json=payload,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    event = _json.loads(data_str)
                except _json.JSONDecodeError:
                    continue

                if event.get("usage"):
                    usage = event["usage"]

                for choice in event.get("choices", []):
                    delta = choice.get("delta", {})
                    content = delta.get("content")
                    if content:
                        chunks.append(content)
                    if choice.get("finish_reason"):
                        finish_reason = choice["finish_reason"]

                if event.get("model"):
                    model_name = event["model"]

        return {
            "content": "".join(chunks),
            "model": model_name,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "finish_reason": finish_reason,
        }


def _create_openai_client(model, config: LLMConfig, logs_dir: str):
    api_key = os.environ.get("OPENAI_API_KEY", "")
    model_id = model or "gpt-5.4"

    if not api_key:
        raise ValueError("OPENAI_API_KEY must be set in .env")

    provider = _OpenAIProvider(api_key, model_id)

    class _OpenAIClient:
        def __init__(self):
            os.makedirs(logs_dir, exist_ok=True)
            print(f"   📁 LLM logs directory: {logs_dir}")
            print(f"   🔧 OpenAI: model={model_id}")

        async def generate(self, prompt: str):
            import json as _json
            result = await provider.generate(
                prompt,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
            )

            log_path = os.path.join(logs_dir, "0001_openai.json")
            with open(log_path, "w") as f:
                _json.dump({
                    "provider": "openai",
                    "model": result["model"],
                    "prompt_chars": len(prompt),
                    "prompt_tokens": result["prompt_tokens"],
                    "completion_tokens": result["completion_tokens"],
                    "finish_reason": result["finish_reason"],
                }, f, indent=2)

            class _Resp:
                content = result["content"]
                model_name = result["model"]
                prompt_tokens = result["prompt_tokens"]
                completion_tokens = result["completion_tokens"]
                total_tokens = result["total_tokens"]
            _Resp.model = result["model"]
            return _Resp()

    return _OpenAIClient()


# ── OpenAI Responses API (for non-chat models like gpt-5.4-pro) ──────────

def _create_openai_responses_client(model, config: LLMConfig, logs_dir: str):
    """Use OpenAI Responses API for models that don't support chat/completions."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    model_id = model or "gpt-5.4-pro"

    if not api_key:
        raise ValueError("OPENAI_API_KEY must be set in .env")

    class _OpenAIResponsesClient:
        def __init__(self):
            import openai
            self._client = openai.OpenAI(api_key=api_key)
            os.makedirs(logs_dir, exist_ok=True)
            print(f"   📁 LLM logs directory: {logs_dir}")
            print(f"   🔧 OpenAI Responses API: model={model_id}")

        async def generate(self, prompt: str):
            import asyncio
            import json as _json

            def _call():
                return self._client.responses.create(
                    model=model_id,
                    input=prompt,
                )

            resp = await asyncio.to_thread(_call)

            content = resp.output_text or ""
            input_tokens = resp.usage.input_tokens if resp.usage else 0
            output_tokens = resp.usage.output_tokens if resp.usage else 0

            log_path = os.path.join(logs_dir, "0001_openai_responses.json")
            with open(log_path, "w") as f:
                _json.dump({
                    "provider": "openai-responses",
                    "model": model_id,
                    "prompt_chars": len(prompt),
                    "prompt_tokens": input_tokens,
                    "completion_tokens": output_tokens,
                    "finish_reason": "stop",
                }, f, indent=2)

            class _Resp:
                pass
            r = _Resp()
            r.content = content
            r.model_name = model_id
            r.model = model_id
            r.prompt_tokens = input_tokens
            r.completion_tokens = output_tokens
            r.total_tokens = input_tokens + output_tokens
            return r

    return _OpenAIResponsesClient()


# ── Anthropic (direct, streaming) ─────────────────────────────────────────

class _AnthropicProvider:
    """Anthropic API provider using httpx streaming."""

    def __init__(self, api_key: str, model: str):
        import httpx
        self._model = model
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(600.0, connect=30.0),
        )

    async def generate(self, prompt: str, max_tokens: int, temperature: float) -> dict:
        import json as _json

        payload = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
            "messages": [{"role": "user", "content": prompt}],
        }

        chunks = []
        finish_reason = "unknown"
        model_name = self._model
        input_tokens = 0
        output_tokens = 0

        async with self._client.stream(
            "POST",
            "https://api.anthropic.com/v1/messages",
            json=payload,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                try:
                    event = _json.loads(data_str)
                except _json.JSONDecodeError:
                    continue

                event_type = event.get("type", "")

                if event_type == "message_start":
                    msg = event.get("message", {})
                    model_name = msg.get("model", self._model)
                    usage = msg.get("usage", {})
                    input_tokens = usage.get("input_tokens", 0)

                elif event_type == "content_block_delta":
                    delta = event.get("delta", {})
                    if delta.get("type") == "text_delta":
                        chunks.append(delta.get("text", ""))

                elif event_type == "message_delta":
                    delta = event.get("delta", {})
                    if delta.get("stop_reason"):
                        finish_reason = delta["stop_reason"]
                    usage = event.get("usage", {})
                    output_tokens = usage.get("output_tokens", output_tokens)

        return {
            "content": "".join(chunks),
            "model": model_name,
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "finish_reason": finish_reason,
        }


def _create_anthropic_client(model, config: LLMConfig, logs_dir: str):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    model_id = model or "claude-opus-4-6"

    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY must be set in .env")

    provider = _AnthropicProvider(api_key, model_id)

    class _AnthropicClient:
        def __init__(self):
            os.makedirs(logs_dir, exist_ok=True)
            print(f"   📁 LLM logs directory: {logs_dir}")
            print(f"   🔧 Anthropic: model={model_id}")

        async def generate(self, prompt: str):
            import json as _json
            result = await provider.generate(
                prompt,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
            )

            log_path = os.path.join(logs_dir, "0001_anthropic.json")
            with open(log_path, "w") as f:
                _json.dump({
                    "provider": "anthropic",
                    "model": result["model"],
                    "prompt_chars": len(prompt),
                    "prompt_tokens": result["prompt_tokens"],
                    "completion_tokens": result["completion_tokens"],
                    "finish_reason": result["finish_reason"],
                }, f, indent=2)

            class _Resp:
                content = result["content"]
                model_name = result["model"]
                prompt_tokens = result["prompt_tokens"]
                completion_tokens = result["completion_tokens"]
                total_tokens = result["total_tokens"]
            _Resp.model = result["model"]
            return _Resp()

    return _AnthropicClient()


# ── Google AI Studio (genai SDK, for Gemini 3+ preview models) ────────────

class _GenaiProvider:
    """
    Lightweight provider using google-genai SDK via Google AI Studio API key.
    Bypasses Vertex AI auth — needed for preview models not available on Vertex.
    """

    def __init__(self, api_key: str, model: str):
        from google import genai
        from google.genai import types
        self._client = genai.Client(api_key=api_key)
        self._types = types
        self._model = model

    async def generate(self, prompt: str, max_tokens: int, temperature: float) -> dict:
        import asyncio

        config = self._types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        )

        def _call():
            return self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=config,
            )

        resp = await asyncio.to_thread(_call)
        usage = resp.usage_metadata
        return {
            "content": resp.text or "",
            "model": self._model,
            "prompt_tokens": usage.prompt_token_count if usage else 0,
            "completion_tokens": usage.candidates_token_count if usage else 0,
            "total_tokens": usage.total_token_count if usage else 0,
            "finish_reason": "stop",
        }


def _create_genai_client(model, config: LLMConfig, logs_dir: str):
    """Return a thin wrapper using Google AI Studio for Gemini 3+ preview models."""
    api_key = os.environ.get("GOOGLE_AI_STUDIO_API_KEY", "")
    model_id = model or "gemini-3.1-pro-preview"

    if not api_key:
        raise ValueError("GOOGLE_AI_STUDIO_API_KEY must be set in .env")

    provider = _GenaiProvider(api_key, model_id)

    class _GenaiClient:
        """Minimal client matching LLMClient.generate() interface."""

        def __init__(self):
            os.makedirs(logs_dir, exist_ok=True)
            print(f"   📁 LLM logs directory: {logs_dir}")
            print(f"   🔧 GenAI Studio: model={model_id}")

        async def generate(self, prompt: str):
            import json as _json
            result = await provider.generate(
                prompt,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
            )

            log_path = os.path.join(logs_dir, "0001_genai.json")
            with open(log_path, "w") as f:
                _json.dump({
                    "provider": "genai",
                    "model": result["model"],
                    "prompt_chars": len(prompt),
                    "prompt_tokens": result["prompt_tokens"],
                    "completion_tokens": result["completion_tokens"],
                    "finish_reason": result["finish_reason"],
                }, f, indent=2)

            class _Resp:
                content = result["content"]
                model_name = result["model"]
                prompt_tokens = result["prompt_tokens"]
                completion_tokens = result["completion_tokens"]
                total_tokens = result["total_tokens"]
            _Resp.model = result["model"]
            return _Resp()

    return _GenaiClient()


# ── Core ────────────────────────────────────────────────────────────────────

def build_prompt(instruction: str, source: str) -> str:
    return (
        f"{instruction}\n\n"
        f"---\n\n"
        f"## Source Document\n\n"
        f"{source}"
    )


async def generate_single(
    provider: str,
    model,
    label: str,
    prompt: str,
    output_dir: str,
    max_tokens: int,
    temperature: float,
) -> dict:
    """Generate output from a single model and save to disk."""
    print(f"\n{'='*60}")
    print(f"Model: {label} ({provider}/{model or 'default'})")
    print(f"{'='*60}")

    logs_dir = os.path.join(output_dir, label, "llm_logs")
    os.makedirs(logs_dir, exist_ok=True)

    extra = {}
    if provider == "gemini" and model and "flash" in model:
        extra["thinking_budget"] = 0

    config = LLMConfig(
        temperature=temperature,
        max_tokens=max_tokens,
        timeout_seconds=600,
        extra=extra,
    )

    client = _create_client(provider, model, config, logs_dir)

    MAX_RETRIES = 3
    MIN_OUTPUT_CHARS = 100

    start = time.perf_counter()
    try:
        response = None
        for attempt in range(MAX_RETRIES):
            response = await client.generate(prompt)
            if response.content and len(response.content.strip()) >= MIN_OUTPUT_CHARS:
                break
            chars = len(response.content) if response.content else 0
            print(f"   [retry {attempt+1}/{MAX_RETRIES}] Empty/short response ({chars} chars), retrying...")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(2)
        duration = time.perf_counter() - start

        output_path = os.path.join(output_dir, label, "output.md")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(response.content)

        meta = {
            "label": label,
            "provider": provider,
            "model": response.model,
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "total_tokens": response.total_tokens,
            "duration_seconds": round(duration, 2),
            "output_chars": len(response.content),
            "output_path": output_path,
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "success",
        }

        meta_path = os.path.join(output_dir, label, "metadata.json")
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

        print(f"   Duration: {duration:.1f}s")
        print(f"   Tokens: {response.prompt_tokens} in / {response.completion_tokens} out")
        print(f"   Output: {len(response.content):,} chars → {output_path}")
        return meta

    except Exception as e:
        duration = time.perf_counter() - start
        print(f"   ERROR: {e}")
        meta = {
            "label": label,
            "provider": provider,
            "model": model,
            "duration_seconds": round(duration, 2),
            "status": "error",
            "error": str(e),
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        meta_path = os.path.join(output_dir, label, "metadata.json")
        os.makedirs(os.path.dirname(meta_path), exist_ok=True)
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)
        return meta


# ── Models Config ───────────────────────────────────────────────────────────

def load_models_config(config_path: str) -> list:
    """
    Load models from a JSON config file.

    Format:
    [
      {"provider": "gemini", "model": "gemini-2.5-pro", "label": "gemini-2.5-pro"},
      {"provider": "nebius", "model": null, "label": "qwen3-235b"},
      {"provider": "bedrock", "model": "anthropic.claude-3-5-sonnet-20241022-v2:0", "label": "claude-3.5-sonnet"}
    ]
    """
    with open(config_path, "r") as f:
        data = json.load(f)
    if isinstance(data, dict) and "models" in data:
        data = data["models"]
    models = []
    for m in data:
        models.append({
            "provider": m["provider"],
            "model": m.get("model") or None,
            "label": m.get("label") or m.get("name") or f"{m['provider']}-{m.get('model', 'default')}",
        })
    return models


# ── CLI ─────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(
        description="Generate benchmark outputs from multiple models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default models, small source
  python generate_outputs.py -i examples/medical_chronology_instruction.txt \\
      -s examples/benchmark_source_small.txt -o outputs/medical_chronology

  # Full source (large document benchmark)
  python generate_outputs.py -i examples/medical_chronology_instruction.txt \\
      -s examples/source.txt -o outputs/medical_chronology_full

  # Custom models from config
  python generate_outputs.py -i examples/claim_info_instruction.txt \\
      -s examples/source.txt -o outputs/claim_info \\
      --models-config models.json

  # Single model
  python generate_outputs.py -i examples/red_flags_instruction.txt \\
      -s examples/benchmark_source_small.txt -o outputs/red_flags \\
      --model gemini:gemini-2.5-pro:gemini-pro
        """,
    )
    parser.add_argument("--instruction", "-i", help="Path to instruction file")
    parser.add_argument("--source", "-s", help="Path to source document")
    parser.add_argument("--output-dir", "-o", default="outputs", help="Output directory (default: outputs)")
    parser.add_argument("--model", "-m", action="append",
                        help="Model spec: provider:model:label (can repeat). If omitted, uses defaults.")
    parser.add_argument("--models-config", help="Path to JSON file with model definitions")
    parser.add_argument("--max-tokens", type=int, default=64000, help="Max output tokens (default: 64000)")
    parser.add_argument("--temperature", type=float, default=0.2, help="Temperature (default: 0.2)")
    parser.add_argument("--list-models", action="store_true", help="List default models and exit")
    parser.add_argument("--sequential", action="store_true", help="Run models sequentially (default: parallel)")
    args = parser.parse_args()

    if args.list_models:
        print("Default models:")
        for m in DEFAULT_MODELS:
            print(f"  {m['label']:25s} provider={m['provider']}, model={m['model'] or '(default)'}")
        print("\nAvailable providers: gemini, nebius, bedrock")
        print("\nTo add custom models, create a models.json:")
        print('  [{"provider": "gemini", "model": "gemini-2.5-pro", "label": "my-label"}]')
        return

    if not args.instruction or not args.source:
        parser.error("--instruction and --source are required (unless using --list-models)")

    with open(args.instruction, "r") as f:
        instruction = f.read()
    with open(args.source, "r") as f:
        source = f.read()

    prompt = build_prompt(instruction, source)
    source_size_mb = len(source) / 1_000_000
    est_tokens = len(prompt) // 4
    print(f"Instruction: {len(instruction):,} chars")
    print(f"Source: {len(source):,} chars ({source_size_mb:.1f} MB, ~{est_tokens:,} tokens)")
    print(f"Total prompt: {len(prompt):,} chars")

    # Resolve model list
    if args.models_config:
        models = load_models_config(args.models_config)
        print(f"\nLoaded {len(models)} models from {args.models_config}")
    elif args.model:
        models = []
        for spec in args.model:
            parts = spec.split(":")
            if len(parts) == 3:
                models.append({"provider": parts[0], "model": parts[1] or None, "label": parts[2]})
            elif len(parts) == 2:
                models.append({"provider": parts[0], "model": parts[1] or None, "label": parts[1] or parts[0]})
            else:
                models.append({"provider": parts[0], "model": None, "label": parts[0]})
    else:
        models = DEFAULT_MODELS

    print(f"\nModels to run: {len(models)}")
    for m in models:
        print(f"  - {m['label']} ({m['provider']}/{m['model'] or 'default'})")

    os.makedirs(args.output_dir, exist_ok=True)

    if args.sequential:
        results = []
        for m in models:
            r = await generate_single(
                m["provider"], m["model"], m["label"],
                prompt, args.output_dir, args.max_tokens, args.temperature,
            )
            results.append(r)
    else:
        tasks = [
            generate_single(
                m["provider"], m["model"], m["label"],
                prompt, args.output_dir, args.max_tokens, args.temperature,
            )
            for m in models
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        results = [
            r if isinstance(r, dict) else {"status": "error", "error": str(r)}
            for r in results
        ]

    # Write summary
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "instruction_file": args.instruction,
        "source_file": args.source,
        "source_chars": len(source),
        "prompt_chars": len(prompt),
        "models": results,
    }
    summary_path = os.path.join(args.output_dir, "generation_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    # Generate comparison_config.json (paths relative to config file directory)
    config_dir = os.path.abspath(args.output_dir)
    def _rel(p: str) -> str:
        return os.path.relpath(os.path.abspath(p), config_dir)

    comparison_config = {
        "comparison_name": f"Model Comparison - {Path(args.instruction).stem}",
        "instruction": _rel(args.instruction),
        "source": _rel(args.source),
        "parser": "auto",
        "models": [
            {
                "name": r["label"],
                "output": os.path.join(r["label"], "output.md"),
                "provider": r.get("provider", ""),
                "model_id": r.get("model", "") or "",
            }
            for r in results
            if isinstance(r, dict) and r.get("status") == "success"
        ],
    }
    config_path = os.path.join(args.output_dir, "comparison_config.json")
    with open(config_path, "w") as f:
        json.dump(comparison_config, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Summary: {summary_path}")
    print(f"Comparison config: {config_path}")
    print(f"\nNext step:")
    print(f"  python main.py --compare {config_path}")

    success = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "success")
    print(f"\nResults: {success}/{len(models)} succeeded")


if __name__ == "__main__":
    asyncio.run(main())
