#!/usr/bin/env python3
"""
Test script to verify all job URL extractions work with the updated pipeline
"""

import sys
import os
from pathlib import Path
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from extractor.fetcher import fetch_url, smart_fetch, detect_js_required
from extractor.source_detector import detect_source, get_source_display_name, requires_javascript, has_schema_org
from extractor.url_resolver import resolve_url
from extractor.html_parser import parse_html, extract_schema_job_posting
from extractor.content_cleaner import clean_html_content, is_meaningful_content
from extractor.fallback_extractor import get_best_extraction
from utils.logger import logger

# Check browser availability
try:
    from extractor.browser_fetcher import is_browser_available, get_platform_fetcher
    BROWSER_AVAILABLE = is_browser_available()
except ImportError:
    BROWSER_AVAILABLE = False

TEST_URLS = [
    {
        "name": "Apple Careers",
        "url": "https://jobs.apple.com/en-us/details/200630587-3956/data-analyst-strategic-data-solutions?team=OPMFG"
    },
    {
        "name": "iCIMS (AttainFinance)",
        "url": "https://careers-attainfinance.icims.com/jobs/9403/database-engineer/job?mobile=false&width=1290&height=500&bga=true&needsRedirect=false&jan1offset=-360&jun1offset=-300"
    },
    {
        "name": "AshbyHQ (First Resonance)",
        "url": "https://jobs.ashbyhq.com/first-resonance/0492a694-d7f2-47a7-940c-9a8a2f8c7bf0"
    },
    {
        "name": "Tractor Supply (SAP SuccessFactors)",
        "url": "https://www.tractorsupply.careers/job/Brentwood-Data-Scientist%2C-Merchandising-Analytics-TN-37027/1338676300/"
    },
    {
        "name": "AshbyHQ (Braintrust)",
        "url": "https://jobs.ashbyhq.com/Braintrust/f6b07ffd-a793-49df-8815-6230735f482a?utm_source=portfoliojobs.a16z.com"
    }
]

