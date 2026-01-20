"""
Job Source Detection Module

Detects the job posting platform (Greenhouse, Lever, Workday, Apple, iCIMS, AshbyHQ, etc.)
from URL patterns and embedded parameters.
"""

import re
from urllib.parse import urlparse, parse_qs
from typing import Literal
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import logger


# Job source type - Extended to include new platforms
JobSource = Literal[
    "greenhouse", "lever", "workday", "apple", "icims", 
    "ashby", "successfactors", "generic"
]


# URL patterns for each platform
GREENHOUSE_PATTERNS = [
    r'boards\.greenhouse\.io',
    r'greenhouse\.io/embed',
    r'[?&]gh_jid=\d+',  # Embedded Greenhouse job ID parameter
    r'job_app\.greenhouse\.io',
]

LEVER_PATTERNS = [
    r'jobs\.lever\.co',
    r'lever\.co/[^/]+/[a-f0-9-]+',
]

WORKDAY_PATTERNS = [
    r'myworkdayjobs\.com',
    r'\.workday\.com/.*?/job/',
    r'wd\d+\.myworkdaysite\.com',
]

# New platform patterns
APPLE_PATTERNS = [
    r'jobs\.apple\.com',
]

ICIMS_PATTERNS = [
    r'\.icims\.com',
    r'icims\.com/jobs/',
]

ASHBY_PATTERNS = [
    r'jobs\.ashbyhq\.com',
    r'ashbyhq\.com/[^/]+/[a-f0-9-]+',
]

SUCCESSFACTORS_PATTERNS = [
    r'\.careers/',  # Common pattern for SAP SuccessFactors career sites
    r'successfactors\.com',
    r'performancemanager\d*\.successfactors\.com',
    r'/job/[^/]+-[A-Z]{2}-\d+/',  # Pattern like /job/City-Title-ST-12345/
]


# Platform characteristics
PLATFORM_CHARACTERISTICS = {
    "greenhouse": {
        "requires_js": False,
        "has_schema_org": True,
        "extraction_priority": ["schema", "html", "fallback"]
    },
    "lever": {
        "requires_js": False,
        "has_schema_org": True,
        "extraction_priority": ["schema", "html", "fallback"]
    },
    "workday": {
        "requires_js": True,
        "has_schema_org": False,
        "extraction_priority": ["browser", "fallback"]
    },
    "apple": {
        "requires_js": True,
        "has_schema_org": False,
        "extraction_priority": ["browser", "fallback"]
    },
    "icims": {
        "requires_js": True,
        "has_schema_org": False,
        "extraction_priority": ["browser", "fallback"]
    },
    "ashby": {
        "requires_js": True,
        "has_schema_org": True,  # AshbyHQ includes Schema.org data!
        "extraction_priority": ["schema", "browser", "fallback"]
    },
    "successfactors": {
        "requires_js": False,
        "has_schema_org": False,
        "extraction_priority": ["html", "fallback"]
    },
    "generic": {
        "requires_js": False,
        "has_schema_org": False,
        "extraction_priority": ["schema", "html", "fallback", "browser"]
    }
}


def detect_source(url: str) -> JobSource:
    """
    Detect the job posting platform from URL.
    
    Args:
        url: Job posting URL
    
    Returns:
        JobSource enum string indicating the platform
    """
    url_lower = url.lower()
    
    # Check Greenhouse patterns
    if detect_greenhouse(url):
        logger.info("Detected Greenhouse job page")
        return "greenhouse"
    
    # Check Lever patterns
    if detect_lever(url):
        logger.info("Detected Lever job page")
        return "lever"
    
    # Check Workday patterns
    if detect_workday(url):
        logger.info("Detected Workday job page")
        return "workday"
    
    # Check Apple patterns
    if detect_apple(url):
        logger.info("Detected Apple job page")
        return "apple"
    
    # Check iCIMS patterns
    if detect_icims(url):
        logger.info("Detected iCIMS job page")
        return "icims"
    
    # Check AshbyHQ patterns
    if detect_ashby(url):
        logger.info("Detected AshbyHQ job page")
        return "ashby"
    
    # Check SAP SuccessFactors patterns
    if detect_successfactors(url):
        logger.info("Detected SAP SuccessFactors job page")
        return "successfactors"
    
    logger.info("Using generic extraction (no specific platform detected)")
    return "generic"


def detect_greenhouse(url: str) -> bool:
    """
    Detect if URL is a Greenhouse job posting.
    
    Checks for:
    - Direct boards.greenhouse.io URLs
    - Embedded job pages with gh_jid parameter
    - Greenhouse embed URLs
    
    Args:
        url: URL to check
    
    Returns:
        True if Greenhouse job posting
    """
    url_lower = url.lower()
    
    for pattern in GREENHOUSE_PATTERNS:
        if re.search(pattern, url_lower):
            logger.debug(f"Greenhouse pattern matched: {pattern}")
            return True
    
    # Also check for gh_jid in query params
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    
    if 'gh_jid' in query_params:
        logger.debug("Greenhouse gh_jid parameter found")
        return True
    
    return False


