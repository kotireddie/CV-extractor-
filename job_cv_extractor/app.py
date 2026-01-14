"""
Job CV Extractor - Streamlit Application

A local application that extracts CV-relevant intelligence from job posting URLs.
Combines web scraping, content extraction, and LLM analysis.
"""

import streamlit as st
import os
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import modules
from extractor.fetcher import fetch_url, is_valid_job_url
from extractor.html_parser import parse_html, extract_schema_job_posting
from extractor.content_cleaner import clean_html_content, is_meaningful_content
from extractor.fallback_extractor import get_best_extraction
from extractor.source_detector import detect_source, get_source_display_name
from extractor.url_resolver import resolve_url
from llm.analyzer import analyze_job_posting, JobAnalysisResult
from utils.keyword_ranker import rank_keywords, format_keywords_for_display
from utils.logger import logger, get_streamlit_logs, clear_streamlit_logs
from utils.test_tracker import tracker

# Page configuration
st.set_page_config(
    page_title="Job Intelligence Extractor",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E3A5F;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.3rem;
        font-weight: 600;
        color: #2C5282;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    .skill-tag {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        margin: 0.25rem;
        border-radius: 20px;
        font-size: 0.9rem;
    }
    .hard-skill {
        background-color: #E6F3FF;
        color: #1E3A5F;
        border: 1px solid #B3D9FF;
    }
    .soft-skill {
        background-color: #F0FFF4;
        color: #22543D;
        border: 1px solid #9AE6B4;
    }
    .ats-keyword {
        background-color: #FFF5E6;
        color: #744210;
        border: 1px solid #FBD38D;
    }
    .inferred-skill {
        background-color: #FAF5FF;
        color: #553C9A;
        border: 1px solid #D6BCFA;
    }
    .high-priority {
        background-color: #FED7D7;
        color: #822727;
        border: 1px solid #FC8181;
        font-weight: 600;
    }
    .stExpander {
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        margin-bottom: 0.5rem;
    }
    .log-info { color: #2B6CB0; }
    .log-warning { color: #C05621; }
    .log-error { color: #C53030; }
</style>
""", unsafe_allow_html=True)


def main():
    """Main application entry point."""
    
    # Header
    st.markdown('<p class="main-header">🎯 Job Intelligence Extractor</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Extract CV-relevant insights from any job posting URL</p>', unsafe_allow_html=True)
    
    # API Key input (in sidebar for cleaner UI)
    with st.sidebar:
        st.header("⚙️ Settings")
        api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            value=os.environ.get('OPENAI_API_KEY', ''),
            help="Your OpenAI API key. Can be set via .env file, OPENAI_API_KEY environment variable, or entered here."
        )
        
        model = st.selectbox(
            "Model",
            options=["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
            index=0,
            help="gpt-4o-mini is recommended for cost efficiency"
        )
        
        st.divider()
        
        # Show logs toggle
        show_logs = st.checkbox("Show processing logs", value=False)
    
    # Main input
    col1, col2 = st.columns([4, 1])
    
    with col1:
        url = st.text_input(
            "Job Posting URL",
            placeholder="https://www.linkedin.com/jobs/view/...",
            help="Paste the full URL of the job posting"
        )
    
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        extract_button = st.button("🔍 Extract", type="primary", use_container_width=True)
    
    # Process on button click
    if extract_button:
        if not url:
            st.error("Please enter a job posting URL")
            return
        
        if not api_key:
            st.error("Please provide an OpenAI API key in the sidebar")
            return
        
        # Clear previous logs
        clear_streamlit_logs()
        
        # Validate URL
        is_valid, error_msg = is_valid_job_url(url)
        if not is_valid:
            st.error(f"Invalid URL: {error_msg}")
            # Record failed validation
            tracker.record_run(
                url=url,
                status="failure",
                error_message=error_msg,
                error_type="URL Validation Error"
            )
            return
        
        # Process the URL
        result = process_job_url(url, api_key, model)
        
        if result and result.success:
            display_results(result, url)
            # Record successful run
            tracker.record_run(
                url=url,
                status="success",
                platform_detected=getattr(result, '_source_platform', None),
                extraction_method=getattr(result, '_extraction_method', None),
                resolved_url=getattr(result, '_resolved_url', url),
                was_resolved=getattr(result, '_was_resolved', False),
                content_length=len(getattr(result, '_job_text', '')),
                tokens_used=result.tokens_used,
                model_used=result.model_used or model,
                job_title=result.job_title,
                company=result.company,
                skills_extracted=len(result.hard_skills) + len(result.soft_skills) + len(result.inferred_skills),
                responsibilities_extracted=len(result.responsibilities),
                ats_keywords_extracted=len(result.ats_keywords)
            )
        elif result is None:
            # Record failed run (extraction failed) - errors already recorded in process_job_url
            pass
        
        # Show logs if enabled
        if show_logs:
            display_logs()
        
        # Show test history in sidebar
        display_test_history()
    
    # Footer
    st.divider()
    st.caption("💡 Tip: This tool extracts information to help tailor your CV. It does not store any data.")


def process_job_url(url: str, api_key: str, model: str) -> Optional[JobAnalysisResult]:
    """
    Process a job posting URL through the platform-aware extraction pipeline.
    
    Steps:
    1. Detect job source platform (Greenhouse, Lever, Workday, etc.)
    2. Resolve to canonical URL if needed
    3. Fetch HTML from resolved URL
    4. Try Schema.org extraction
    5. Parse and clean HTML
    6. Fallback to trafilatura if needed
    7. Analyze with LLM
    
    Args:
        url: Job posting URL
        api_key: OpenAI API key
        model: Model to use
    
    Returns:
        JobAnalysisResult or None on failure
    """
    # Create status container
    status = st.status("Extracting job intelligence...", expanded=True)
    
    with status:
        # Step 1: Detect job source platform
        st.write("🔎 Detecting job platform...")
        source = detect_source(url)
        source_name = get_source_display_name(source)
        
        if source != "generic":
            st.write(f"✅ Detected **{source_name}** job page")
        else:
            st.write("ℹ️ Using generic extraction strategy")
        
        # Step 2: Resolve to canonical URL
        st.write("🔗 Resolving canonical job URL...")
        resolved_url, was_resolved = resolve_url(url, source)
        
        if was_resolved:
            st.write(f"✅ Resolved to canonical URL")
            logger.info(f"URL resolved: {url} → {resolved_url}")
        else:
            st.write("ℹ️ Using original URL")
            logger.debug(f"URL unchanged: {url}")
        
        # Step 3: Fetch HTML from resolved URL
        st.write("📡 Fetching job posting...")
        fetch_result = fetch_url(resolved_url)
        
        if not fetch_result.success:
            # If resolved URL failed, try original URL as fallback
            if was_resolved and resolved_url != url:
                st.write("⚠️ Resolved URL failed, trying original...")
                logger.warning(f"Resolved URL fetch failed, falling back to original: {url}")
                fetch_result = fetch_url(url)
            
            if not fetch_result.success:
                error_msg = fetch_result.error_message
                st.error(f"Failed to fetch URL: {error_msg}")
                logger.error(f"URL fetch failed: {error_msg}")
                status.update(label="Extraction failed", state="error")
                # Record fetch failure
                tracker.record_run(
                    url=url,
                    status="failure",
                    platform_detected=source_name,
                    resolved_url=resolved_url if was_resolved else url,
                    was_resolved=was_resolved,
                    error_message=error_msg,
                    error_type="Fetch Error"
                )
                return None
        
        st.write(f"✅ Fetched {len(fetch_result.html):,} characters")
        
        # Step 4: Try Schema.org extraction
        st.write("🔍 Looking for structured job data...")
        schema_data = extract_schema_job_posting(fetch_result.html)
        
        job_text = ""
        extraction_method = ""
        
        if schema_data:
            st.write("✅ Found Schema.org JobPosting data")
            extraction_method = f"Schema.org JSON-LD ({source_name})"
            
            # Build text from schema data
            parts = []
            if schema_data.get('title'):
                parts.append(f"Job Title: {schema_data['title']}")
            if schema_data.get('company'):
                parts.append(f"Company: {schema_data['company']}")
            if schema_data.get('description'):
                parts.append(f"\nDescription:\n{schema_data['description']}")
            if schema_data.get('skills'):
                parts.append(f"\nSkills: {', '.join(schema_data['skills'])}")
            
            job_text = '\n'.join(parts)
        
        # Step 5: Parse HTML if schema didn't provide enough
        if len(job_text) < 200:
            st.write("📄 Parsing HTML content...")
            parsed = parse_html(fetch_result.html)
            cleaned = clean_html_content(fetch_result.html)
            
            if is_meaningful_content(cleaned):
                job_text = cleaned
                extraction_method = f"HTML parsing ({source_name})"
                st.write(f"✅ Extracted {len(job_text):,} characters of content")
            else:
                # Step 6: Fallback to trafilatura
                st.write("🔄 Using fallback extractor...")
                job_text = get_best_extraction(fetch_result.html, resolved_url)
                extraction_method = f"Trafilatura fallback ({source_name})"
                
                if job_text:
                    st.write(f"✅ Extracted {len(job_text):,} characters via fallback")
                else:
                    error_msg = "Could not extract meaningful content from the page"
                    st.error(error_msg)
                    logger.error(f"Content extraction failed for {resolved_url}")
                    status.update(label="Extraction failed", state="error")
                    # Record extraction failure
                    tracker.record_run(
                        url=url,
                        status="failure",
                        platform_detected=source_name,
                        extraction_method=f"Trafilatura fallback ({source_name})",
                        resolved_url=resolved_url if was_resolved else url,
                        was_resolved=was_resolved,
                        error_message=error_msg,
                        error_type="Content Extraction Error"
                    )
                    return None
        
        # Step 7: LLM Analysis
        st.write(f"🤖 Analyzing with {model}...")
        result = analyze_job_posting(job_text, api_key, model)
        
        if not result.success:
            error_msg = result.error_message or "LLM analysis failed"
            st.error(f"LLM analysis failed: {error_msg}")
            logger.error(f"LLM analysis error: {error_msg}")
            status.update(label="Analysis failed", state="error")
            # Record LLM analysis failure
            tracker.record_run(
                url=url,
                status="failure",
                platform_detected=source_name,
                extraction_method=extraction_method,
                resolved_url=resolved_url if was_resolved else url,
                was_resolved=was_resolved,
                content_length=len(job_text),
                error_message=error_msg,
                error_type="LLM Analysis Error",
                model_used=model
            )
            return None
        
        st.write("✅ Analysis complete!")
        
        if result.tokens_used:
            st.write(f"📊 Tokens used: {result.tokens_used:,}")
        
        # Store metadata for display
        result._extraction_method = extraction_method
        result._job_text = job_text
        result._source_platform = source_name
        result._resolved_url = resolved_url
        result._was_resolved = was_resolved
        
        status.update(label="Extraction complete!", state="complete")
    
    return result


def display_results(result: JobAnalysisResult, url: str):
    """Display the analysis results in a structured format."""
    
    st.divider()
    
    # Job title and company
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if result.job_title:
            st.markdown(f"## {result.job_title}")
        else:
            st.markdown("## Job Details")
    
    with col2:
        if result.company:
            st.markdown(f"**🏢 Company:** {result.company}")
        if result.seniority_level:
            st.markdown(f"**📊 Level:** {result.seniority_level}")
        if result.years_of_experience:
            st.markdown(f"**⏱️ Experience:** {result.years_of_experience}")
    
    # Job Summary
    if result.job_summary:
        st.markdown("### 📋 Summary")
        st.info(result.job_summary)
    
    # Main content in columns
    col1, col2 = st.columns(2)
    
    with col1:
        # Responsibilities
        with st.expander("📌 Responsibilities", expanded=True):
            if result.responsibilities:
                for resp in result.responsibilities:
                    st.markdown(f"• {resp}")
            else:
                st.write("No responsibilities extracted")
        
        # Hard Skills
        with st.expander("💻 Technical/Hard Skills", expanded=True):
            if result.hard_skills:
                skills_html = ' '.join([
                    f'<span class="skill-tag hard-skill">{skill}</span>'
                    for skill in result.hard_skills
                ])
                st.markdown(skills_html, unsafe_allow_html=True)
            else:
                st.write("No hard skills extracted")
        
        # Soft Skills
        with st.expander("🤝 Soft Skills", expanded=True):
            if result.soft_skills:
                skills_html = ' '.join([
                    f'<span class="skill-tag soft-skill">{skill}</span>'
                    for skill in result.soft_skills
                ])
                st.markdown(skills_html, unsafe_allow_html=True)
            else:
                st.write("No soft skills extracted")
    
    with col2:
        # ATS Keywords
        with st.expander("🎯 ATS Keywords", expanded=True):
            if result.ats_keywords:
                # Rank keywords with frequency analysis
                job_text = getattr(result, '_job_text', '')
                ranked = rank_keywords(job_text, result.ats_keywords)
                formatted = format_keywords_for_display(ranked)
                
                if formatted['high_priority']:
                    st.markdown("**High Priority:**")
                    keywords_html = ' '.join([
                        f'<span class="skill-tag high-priority">{kw}</span>'
                        for kw in formatted['high_priority'][:15]
                    ])
                    st.markdown(keywords_html, unsafe_allow_html=True)
                
                if formatted['medium_priority']:
                    st.markdown("**Medium Priority:**")
                    keywords_html = ' '.join([
                        f'<span class="skill-tag ats-keyword">{kw}</span>'
                        for kw in formatted['medium_priority'][:10]
                    ])
                    st.markdown(keywords_html, unsafe_allow_html=True)
                
                if formatted['other']:
                    st.markdown("**Other:**")
                    keywords_html = ' '.join([
                        f'<span class="skill-tag ats-keyword">{kw}</span>'
                        for kw in formatted['other'][:10]
                    ])
                    st.markdown(keywords_html, unsafe_allow_html=True)
            else:
                st.write("No ATS keywords extracted")
        
        # Inferred Skills
        with st.expander("💡 Inferred/Implied Skills", expanded=True):
            if result.inferred_skills:
                st.caption("Skills not explicitly stated but likely needed for this role:")
                skills_html = ' '.join([
                    f'<span class="skill-tag inferred-skill">{skill}</span>'
                    for skill in result.inferred_skills
                ])
                st.markdown(skills_html, unsafe_allow_html=True)
            else:
                st.write("No inferred skills identified")
    
    # Metadata
    with st.expander("ℹ️ Extraction Details"):
        source_platform = getattr(result, '_source_platform', 'Unknown')
        extraction_method = getattr(result, '_extraction_method', 'Unknown')
        resolved_url = getattr(result, '_resolved_url', url)
        was_resolved = getattr(result, '_was_resolved', False)
        
        st.markdown(f"**Platform Detected:** {source_platform}")
        st.markdown(f"**Extraction Method:** {extraction_method}")
        st.markdown(f"**Model Used:** {result.model_used or 'Unknown'}")
        st.markdown(f"**Tokens Used:** {result.tokens_used or 'Unknown'}")
        
        if was_resolved and resolved_url != url:
            st.markdown(f"**Original URL:** [{url}]({url})")
            st.markdown(f"**Resolved URL:** [{resolved_url}]({resolved_url})")
        else:
            st.markdown(f"**Source URL:** [{url}]({url})")


def display_logs():
    """Display processing logs."""
    st.divider()
    
    with st.expander("📋 Processing Logs", expanded=False):
        logs = get_streamlit_logs()
        
        if not logs:
            st.write("No logs to display")
            return
        
        for log in logs:
            level = log['level']
            msg = log['message']
            time = log['timestamp']
            
            if level == 'ERROR':
                st.markdown(f'<span class="log-error">❌ [{time}] {msg}</span>', unsafe_allow_html=True)
            elif level == 'WARNING':
                st.markdown(f'<span class="log-warning">⚠️ [{time}] {msg}</span>', unsafe_allow_html=True)
            else:
                st.markdown(f'<span class="log-info">ℹ️ [{time}] {msg}</span>', unsafe_allow_html=True)


def display_test_history():
    """Display test run history and statistics."""
    stats = tracker.get_stats()
    
    if stats['total_runs'] == 0:
        return
    
    with st.sidebar:
        st.divider()
        st.header("📊 Test History")
        
        # Statistics
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Runs", stats['total_runs'])
            st.metric("Success Rate", f"{stats['success_rate']:.1f}%")
        with col2:
            st.metric("Success", stats['success'])
            st.metric("Failures", stats['failure'])
        
        # Platform breakdown
        if stats['platforms']:
            st.subheader("Platforms Tested")
            for platform, count in sorted(stats['platforms'].items(), key=lambda x: x[1], reverse=True):
                st.write(f"• **{platform}**: {count}")
        
        # Error types
        if stats['error_types']:
            st.subheader("Error Types")
            for error_type, count in sorted(stats['error_types'].items(), key=lambda x: x[1], reverse=True):
                st.write(f"• **{error_type}**: {count}")
        
        # Recent runs
        with st.expander("📝 Recent Test Runs", expanded=False):
            recent_runs = tracker.get_runs(limit=10)
            if recent_runs:
                for run in reversed(recent_runs[-10:]):
                    status_icon = "✅" if run.status == "success" else "❌" if run.status == "failure" else "⚠️"
                    status_color = "green" if run.status == "success" else "red" if run.status == "failure" else "orange"
                    
                    # Format timestamp
                    try:
                        dt = datetime.fromisoformat(run.timestamp)
                        time_str = dt.strftime("%m/%d %H:%M")
                    except:
                        time_str = run.timestamp[:16]
                    
                    st.markdown(f"{status_icon} **{time_str}**")
                    st.caption(f"[{run.url[:50]}...]({run.url})" if len(run.url) > 50 else f"[{run.url}]({run.url})")
                    
                    if run.job_title:
                        st.write(f"  • {run.job_title}")
                    if run.error_message:
                        st.error(f"  Error: {run.error_message[:100]}")
                    st.write("---")
            else:
                st.write("No test runs yet")
        
        # Export button
        if st.button("📥 Export Test Data", use_container_width=True):
            runs = tracker.get_runs()
            import json
            export_data = {
                'exported_at': datetime.now().isoformat(),
                'total_runs': len(runs),
                'statistics': stats,
                'runs': [run.to_dict() for run in runs]
            }
            st.download_button(
                label="Download JSON",
                data=json.dumps(export_data, indent=2, ensure_ascii=False),
                file_name=f"test_runs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )
        
        # Clear history button
        if st.button("🗑️ Clear History", use_container_width=True):
            tracker.clear_runs()
            st.success("Test history cleared!")
            st.rerun()


if __name__ == "__main__":
    main()
