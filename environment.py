"""
Environment configuration for LLM providers.

All environment variables should be accessed through this module.
"""

import os


class Environment:
    """Environment configuration for the research task."""

    # ==========================================================================
    # Core Configuration
    # ==========================================================================
    message_body = os.getenv("MESSAGE_BODY", None)
    verbose_output = os.getenv("VERBOSE_OUTPUT", "0").lower() in ("1", "true", "yes")

    # ==========================================================================
    # Google Cloud / Gemini Configuration
    # ==========================================================================
    google_cert_json = os.getenv("GOOGLE_CERT_JSON", "")
    google_cert_location = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", None)
    gcp_project_id = os.getenv("GCP_PROJECT_ID", None)
    gcp_location = os.getenv("GCP_LOCATION", "us-central1")

    # Gemini Model Configuration
    _gemini_model_str = os.getenv("GEMINI_MODELS", "gemini-2.5-flash,gemini-2.0-flash-001")
    gemini_models = [m.strip() for m in _gemini_model_str.split(",") if m.strip()]
    gemini_model = gemini_models[0] if gemini_models else "gemini-2.5-flash"  # Default/first model
    gemini_temperature = float(os.getenv("GEMINI_TEMPERATURE", "0.2"))
    gemini_max_tokens = int(os.getenv("GEMINI_MAX_TOKENS", "64000"))
    gemini_timeout = int(os.getenv("GEMINI_TIMEOUT", "600"))  # 10 minutes for large context

    # GCP Streaming Configuration
    gcp_stream_timeout_seconds = int(os.getenv("GCP_STREAM_TIMEOUT_SECONDS", "600"))
    gcp_stream_retry = int(os.getenv("GCP_STREAM_RETRY", "3"))
    gcp_max_continuations = int(os.getenv("GCP_MAX_CONTINUATIONS", "3"))

    # ==========================================================================
    # Nebius Configuration
    # ==========================================================================
    nebius_api_key = os.getenv("NEBIUS_API_KEY", None)
    nebius_base_url = os.getenv("NEBIUS_BASE_URL", "https://api.studio.nebius.com/v1/")
    _nebius_model_str = os.getenv("NEBIUS_MODELS", "Qwen/Qwen3-235B-A22B-Instruct-2507")
    nebius_models = [m.strip() for m in _nebius_model_str.split(",") if m.strip()]
    nebius_temperature = float(os.getenv("NEBIUS_TEMPERATURE", "0.1"))
    nebius_max_tokens = int(os.getenv("NEBIUS_MAX_TOKENS", "64000"))
    nebius_max_input_tokens = int(os.getenv("NEBIUS_MAX_INPUT_TOKENS", "160000"))  # Max input tokens (leave room for output)
    nebius_context_limit = int(os.getenv("NEBIUS_CONTEXT_LIMIT", "262144"))  # Qwen3 model context window
    nebius_timeout = int(os.getenv("NEBIUS_TIMEOUT", "600"))  # 20 minutes for long-running requests

    # ==========================================================================
    # AWS Credentials
    # ==========================================================================
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID", None)
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY", None)
    aws_region = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))

    # AWS S3 Configuration
    aws_s3_region = os.getenv("AWS_S3_REGION", aws_region)

    # AWS Connection Pool Configuration
    aws_max_pool_connections = int(os.getenv("AWS_MAX_POOL_CONNECTIONS", "50"))
    aws_connect_timeout = int(os.getenv("AWS_CONNECT_TIMEOUT", "60"))
    aws_read_timeout = int(os.getenv("AWS_READ_TIMEOUT", "60"))
    aws_max_retry_attempts = int(os.getenv("AWS_MAX_RETRY_ATTEMPTS", "3"))

    # ==========================================================================
    # AWS Bedrock Configuration
    # ==========================================================================
    bedrock_region = os.getenv("BEDROCK_REGION", os.getenv("AWS_REGION", "us-east-2"))
    _bedrock_model_str = os.getenv("BEDROCK_MODELS", "qwen.qwen3-235b-a22b-2507-v1:0,qwen.qwen3-235b-a22b-2507-v1:0,qwen.qwen3-235b-a22b-2507-v1:0")
    bedrock_models = [m.strip() for m in _bedrock_model_str.split(",") if m.strip()]
    bedrock_temperature = float(os.getenv("BEDROCK_TEMPERATURE", "0.2"))
    bedrock_max_tokens = int(os.getenv("BEDROCK_MAX_TOKENS", "4096"))
    bedrock_timeout = int(os.getenv("BEDROCK_TIMEOUT", "600"))  # 10 minutes for long responses

    # ==========================================================================
    # LLM Provider Selection
    # ==========================================================================
    # Default provider: "gemini", "nebius", or "bedrock"
    llm_default_provider = os.getenv("LLM_DEFAULT_PROVIDER", "nebius")
    
    # Multi-Provider Configuration (for distributing across multiple providers)
    # Set LLM_MULTI_PROVIDERS to enable (e.g., "nebius,bedrock")
    _llm_multi_providers_str = os.getenv("LLM_MULTI_PROVIDERS", "")
    llm_multi_providers = [p.strip() for p in _llm_multi_providers_str.split(",") if p.strip()]
    llm_multi_strategy = os.getenv("LLM_MULTI_STRATEGY", "round_robin")  # round_robin, random, failover, weighted
    
    # Chunk size for "list" output type - smaller chunks for parallel extraction
    llm_chunk_size = int(os.getenv("LLM_CHUNK_SIZE", "8000"))
    # Chunk size for "single" output type - larger chunks since we select relevant ones
    llm_single_chunk_size = int(os.getenv("LLM_SINGLE_CHUNK_SIZE", "1200"))
    llm_overlap_pages = int(os.getenv("LLM_OVERLAP_PAGES", "0"))
    llm_source_preview_tokens = int(os.getenv("LLM_SOURCE_PREVIEW_TOKENS", "16000"))
    
    # Parallel Processing
    llm_max_workers = int(os.getenv("LLM_MAX_WORKERS", "10"))

    # Chunk Extraction Retry
    # Max split depth when chunk extraction fails (splits chunk in half and retries)
    llm_chunk_split_max_depth = int(os.getenv("LLM_CHUNK_SPLIT_MAX_DEPTH", "3"))

    # Deduplication
    llm_dedup_batch_size = int(os.getenv("LLM_DEDUP_BATCH_SIZE", "8"))
    llm_dedup_max_retries = int(os.getenv("LLM_DEDUP_MAX_RETRIES", "3"))
    llm_dedup_retry_delay = float(os.getenv("LLM_DEDUP_RETRY_DELAY", "1.0"))  # Base delay in seconds

    # Markdown Template Rendering
    llm_markdown_template_rendering_retries = int(os.getenv("LLM_MARKDOWN_TEMPLATE_RENDERING_RETRIES", "10"))

    # Single Output Type - Max tokens for records passed to LLM for direct rendering
    # Default 92K to allow rich context for comprehensive output generation
    llm_single_output_max_tokens = int(os.getenv("LLM_SINGLE_OUTPUT_MAX_TOKENS", "92000"))

    # Force output type to "single" regardless of schema generation (for testing/debugging)
    # Set to "true" to always use single output mode
    llm_force_single_output = os.getenv("LLM_FORCE_SINGLE_OUTPUT", "false").lower() in ("1", "true", "yes")

    # Max tokens per batch for chunk selection (each batch gets full content, processed in parallel)
    # Set based on your model's input limit, leaving room for prompt overhead
    llm_chunk_selection_batch_tokens = int(os.getenv("LLM_CHUNK_SELECTION_BATCH_TOKENS", "80000"))

    # Tiktoken Encoders
    tiktoken_encoder_primary = os.getenv("TIKTOKEN_ENCODER_PRIMARY", "cl100k_base")
    tiktoken_encoder_fallback = os.getenv("TIKTOKEN_ENCODER_FALLBACK", "gpt2")

    # Version
    version = os.getenv("VERSION", "1.0")