def detect_lever(url: str) -> bool:
    """
    Detect if URL is a Lever job posting.
    
    Args:
        url: URL to check
    
    Returns:
        True if Lever job posting
    """
    url_lower = url.lower()
    
    for pattern in LEVER_PATTERNS:
        if re.search(pattern, url_lower):
            logger.debug(f"Lever pattern matched: {pattern}")
            return True
    
    return False


def detect_workday(url: str) -> bool:
    """
    Detect if URL is a Workday job posting.
    
    Args:
        url: URL to check
    
    Returns:
        True if Workday job posting
    """
    url_lower = url.lower()
    
    for pattern in WORKDAY_PATTERNS:
        if re.search(pattern, url_lower):
            logger.debug(f"Workday pattern matched: {pattern}")
            return True
    
    return False


def detect_apple(url: str) -> bool:
    """
    Detect if URL is an Apple job posting.
    
    Args:
        url: URL to check
    
    Returns:
        True if Apple job posting
    """
    url_lower = url.lower()
    
    for pattern in APPLE_PATTERNS:
        if re.search(pattern, url_lower):
            logger.debug(f"Apple pattern matched: {pattern}")
            return True
    
    return False


def detect_icims(url: str) -> bool:
    """
    Detect if URL is an iCIMS job posting.
    
    iCIMS is a popular Applicant Tracking System (ATS) used by many companies.
    URLs typically contain .icims.com in the domain.
    
    Args:
        url: URL to check
    
    Returns:
        True if iCIMS job posting
    """
    url_lower = url.lower()
    
    for pattern in ICIMS_PATTERNS:
        if re.search(pattern, url_lower):
            logger.debug(f"iCIMS pattern matched: {pattern}")
            return True
    
    return False


def detect_ashby(url: str) -> bool:
    """
    Detect if URL is an AshbyHQ job posting.
    
    AshbyHQ provides Schema.org structured data even though
    the page requires JavaScript to render visually.
    
    Args:
        url: URL to check
    
    Returns:
        True if AshbyHQ job posting
    """
    url_lower = url.lower()
    
    for pattern in ASHBY_PATTERNS:
        if re.search(pattern, url_lower):
            logger.debug(f"AshbyHQ pattern matched: {pattern}")
            return True
    
    return False


def detect_successfactors(url: str) -> bool:
    """
    Detect if URL is a SAP SuccessFactors job posting.
    
    SAP SuccessFactors career sites typically use server-side rendering
    and work well with standard HTML extraction.
    
    Args:
        url: URL to check
    
    Returns:
        True if SAP SuccessFactors job posting
    """
    url_lower = url.lower()
    
    for pattern in SUCCESSFACTORS_PATTERNS:
        if re.search(pattern, url_lower):
            logger.debug(f"SAP SuccessFactors pattern matched: {pattern}")
            return True
    
    return False


def get_source_display_name(source: JobSource) -> str:
    """
    Get user-friendly display name for job source.
    
    Args:
        source: JobSource enum value
    
    Returns:
        Human-readable platform name
    """
    names = {
        "greenhouse": "Greenhouse",
        "lever": "Lever",
        "workday": "Workday",
        "apple": "Apple Careers",
        "icims": "iCIMS",
        "ashby": "AshbyHQ",
        "successfactors": "SAP SuccessFactors",
        "generic": "Generic Job Site"
    }
    return names.get(source, "Unknown")


def requires_javascript(source: JobSource) -> bool:
    """
    Check if platform requires JavaScript rendering.
    
    Args:
        source: JobSource enum value
    
    Returns:
        True if platform requires JavaScript to render content
    """
    characteristics = PLATFORM_CHARACTERISTICS.get(source, {})
    return characteristics.get("requires_js", False)


def has_schema_org(source: JobSource) -> bool:
    """
    Check if platform typically provides Schema.org structured data.
    
    Args:
        source: JobSource enum value
    
    Returns:
        True if platform typically provides Schema.org JobPosting data
    """
    characteristics = PLATFORM_CHARACTERISTICS.get(source, {})
    return characteristics.get("has_schema_org", False)


def get_extraction_priority(source: JobSource) -> list:
    """
    Get the recommended extraction method priority for a platform.
    
    Args:
        source: JobSource enum value
    
    Returns:
        List of extraction methods in priority order
    """
    characteristics = PLATFORM_CHARACTERISTICS.get(source, {})
    return characteristics.get("extraction_priority", ["schema", "html", "fallback"])
