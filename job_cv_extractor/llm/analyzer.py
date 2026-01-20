"""
LLM Analyzer Module

Handles OpenAI API calls for job posting analysis.
Includes Langfuse integration for observability, tracing, and cost tracking.
"""

import json
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import logger
from .prompts import get_system_prompt, get_user_prompt

# Import Langfuse integration
from .langfuse_config import (
    LANGFUSE_AVAILABLE,
    is_langfuse_configured,
    get_langfuse_client,
    get_langfuse_host,
    flush_langfuse,
    observe,
    create_trace_id,
    start_generation,
    create_score,
    get_trace_url,
)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI SDK not available")


@dataclass
class JobAnalysisResult:
    """Structured result from job posting analysis."""
    job_title: Optional[str] = None
    company: Optional[str] = None
    job_summary: Optional[str] = None
    responsibilities: List[str] = field(default_factory=list)
    hard_skills: List[str] = field(default_factory=list)
    soft_skills: List[str] = field(default_factory=list)
    ats_keywords: List[str] = field(default_factory=list)
    inferred_skills: List[str] = field(default_factory=list)
    seniority_level: Optional[str] = None
    years_of_experience: Optional[str] = None
    
    # Metadata
    success: bool = False
    error_message: Optional[str] = None
    tokens_used: Optional[int] = None
    model_used: Optional[str] = None
    cost_usd: Optional[float] = None  # Estimated cost
    latency_ms: Optional[int] = None  # Response time
    trace_id: Optional[str] = None  # Langfuse trace ID
    trace_url: Optional[str] = None  # URL to view trace
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobAnalysisResult':
        """Create JobAnalysisResult from parsed JSON response."""
        required_skills = data.get('required_skills', {})
        
        return cls(
            job_title=data.get('job_title'),
            company=data.get('company'),
            job_summary=data.get('job_summary'),
            responsibilities=data.get('responsibilities', []),
            hard_skills=required_skills.get('hard_skills', []),
            soft_skills=required_skills.get('soft_skills', []),
            ats_keywords=data.get('ats_keywords', []),
            inferred_skills=data.get('inferred_skills', []),
            seniority_level=data.get('seniority_level'),
            years_of_experience=data.get('years_of_experience'),
            success=True
        )
    
    @classmethod
    def error(cls, message: str) -> 'JobAnalysisResult':
        """Create an error result."""
        return cls(success=False, error_message=message)


