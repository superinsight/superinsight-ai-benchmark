"""
S3 utilities for reading benchmark inputs from AWS S3.

Supports both s3:// URIs and direct bucket/key specification.
"""

import os
import json
import tempfile
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None
    ClientError = Exception


@dataclass
class S3Path:
    """Parsed S3 path."""
    bucket: str
    key: str
    
    @classmethod
    def parse(cls, path: str) -> Optional['S3Path']:
        """
        Parse S3 URI or return None if not an S3 path.
        
        Args:
            path: Either 's3://bucket/key' or local path
            
        Returns:
            S3Path if valid S3 URI, None otherwise
        """
        if not path:
            return None
            
        if path.startswith('s3://'):
            # Parse s3://bucket/key format
            parts = path[5:].split('/', 1)
            if len(parts) >= 2:
                return cls(bucket=parts[0], key=parts[1])
            elif len(parts) == 1:
                return cls(bucket=parts[0], key='')
        
        return None
    
    def to_uri(self) -> str:
        """Convert back to s3:// URI."""
        return f"s3://{self.bucket}/{self.key}"


class S3Client:
    """
    S3 client for reading benchmark inputs.
    
    Automatically handles credentials from environment.
    """
    
    def __init__(
        self,
        region: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
    ):
        """
        Initialize S3 client.
        
        Args:
            region: AWS region (defaults to AWS_REGION or AWS_DEFAULT_REGION)
            access_key_id: AWS access key (defaults to AWS_ACCESS_KEY_ID)
            secret_access_key: AWS secret key (defaults to AWS_SECRET_ACCESS_KEY)
        """
        if boto3 is None:
            raise ImportError("boto3 is required for S3 support. Install with: pip install boto3")
        
        self.region = region or os.getenv('AWS_REGION', os.getenv('AWS_DEFAULT_REGION', 'us-east-1'))
        self.access_key_id = access_key_id or os.getenv('AWS_ACCESS_KEY_ID')
        self.secret_access_key = secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY')
        
        self._client = None
    
    @property
    def client(self):
        """Lazy load S3 client."""
        if self._client is None:
            if self.access_key_id and self.secret_access_key:
                self._client = boto3.client(
                    's3',
                    region_name=self.region,
                    aws_access_key_id=self.access_key_id,
                    aws_secret_access_key=self.secret_access_key,
                )
            else:
                # Use default credentials (IAM role, etc.)
                self._client = boto3.client('s3', region_name=self.region)
        return self._client
    
    def read_text(self, bucket: str, key: str) -> str:
        """
        Read text content from S3.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            
        Returns:
            Text content of the object
        """
        try:
            response = self.client.get_object(Bucket=bucket, Key=key)
            return response['Body'].read().decode('utf-8')
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            raise RuntimeError(f"Failed to read s3://{bucket}/{key}: {error_code} - {e}")
    
    def read_json(self, bucket: str, key: str) -> Dict[str, Any]:
        """
        Read JSON content from S3.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            
        Returns:
            Parsed JSON content
        """
        text = self.read_text(bucket, key)
        return json.loads(text)
    
    def download_file(self, bucket: str, key: str, local_path: Optional[str] = None) -> str:
        """
        Download file from S3 to local path.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            local_path: Optional local path (creates temp file if not provided)
            
        Returns:
            Local file path
        """
        if local_path is None:
            # Create temp file with same extension
            ext = os.path.splitext(key)[1] or '.txt'
            fd, local_path = tempfile.mkstemp(suffix=ext)
            os.close(fd)
        
        try:
            self.client.download_file(bucket, key, local_path)
            return local_path
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            raise RuntimeError(f"Failed to download s3://{bucket}/{key}: {error_code} - {e}")
    
    def exists(self, bucket: str, key: str) -> bool:
        """Check if object exists in S3."""
        try:
            self.client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError:
            return False


def read_file_or_s3(path: str, s3_client: Optional[S3Client] = None) -> str:
    """
    Read file from local path or S3.
    
    Args:
        path: Local path or s3://bucket/key URI
        s3_client: Optional S3Client instance (created if needed)
        
    Returns:
        File content as string
    """
    s3_path = S3Path.parse(path)
    
    if s3_path:
        # S3 path
        if s3_client is None:
            s3_client = S3Client()
        return s3_client.read_text(s3_path.bucket, s3_path.key)
    else:
        # Local path
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()


def read_json_or_s3(path: str, s3_client: Optional[S3Client] = None) -> Dict[str, Any]:
    """
    Read JSON from local path or S3.
    
    Args:
        path: Local path or s3://bucket/key URI
        s3_client: Optional S3Client instance
        
    Returns:
        Parsed JSON content
    """
    content = read_file_or_s3(path, s3_client)
    return json.loads(content)


def is_s3_path(path: str) -> bool:
    """Check if path is an S3 URI."""
    return path.startswith('s3://') if path else False


@dataclass
class BenchmarkContext:
    """
    Context for benchmark evaluation from MESSAGE_BODY.
    
    Similar to research's ProcessingContext.
    """
    research_id: str
    
    # Output location (required)
    output_s3_bucket: str
    output_s3_key: str
    
    # Source location (optional, for deep check)
    source_s3_bucket: Optional[str] = None
    source_s3_key: Optional[str] = None
    
    # Metadata location (optional, derived from output if not provided)
    metadata_s3_bucket: Optional[str] = None
    metadata_s3_key: Optional[str] = None
    
    # Options
    deep_check: bool = False
    max_claims: int = 50
    
    @classmethod
    def from_message_body(cls, message_body: str) -> 'BenchmarkContext':
        """
        Create context from MESSAGE_BODY JSON.
        
        Args:
            message_body: JSON string with context data
            
        Returns:
            BenchmarkContext instance
        """
        data = json.loads(message_body)
        
        # Required fields
        required = ['research_id', 'output_s3_bucket', 'output_s3_key']
        missing = [f for f in required if f not in data]
        if missing:
            raise ValueError(f"Missing required fields in MESSAGE_BODY: {missing}")
        
        # Derive metadata key from output key if not provided
        metadata_s3_key = data.get('metadata_s3_key')
        if not metadata_s3_key and data.get('output_s3_key'):
            metadata_s3_key = data['output_s3_key'].replace('.md', '_metadata.json')
            # Also try without underscore
            if not metadata_s3_key.endswith('_metadata.json'):
                metadata_s3_key = data['output_s3_key'].replace('output.md', 'metadata.json')
        
        return cls(
            research_id=data['research_id'],
            output_s3_bucket=data['output_s3_bucket'],
            output_s3_key=data['output_s3_key'],
            source_s3_bucket=data.get('source_s3_bucket'),
            source_s3_key=data.get('source_s3_key'),
            metadata_s3_bucket=data.get('metadata_s3_bucket', data['output_s3_bucket']),
            metadata_s3_key=metadata_s3_key,
            deep_check=data.get('deep_check', False),
            max_claims=data.get('max_claims', 50),
        )
    
    def get_output_uri(self) -> str:
        """Get output S3 URI."""
        return f"s3://{self.output_s3_bucket}/{self.output_s3_key}"
    
    def get_source_uri(self) -> Optional[str]:
        """Get source S3 URI if available."""
        if self.source_s3_bucket and self.source_s3_key:
            return f"s3://{self.source_s3_bucket}/{self.source_s3_key}"
        return None
    
    def get_metadata_uri(self) -> Optional[str]:
        """Get metadata S3 URI if available."""
        if self.metadata_s3_bucket and self.metadata_s3_key:
            return f"s3://{self.metadata_s3_bucket}/{self.metadata_s3_key}"
        return None
