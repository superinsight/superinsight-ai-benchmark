"""Utility modules for benchmark."""

from .source_index import SourceIndex
from .markdown_parser import MarkdownParser, parse_output
from .s3_utils import (
    S3Client,
    S3Path,
    BenchmarkContext,
    read_file_or_s3,
    read_json_or_s3,
    is_s3_path,
)
from .token_counter import (
    count_tokens_tiktoken,
    estimate_tokens_from_chars,
    get_model_limits,
    truncate_to_token_limit,
    validate_input_size,
    TokenBudget,
)
from .trace_writer import TraceWriter, TraceMetadata, write_trace

__all__ = [
    'SourceIndex',
    'MarkdownParser',
    'parse_output',
    'S3Client',
    'S3Path',
    'BenchmarkContext',
    'read_file_or_s3',
    'read_json_or_s3',
    'is_s3_path',
    # Token counting
    'count_tokens_tiktoken',
    'estimate_tokens_from_chars',
    'get_model_limits',
    'truncate_to_token_limit',
    'validate_input_size',
    'TokenBudget',
    # Trace writing
    'TraceWriter',
    'TraceMetadata',
    'write_trace',
]