def test_url(url_info):
    """Test a single URL with the new extraction pipeline."""
    name = url_info["name"]
    url = url_info["url"]
    
    print(f"\n{'='*80}")
    print(f"TESTING: {name}")
    print(f"{'='*80}")
    print(f"URL: {url}\n")
    
    results = {
        "name": name,
        "url": url,
        "timestamp": datetime.now().isoformat()
    }
    
    # Step 1: Source Detection
    print("Step 1: Source Detection")
    print("-" * 40)
    source = detect_source(url)
    source_name = get_source_display_name(source)
    needs_js = requires_javascript(source)
    expects_schema = has_schema_org(source)
    
    results['source_detection'] = {
        'source': source,
        'display_name': source_name,
        'requires_js': needs_js,
        'has_schema_org': expects_schema
    }
    print(f"Platform: {source_name}")
    print(f"Requires JavaScript: {needs_js}")
    print(f"Expected Schema.org: {expects_schema}")
    print()
    
    # Step 2: URL Resolution
    resolved_url, was_resolved = resolve_url(url, source)
    results['url_resolution'] = {'was_resolved': was_resolved}
    
    # Step 3: Standard HTTP Fetch
    print("Step 2: Standard HTTP Fetch")
    print("-" * 40)
    fetch_result = fetch_url(resolved_url)
    results['http_fetch'] = {
        'success': fetch_result.success,
        'html_length': len(fetch_result.html) if fetch_result.html else 0
    }
    print(f"Success: {fetch_result.success}")
    print(f"HTML Length: {len(fetch_result.html) if fetch_result.html else 0:,} chars")
    print()
    
    if not fetch_result.success:
        results['status'] = 'FAILED - HTTP Fetch Error'
        return results
    
    job_text = ""
    extraction_method = ""
    fetch_method = "HTTP"
    
    # Step 4: Schema.org Extraction
    print("Step 3: Schema.org Extraction")
    print("-" * 40)
    schema_data = extract_schema_job_posting(fetch_result.html)
    
    if schema_data:
        print(f"✅ Found Schema.org data")
        print(f"   Title: {schema_data.get('title', 'N/A')}")
        print(f"   Company: {schema_data.get('company', 'N/A')}")
        print(f"   Description: {len(schema_data.get('description', '')):,} chars")
        
        # Build text from schema
        parts = []
        if schema_data.get('title'):
            parts.append(f"Job Title: {schema_data['title']}")
        if schema_data.get('company'):
            parts.append(f"Company: {schema_data['company']}")
        if schema_data.get('description'):
            parts.append(f"\nDescription:\n{schema_data['description']}")
        job_text = '\n'.join(parts)
        extraction_method = f"Schema.org ({source_name})"
    else:
        print("❌ No Schema.org data found")
    print()
    
    results['schema_extraction'] = {
        'found': schema_data is not None,
        'content_length': len(job_text)
    }
    
    # Step 5: HTML Cleaning (if needed)
    if len(job_text) < 200:
        print("Step 4: HTML Cleaning")
        print("-" * 40)
        cleaned = clean_html_content(fetch_result.html)
        is_meaningful = is_meaningful_content(cleaned)
        
        results['html_cleaning'] = {
            'cleaned_length': len(cleaned),
            'is_meaningful': is_meaningful
        }
        
        if is_meaningful:
            print(f"✅ Extracted {len(cleaned):,} chars of meaningful content")
            job_text = cleaned
            extraction_method = f"HTML Cleaning ({source_name})"
        else:
            print(f"❌ Only {len(cleaned):,} chars (not meaningful)")
        print()
    
    # Step 6: Trafilatura Fallback (if needed)
    if len(job_text) < 200:
        print("Step 5: Trafilatura Fallback")
        print("-" * 40)
        fallback = get_best_extraction(fetch_result.html, resolved_url)
        
        results['fallback_extraction'] = {
            'content_length': len(fallback) if fallback else 0
        }
        
        if fallback and len(fallback) >= 200:
            print(f"✅ Extracted {len(fallback):,} chars via Trafilatura")
            job_text = fallback
            extraction_method = f"Trafilatura ({source_name})"
        else:
            print(f"❌ Fallback got {len(fallback) if fallback else 0:,} chars")
        print()
    
    # Step 7: Browser Fetch (if needed and available)
    if len(job_text) < 200:
        js_detected = detect_js_required(fetch_result.html)
        
        if needs_js or js_detected:
            print("Step 6: Browser Fetch (JavaScript Rendering)")
            print("-" * 40)
            
            if BROWSER_AVAILABLE:
                print("🌐 Attempting browser fetch...")
                try:
                    fetcher = get_platform_fetcher(source)
                    browser_result = fetcher(resolved_url)
                    
                    results['browser_fetch'] = {
                        'success': browser_result.success,
                        'html_length': len(browser_result.html) if browser_result.html else 0
                    }
                    
                    if browser_result.success and browser_result.html:
                        print(f"✅ Browser fetched {len(browser_result.html):,} chars")
                        fetch_method = "Browser"
                        
                        # Try Schema.org on browser content
                        browser_schema = extract_schema_job_posting(browser_result.html)
                        if browser_schema and browser_schema.get('description'):
                            parts = []
                            if browser_schema.get('title'):
                                parts.append(f"Job Title: {browser_schema['title']}")
                            if browser_schema.get('company'):
                                parts.append(f"Company: {browser_schema['company']}")
                            if browser_schema.get('description'):
                                parts.append(f"\nDescription:\n{browser_schema['description']}")
                            job_text = '\n'.join(parts)
                            extraction_method = f"Browser + Schema.org ({source_name})"
                            print(f"✅ Found Schema.org in browser content")
                        else:
                            # Try HTML cleaning
                            browser_cleaned = clean_html_content(browser_result.html)
                            if is_meaningful_content(browser_cleaned):
                                job_text = browser_cleaned
                                extraction_method = f"Browser + HTML ({source_name})"
                                print(f"✅ Cleaned {len(job_text):,} chars from browser content")
                            else:
                                # Try trafilatura
                                browser_fallback = get_best_extraction(browser_result.html, resolved_url)
                                if browser_fallback and len(browser_fallback) >= 200:
                                    job_text = browser_fallback
                                    extraction_method = f"Browser + Trafilatura ({source_name})"
                                    print(f"✅ Trafilatura got {len(job_text):,} chars from browser content")
                    else:
                        print(f"❌ Browser fetch failed: {browser_result.error_message}")
                except Exception as e:
                    print(f"❌ Browser error: {str(e)}")
                    results['browser_fetch'] = {'error': str(e)}
            else:
                print("⚠️ Browser not available - Playwright not installed")
                results['browser_fetch'] = {'available': False}
            print()
    
    # Final Results
    print("="*40)
    print("FINAL RESULTS")
    print("="*40)
    
    results['final'] = {
        'content_length': len(job_text),
        'extraction_method': extraction_method,
        'fetch_method': fetch_method
    }
    
    if len(job_text) >= 200:
        results['status'] = 'SUCCESS'
        print(f"✅ SUCCESS")
        print(f"   Extraction Method: {extraction_method}")
        print(f"   Fetch Method: {fetch_method}")
        print(f"   Content Length: {len(job_text):,} chars")
        print(f"\n   Content Preview:")
        print(f"   {job_text[:300]}...")
    else:
        results['status'] = 'FAILED'
        print(f"❌ FAILED - Only {len(job_text):,} chars extracted")
        if needs_js and not BROWSER_AVAILABLE:
            print("   → This platform requires JavaScript. Install Playwright:")
            print("     pip install playwright && playwright install chromium")
    
    return results


def main():
    """Test all URLs."""
    print("="*80)
    print("JOB CV EXTRACTOR - COMPREHENSIVE URL TEST")
    print("="*80)
    print(f"Browser Available: {BROWSER_AVAILABLE}")
    print(f"Testing {len(TEST_URLS)} URLs")
    print("="*80)
    
    all_results = []
    
    for url_info in TEST_URLS:
        try:
            result = test_url(url_info)
            all_results.append(result)
        except Exception as e:
            print(f"\n❌ ERROR testing {url_info['name']}: {str(e)}")
            import traceback
            traceback.print_exc()
            all_results.append({
                "name": url_info["name"],
                "url": url_info["url"],
                "status": "ERROR",
                "error": str(e)
            })
    
    # Save results
    output_file = project_root / "comprehensive_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    success_count = sum(1 for r in all_results if r.get('status') == 'SUCCESS')
    failed_count = sum(1 for r in all_results if r.get('status') == 'FAILED')
    error_count = sum(1 for r in all_results if r.get('status') == 'ERROR')
    
    for result in all_results:
        status = result.get('status', 'UNKNOWN')
        name = result.get('name', 'Unknown')
        method = result.get('final', {}).get('extraction_method', 'N/A')
        icon = "✅" if status == "SUCCESS" else "❌"
        print(f"{icon} {name}: {status}")
        if status == "SUCCESS":
            print(f"   Method: {method}")
    
    print(f"\nTotal: {success_count} SUCCESS, {failed_count} FAILED, {error_count} ERROR")
    print(f"Success Rate: {success_count}/{len(all_results)} ({100*success_count/len(all_results):.1f}%)")
    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
