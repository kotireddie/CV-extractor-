"""
Langfuse Configuration Module

Handles Langfuse setup for LLM observability, tracing, and prompt management.
Langfuse provides:
- Tracing of LLM calls
- Prompt versioning and management
- Cost tracking
- Quality evaluation
- Performance monitoring

Setup:
1. Sign up at https://langfuse.com (free tier available) or self-host
2. Set environment variables:
   - LANGFUSE_PUBLIC_KEY
   - LANGFUSE_SECRET_KEY
   - LANGFUSE_BASE_URL (optional, for different regions/self-hosted)
"""

import os
import sys
from typing import Optional, Any, Dict
from functools import wraps

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import logger

# Try to import Langfuse
LANGFUSE_AVAILABLE = False
langfuse_client = None

try:
    from langfuse import Langfuse, observe
    LANGFUSE_AVAILABLE = True
    logger.info("Langfuse SDK loaded successfully")
except ImportError:
    logger.warning("Langfuse not available. Install with: pip install langfuse")
    LANGFUSE_AVAILABLE = False
    Langfuse = None
    # Create dummy decorator for graceful fallback
    def observe(*args, **kwargs):
        def decorator(func):
            return func
        return decorator


def is_langfuse_configured() -> bool:
    """Check if Langfuse is properly configured with API keys."""
    public_key = os.environ.get('LANGFUSE_PUBLIC_KEY')
    secret_key = os.environ.get('LANGFUSE_SECRET_KEY')
    return bool(public_key and secret_key)


def get_langfuse_host() -> str:
    """Get the Langfuse host URL, checking multiple env var names."""
    return (
        os.environ.get('LANGFUSE_BASE_URL') or 
        os.environ.get('LANGFUSE_HOST') or 
        'https://cloud.langfuse.com'
    )


def init_langfuse() -> Optional[Any]:
    """
    Initialize Langfuse client if available and configured.
    
    Returns:
        Langfuse client instance or None
    """
    global langfuse_client
    
    if not LANGFUSE_AVAILABLE:
        logger.debug("Langfuse SDK not installed")
        return None
    
    if not is_langfuse_configured():
        logger.debug("Langfuse not configured (missing API keys)")
        return None
    
    try:
        host = get_langfuse_host()
        langfuse_client = Langfuse(
            public_key=os.environ.get('LANGFUSE_PUBLIC_KEY'),
            secret_key=os.environ.get('LANGFUSE_SECRET_KEY'),
            host=host,
        )
        logger.info(f"Langfuse client initialized successfully (host: {host})")
        return langfuse_client
    except Exception as e:
        logger.error(f"Failed to initialize Langfuse: {str(e)}")
        return None


def get_langfuse_client() -> Optional[Any]:
    """Get the Langfuse client instance."""
    global langfuse_client
    if langfuse_client is None:
        langfuse_client = init_langfuse()
    return langfuse_client


def flush_langfuse():
    """Flush any pending Langfuse events."""
    if langfuse_client:
        try:
            langfuse_client.flush()
        except Exception as e:
            logger.debug(f"Failed to flush Langfuse: {str(e)}")


def create_trace_id() -> Optional[str]:
    """
    Create a new trace ID for tracking an extraction.
    
    Returns:
        Trace ID string or None
    """
    client = get_langfuse_client()
    
    if client is None:
        return None
    
    try:
        return client.create_trace_id()
    except Exception as e:
        logger.debug(f"Failed to create trace ID: {str(e)}")
        return None


def start_generation(
    name: str,
    model: str,
    input_data: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Any]:
    """
    Start a generation span for LLM call tracking.
    
    Args:
        name: Name of the generation
        model: Model name
        input_data: Input messages/prompts
        metadata: Additional metadata
    
    Returns:
        Generation context manager or None
    """
    client = get_langfuse_client()
    
    if client is None:
        return None
    
    try:
        return client.start_generation(
            name=name,
            model=model,
            input=input_data,
            metadata=metadata or {},
        )
    except Exception as e:
        logger.debug(f"Failed to start generation: {str(e)}")
        return None


def create_score(
    trace_id: str,
    name: str,
    value: float,
    comment: Optional[str] = None
):
    """
    Add a score to a Langfuse trace for quality evaluation.
    
    Args:
        trace_id: ID of the trace to score
        name: Name of the score (e.g., "extraction_quality")
        value: Score value (0-1)
        comment: Optional comment
    """
    client = get_langfuse_client()
    
    if client is None:
        return
    
    try:
        client.create_score(
            trace_id=trace_id,
            name=name,
            value=value,
            comment=comment,
        )
    except Exception as e:
        logger.debug(f"Failed to add score to Langfuse: {str(e)}")


def get_prompt_from_langfuse(prompt_name: str, fallback: str) -> str:
    """
    Get a prompt from Langfuse prompt management, with fallback.
    
    Args:
        prompt_name: Name of the prompt in Langfuse
        fallback: Fallback prompt content if Langfuse is not available
    
    Returns:
        Prompt content string
    """
    client = get_langfuse_client()
    
    if client is None:
        return fallback
    
    try:
        prompt = client.get_prompt(prompt_name)
        if prompt and prompt.prompt:
            logger.debug(f"Using prompt '{prompt_name}' from Langfuse (version {prompt.version})")
            return prompt.prompt
    except Exception as e:
        logger.debug(f"Could not fetch prompt from Langfuse: {str(e)}")
    
    return fallback


def get_trace_url(trace_id: str) -> Optional[str]:
    """
    Get the URL to view a trace in the Langfuse dashboard.
    
    Args:
        trace_id: The trace ID
    
    Returns:
        URL string or None
    """
    client = get_langfuse_client()
    
    if client is None:
        return None
    
    try:
        return client.get_trace_url(trace_id)
    except Exception as e:
        logger.debug(f"Failed to get trace URL: {str(e)}")
        return None


# Export for use in other modules
__all__ = [
    'LANGFUSE_AVAILABLE',
    'is_langfuse_configured',
    'get_langfuse_host',
    'init_langfuse',
    'get_langfuse_client',
    'flush_langfuse',
    'observe',
    'create_trace_id',
    'start_generation',
    'create_score',
    'get_prompt_from_langfuse',
    'get_trace_url',
]