# Cost per 1K tokens (approximate, as of 2024)
MODEL_COSTS = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
}


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Estimate the cost of an API call.
    
    Args:
        model: Model name
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
    
    Returns:
        Estimated cost in USD
    """
    costs = MODEL_COSTS.get(model, MODEL_COSTS["gpt-4o-mini"])
    input_cost = (prompt_tokens / 1000) * costs["input"]
    output_cost = (completion_tokens / 1000) * costs["output"]
    return round(input_cost + output_cost, 6)


@observe(name="analyze_job_posting")
def analyze_job_posting(
    job_text: str,
    api_key: Optional[str] = None,
    model: str = "gpt-4o-mini",
    platform: Optional[str] = None,
    url: Optional[str] = None,
) -> JobAnalysisResult:
    """
    Analyze job posting text using OpenAI API with Langfuse tracing.
    
    Args:
        job_text: Cleaned job posting text
        api_key: OpenAI API key (uses env var if not provided)
        model: Model to use (default: gpt-4o-mini for cost efficiency)
        platform: Optional platform name for tracing
        url: Optional URL for tracing
    
    Returns:
        JobAnalysisResult with extracted information
    """
    if not OPENAI_AVAILABLE:
        return JobAnalysisResult.error("OpenAI SDK not installed. Run: pip install openai")
    
    # Get API key
    api_key = api_key or os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return JobAnalysisResult.error("OpenAI API key not provided. Set OPENAI_API_KEY environment variable.")
    
    logger.info(f"Analyzing job posting with {model}")
    
    # Get trace ID for Langfuse tracking
    trace_id = None
    trace_url_str = None
    langfuse_client = get_langfuse_client()
    
    if langfuse_client and is_langfuse_configured():
        try:
            trace_id = langfuse_client.get_current_trace_id()
            if trace_id:
                trace_url_str = get_trace_url(trace_id)
                logger.debug(f"Langfuse trace: {trace_id}")
        except Exception as e:
            logger.debug(f"Failed to get Langfuse trace ID: {str(e)}")
    
    start_time = time.time()
    
    try:
        client = OpenAI(api_key=api_key)
        
        system_prompt = get_system_prompt()
        user_prompt = get_user_prompt(job_text)
        
        # Start a generation span for LLM tracking
        generation = None
        if langfuse_client:
            try:
                generation = langfuse_client.start_generation(
                    name="llm-extraction",
                    model=model,
                    input={
                        "system": system_prompt[:500] + "..." if len(system_prompt) > 500 else system_prompt,
                        "user": user_prompt[:500] + "..." if len(user_prompt) > 500 else user_prompt,
                    },
                    metadata={
                        "temperature": 0.1, 
                        "max_tokens": 2000,
                        "platform": platform or "unknown",
                        "url": url or "unknown",
                    },
                )
            except Exception as e:
                logger.debug(f"Failed to start Langfuse generation: {str(e)}")
        
        # Make API call
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,  # Low temperature for consistent extraction
            max_tokens=2000,
            response_format={"type": "json_object"}  # Enforce JSON response
        )
        
        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Extract response content
        content = response.choices[0].message.content
        
        # Calculate tokens and cost
        tokens_used = None
        prompt_tokens = 0
        completion_tokens = 0
        cost_usd = None
        
        if response.usage:
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            tokens_used = response.usage.total_tokens
            cost_usd = estimate_cost(model, prompt_tokens, completion_tokens)
            logger.info(f"Tokens used: {tokens_used} (prompt: {prompt_tokens}, completion: {completion_tokens})")
            logger.info(f"Estimated cost: ${cost_usd:.6f}")
        
        # End Langfuse generation with output
        if generation:
            try:
                generation.end(
                    output=content[:1000] + "..." if len(content) > 1000 else content,
                    usage={
                        "input": prompt_tokens,
                        "output": completion_tokens,
                        "total": tokens_used,
                        "unit": "TOKENS",
                    },
                    metadata={
                        "cost_usd": cost_usd,
                        "latency_ms": latency_ms,
                    },
                )
            except Exception as e:
                logger.debug(f"Failed to end Langfuse generation: {str(e)}")
        
        # Parse JSON response
        result = _parse_llm_response(content)
        result.tokens_used = tokens_used
        result.model_used = model
        result.cost_usd = cost_usd
        result.latency_ms = latency_ms
        result.trace_id = trace_id
        result.trace_url = trace_url_str
        
        # Calculate extraction quality score
        quality_score = _calculate_extraction_quality(result)
        
        # Add quality score to Langfuse
        if langfuse_client and trace_id:
            try:
                langfuse_client.create_score(
                    trace_id=trace_id,
                    name="extraction_quality",
                    value=quality_score,
                    comment=f"Auto-evaluated: {result.job_title or 'No title'}",
                )
            except Exception as e:
                logger.debug(f"Failed to create score: {str(e)}")
        
        # Flush Langfuse events
        flush_langfuse()
        
        return result
    
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse LLM response as JSON: {str(e)}"
        logger.error(error_msg)
        flush_langfuse()
        return JobAnalysisResult.error(error_msg)
    
    except Exception as e:
        error_msg = f"OpenAI API error: {str(e)}"
        logger.error(error_msg)
        flush_langfuse()
        return JobAnalysisResult.error(error_msg)


def _calculate_extraction_quality(result: JobAnalysisResult) -> float:
    """
    Calculate an automatic quality score for the extraction.
    
    Score is based on completeness of extracted data.
    
    Args:
        result: The extraction result
    
    Returns:
        Quality score between 0 and 1
    """
    if not result.success:
        return 0.0
    
    score = 0.0
    max_score = 0.0
    
    # Job title (important)
    max_score += 0.15
    if result.job_title:
        score += 0.15
    
    # Company
    max_score += 0.10
    if result.company:
        score += 0.10
    
    # Job summary
    max_score += 0.10
    if result.job_summary and len(result.job_summary) > 50:
        score += 0.10
    
    # Responsibilities
    max_score += 0.15
    if result.responsibilities:
        score += min(0.15, len(result.responsibilities) * 0.03)
    
    # Hard skills (important)
    max_score += 0.20
    if result.hard_skills:
        score += min(0.20, len(result.hard_skills) * 0.02)
    
    # Soft skills
    max_score += 0.10
    if result.soft_skills:
        score += min(0.10, len(result.soft_skills) * 0.02)
    
    # ATS keywords
    max_score += 0.15
    if result.ats_keywords:
        score += min(0.15, len(result.ats_keywords) * 0.015)
    
    # Seniority level
    max_score += 0.05
    if result.seniority_level and result.seniority_level != "Unknown":
        score += 0.05
    
    return round(score / max_score if max_score > 0 else 0, 2)


def _parse_llm_response(content: str) -> JobAnalysisResult:
    """
    Parse and validate LLM response.
    
    Args:
        content: Raw response content from LLM
    
    Returns:
        JobAnalysisResult
    """
    # Try to parse JSON
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # Try to extract JSON from response
        data = _extract_json_from_text(content)
        if data is None:
            return JobAnalysisResult.error("Could not parse response as JSON")
    
    # Validate required fields
    if not isinstance(data, dict):
        return JobAnalysisResult.error("Response is not a JSON object")
    
    # Create result
    result = JobAnalysisResult.from_dict(data)
    
    # Validate result
    if not result.job_title and not result.job_summary and not result.responsibilities:
        logger.warning("LLM response missing key fields")
    
    logger.info(f"Successfully parsed job analysis: {result.job_title or 'Unknown Title'}")
    
    return result


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Attempt to extract JSON object from text that may contain other content.
    
    Args:
        text: Text that may contain a JSON object
    
    Returns:
        Parsed JSON dict or None
    """
    import re
    
    # Try to find JSON object in text
    # Look for content between { and }
    match = re.search(r'\{[\s\S]*\}', text)
    
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    
    return None


def validate_api_key(api_key: str) -> bool:
    """
    Validate OpenAI API key by making a minimal API call.
    
    Args:
        api_key: OpenAI API key to validate
    
    Returns:
        True if key is valid
    """
    if not OPENAI_AVAILABLE:
        return False
    
    try:
        client = OpenAI(api_key=api_key)
        # Make minimal API call to validate
        client.models.list()
        return True
    except Exception:
        return False


def get_langfuse_status() -> Dict[str, Any]:
    """
    Get the current Langfuse configuration status.
    
    Returns:
        Dictionary with status information
    """
    return {
        "available": LANGFUSE_AVAILABLE,
        "configured": is_langfuse_configured(),
        "client_initialized": get_langfuse_client() is not None,
        "public_key_set": bool(os.environ.get('LANGFUSE_PUBLIC_KEY')),
        "secret_key_set": bool(os.environ.get('LANGFUSE_SECRET_KEY')),
        "host": get_langfuse_host(),
    }
