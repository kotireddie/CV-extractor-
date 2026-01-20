# Test Tracking - Apple Job URL Extraction Analysis

## Test URL
**URL:** `https://jobs.apple.com/en-us/details/200630587-3956/data-analyst-strategic-data-solutions?team=OPMFG`

**Date:** 2025-01-27

**Status:** ❌ **EXTRACTION FAILED**

---

## Test Results Summary

### Step-by-Step Analysis

#### 1. URL Validation ✅
- **Status:** Valid
- **Result:** URL passed basic validation checks
- **Error:** None

#### 2. Source Detection ⚠️
- **Detected Source:** `generic` (Generic Job Site)
- **Display Name:** "Generic Job Site"
- **Issue:** Apple job URLs are not specifically detected as a supported platform
- **Impact:** No platform-specific extraction logic is applied

#### 3. URL Resolution ℹ️
- **Original URL:** `https://jobs.apple.com/en-us/details/200630587-3956/data-analyst-strategic-data-solutions?team=OPMFG`
- **Resolved URL:** Same as original (no resolution needed)
- **Was Resolved:** False
- **Status:** Normal for generic URLs

#### 4. HTML Fetching ✅
- **Status:** Success
- **HTTP Status Code:** 200
- **HTML Length:** 191,116 characters
- **Final URL:** Same as original
- **Result:** HTML was successfully fetched

#### 5. Schema.org Extraction ❌
- **Status:** Failed
- **Schema.org JobPosting Found:** No
- **Issue:** Apple job pages do not include Schema.org JobPosting JSON-LD structured data
- **Impact:** Cannot use structured data extraction method

#### 6. HTML Parsing ⚠️
- **Status:** Partial Success
- **Page Title Extracted:** ✅ "Data Analyst - Strategic Data Solutions - Jobs - Careers at Apple"
- **Meta Description Extracted:** ✅ "Apply for a Data Analyst - Strategic Data Solutions job at Apple. Read about the role and find out if it's right for you."
- **Content Length:** 0 characters
- **Issue:** HTML parser found the page shell but no actual job description content

#### 7. Content Cleaning ❌
- **Cleaned Length:** 65 characters
- **Is Meaningful:** False (minimum 200 chars required)
- **Extracted Content:** Only page title
- **Issue:** Content cleaner only found navigation/header text, not the job description

#### 8. Fallback Extraction ❌
- **Trafilatura Available:** No (not installed)
- **Content Extracted:** 0 characters
- **Issue:** Fallback extraction method not available

---

## Root Cause Analysis

### Primary Issue: JavaScript-Dependent Content Loading

**Problem:** Apple's job posting pages are **Single Page Applications (SPAs)** that load content dynamically via JavaScript after the initial HTML is served.

**Evidence:**
1. ✅ HTML fetch succeeds (191KB of HTML retrieved)
2. ✅ Page title and meta tags are present in HTML
3. ❌ Body text contains only: "Please enable Javascript in your browser for best experience"
4. ❌ No job description, responsibilities, or requirements found in static HTML
5. ❌ Keywords like "responsibilities", "requirements", "qualifications" exist in HTML but are not in readable text format
6. ✅ HTML contains React/Vue app root element (`id="root"` or `id="app"`)
7. ❌ No Schema.org structured data present
8. ❌ No embedded JSON data with job description found in script tags

### Technical Details

1. **Page Structure:**
   - The HTML is a shell that contains:
     - Page metadata (title, description)
     - Navigation elements
     - Footer content
     - JavaScript bundles
     - A root element for the React/Vue application
   - The actual job description is rendered client-side after JavaScript executes

2. **Content Loading Mechanism:**
   - Apple uses a modern JavaScript framework (likely React based on patterns)
   - Job data is likely fetched via API calls after page load
   - Content is rendered into the DOM dynamically

3. **Why Current Extraction Fails:**
   - The application uses `requests.get()` which only fetches static HTML
   - JavaScript execution is required to render the job description
   - No server-side rendering (SSR) provides the content in the initial HTML
   - No embedded JSON data contains the full job description

---

## Impact Assessment

### What Works ✅
- URL validation
- HTML fetching
- Page title extraction
- Meta description extraction

### What Doesn't Work ❌
- Job description extraction
- Responsibilities extraction
- Requirements/qualifications extraction
- Skills extraction
- Any meaningful job content extraction

### Current Extraction Result
- **Best Extraction Method:** None - Extraction Failed
- **Content Length:** 0 characters
- **Meaningful Content:** None

---

## Recommendations

### Option 1: Add Headless Browser Support (Recommended)
**Use Selenium or Playwright to render JavaScript before extraction**

**Pros:**
- Can handle all JavaScript-rendered content
- Works with modern SPAs
- Most comprehensive solution

**Cons:**
- Requires additional dependencies
- Slower than static HTML fetching
- More resource-intensive

**Implementation:**
```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--headless')
driver = webdriver.Chrome(options=options)
driver.get(url)
html = driver.page_source  # Now contains rendered content
driver.quit()
```

### Option 2: Check for Apple-Specific API Endpoints
**Investigate if Apple provides a JSON API for job data**

**Pros:**
- Fast and efficient
- Structured data format
- No JavaScript rendering needed

**Cons:**
- May not exist
- May require authentication
- May be rate-limited

**Investigation Needed:**
- Check browser network requests when loading Apple job page
- Look for API endpoints like `/api/jobs/{id}` or similar
- Check if job data is available via API

### Option 3: Add Apple-Specific Detection and Handling
**Create specialized extraction logic for Apple job pages**

**Pros:**
- Can optimize for Apple's specific structure
- May find alternative data sources

**Cons:**
- Still won't solve JavaScript rendering issue
- Requires maintenance for Apple site changes

**If API exists:**
- Detect Apple URLs specifically
- Extract job ID from URL
- Fetch from API endpoint instead of HTML

### Option 4: Use Trafilatura with Rendered HTML
**Install trafilatura and use it with headless browser**

**Pros:**
- Trafilatura is good at extracting main content
- Works well with rendered HTML

**Cons:**
- Still requires headless browser
- May not work if content is deeply nested in React components

---

## Next Steps

1. **Immediate:** Install trafilatura to enable fallback extraction
   ```bash
   pip install trafilatura
   ```

2. **Short-term:** Investigate Apple job API endpoints
   - Use browser developer tools to inspect network requests
   - Check if job data is available via API

3. **Long-term:** Implement headless browser support
   - Add Selenium or Playwright as optional dependency
   - Create new extraction method for JavaScript-rendered pages
   - Add configuration option to enable/disable JS rendering

---

## Test Data Files

- **Test Results JSON:** `apple_url_test_results.json`
- **Test Script:** `test_apple_url.py`

---

## Related Issues

- Generic extraction strategy may fail for other modern SPA-based job sites
- Consider adding a "JavaScript Required" detection mechanism
- May need to update `is_meaningful_content()` to better detect empty shells

---

## Conclusion

The Apple job URL extraction fails because Apple's job pages are JavaScript-dependent Single Page Applications. The current static HTML fetching approach cannot extract the job description, which is rendered client-side. To fix this, the application needs to either:

1. Use a headless browser to render JavaScript (recommended)
2. Find and use an Apple job API endpoint (if available)
3. Implement a hybrid approach that detects JavaScript-dependent pages and uses appropriate extraction method

---

# Additional URL Tests - Multiple Job Platforms

**Date:** 2025-01-27

**Tested URLs:** 4 additional job posting URLs from different platforms

---

## Test Summary

| Platform | URL | Status | Extraction Method | Content Length |
|----------|-----|--------|------------------|----------------|
| iCIMS (AttainFinance) | careers-attainfinance.icims.com | ❌ FAILED | None | 0 chars |
| AshbyHQ (First Resonance) | jobs.ashbyhq.com/first-resonance | ✅ SUCCESS | Schema.org | 5,981 chars |
| Tractor Supply (SAP SuccessFactors) | tractorsupply.careers | ✅ SUCCESS | HTML Cleaning | 6,891 chars |
| AshbyHQ (Braintrust) | jobs.ashbyhq.com/Braintrust | ✅ SUCCESS | Schema.org | 4,621 chars |

**Success Rate:** 3 out of 4 URLs (75%)

---

## 1. iCIMS (AttainFinance) - Database Engineer

**URL:** `https://careers-attainfinance.icims.com/jobs/9403/database-engineer/job?mobile=false&width=1290&height=500&bga=true&needsRedirect=false&jan1offset=-360&jun1offset=-300`

**Status:** ❌ **EXTRACTION FAILED**

### Test Results

#### Step-by-Step Analysis

1. **URL Validation:** ✅ Valid
2. **Source Detection:** ⚠️ Generic (not specifically detected)
3. **URL Resolution:** ℹ️ No resolution needed
4. **HTML Fetching:** ✅ Success (45,903 characters fetched)
5. **Schema.org Extraction:** ❌ No Schema.org data found
6. **HTML Parsing:** ⚠️ Partial - Only navigation/footer content (297 chars)
7. **Content Cleaning:** ❌ Failed (0 chars - all content removed as boilerplate)
8. **Fallback Extraction:** ❌ Trafilatura not available

### Root Cause Analysis

**Problem:** iCIMS job pages appear to be JavaScript-dependent Single Page Applications.

**Evidence:**
- HTML fetch succeeds (45KB retrieved)
- Only navigation and footer content found in static HTML
- No job description, responsibilities, or requirements in readable format
- Content cleaner removed all content as boilerplate
- Page title is `None` (not found in HTML)

**Technical Details:**
- iCIMS is a popular ATS (Applicant Tracking System) platform
- Uses modern JavaScript frameworks for dynamic content rendering
- Job content is likely loaded via API calls after initial page load
- Similar issue to Apple job pages - requires JavaScript execution

### Recommendations

1. **Add iCIMS-specific detection** - Detect `*.icims.com` URLs
2. **Investigate iCIMS API** - Check if job data is available via API endpoints
3. **Use headless browser** - Render JavaScript to access dynamic content
4. **Check for embedded data** - Look for JSON data in script tags or data attributes

---

## 2. AshbyHQ (First Resonance) - Senior Data Engineer

**URL:** `https://jobs.ashbyhq.com/first-resonance/0492a694-d7f2-47a7-940c-9a8a2f8c7bf0`

**Status:** ✅ **EXTRACTION SUCCESS**

### Test Results

#### Step-by-Step Analysis

1. **URL Validation:** ✅ Valid
2. **Source Detection:** ⚠️ Generic (not specifically detected)
3. **URL Resolution:** ℹ️ No resolution needed
4. **HTML Fetching:** ✅ Success (67,599 characters fetched)
5. **Schema.org Extraction:** ✅ **SUCCESS** - Found JobPosting JSON-LD
6. **HTML Parsing:** ⚠️ Partial - JavaScript required message (46 chars)
7. **Content Cleaning:** ❌ Failed (0 chars - JavaScript-dependent)
8. **Fallback Extraction:** ❌ Trafilatura not available

### Extraction Details

**Best Method:** Schema.org JSON-LD extraction

**Extracted Data:**
- **Title:** Senior Data Engineer
- **Company:** First Resonance
- **Location:** Los Angeles, CA, United States
- **Employment Type:** FULL_TIME
- **Date Posted:** 2025-09-02
- **Salary:** USD 150,000 - 180,000 per YEAR
- **Description Length:** 5,981 characters

**Content Quality:** ✅ Excellent - Full job description with responsibilities, qualifications, and benefits

### Key Findings

**Why It Worked:**
- ✅ AshbyHQ includes Schema.org JobPosting structured data in HTML
- ✅ Schema.org extraction successfully parsed the JSON-LD data
- ✅ Complete job description available in structured format
- ✅ Includes HTML-formatted content with proper structure

**Note:** While the page requires JavaScript for rendering, AshbyHQ embeds the full job data in Schema.org format, making it accessible without JavaScript execution.

### Recommendations

1. **Add AshbyHQ detection** - Detect `jobs.ashbyhq.com` URLs for better platform identification
2. **Prioritize Schema.org extraction** - This platform demonstrates best practices
3. **No changes needed** - Current extraction works perfectly for AshbyHQ

---

## 3. Tractor Supply (SAP SuccessFactors) - Data Scientist

**URL:** `https://www.tractorsupply.careers/job/Brentwood-Data-Scientist%2C-Merchandising-Analytics-TN-37027/1338676300/`

**Status:** ✅ **EXTRACTION SUCCESS**

### Test Results

#### Step-by-Step Analysis

1. **URL Validation:** ✅ Valid
2. **Source Detection:** ⚠️ Generic (not specifically detected)
3. **URL Resolution:** ℹ️ No resolution needed
4. **HTML Fetching:** ✅ Success (94,804 characters fetched)
5. **Schema.org Extraction:** ❌ No Schema.org data found
6. **HTML Parsing:** ✅ Success (7,610 characters parsed)
7. **Content Cleaning:** ✅ **SUCCESS** - Meaningful content extracted (6,891 chars)
8. **Fallback Extraction:** ❌ Trafilatura not available (not needed)

### Extraction Details

**Best Method:** HTML Cleaning

**Extracted Content:**
- **Page Title:** Data Scientist, Merchandising Analytics Job Details | Tractor Supply Company
- **Content Length:** 6,891 characters
- **Is Meaningful:** ✅ Yes (passed validation)

**Content Quality:** ✅ Excellent - Full job description including:
- Overall Job Summary
- Essential Duties and Responsibilities
- Required Qualifications
- Preferred knowledge, skills, or abilities
- Working Conditions
- Physical Requirements
- Company Info

### Key Findings

**Why It Worked:**
- ✅ SAP SuccessFactors provides server-side rendered HTML
- ✅ Job content is present in static HTML (no JavaScript required)
- ✅ HTML cleaning successfully removed boilerplate while preserving job content
- ✅ Content validation passed (found job-related keywords)

**Technical Details:**
- Uses traditional server-side rendering
- Content is immediately available in HTML
- No JavaScript dependency for content access
- Well-structured HTML with semantic elements

### Recommendations

1. **Add SAP SuccessFactors detection** - Detect `*.careers` domains using SuccessFactors
2. **No changes needed** - Current HTML cleaning works well for this platform
3. **Consider adding SuccessFactors-specific selectors** - May improve extraction quality further

---

## 4. AshbyHQ (Braintrust) - Technical Recruiter

**URL:** `https://jobs.ashbyhq.com/Braintrust/f6b07ffd-a793-49df-8815-6230735f482a?utm_source=portfoliojobs.a16z.com`

**Status:** ✅ **EXTRACTION SUCCESS**

### Test Results

#### Step-by-Step Analysis

1. **URL Validation:** ✅ Valid
2. **Source Detection:** ⚠️ Generic (not specifically detected)
3. **URL Resolution:** ℹ️ No resolution needed
4. **HTML Fetching:** ✅ Success (68,068 characters fetched)
5. **Schema.org Extraction:** ✅ **SUCCESS** - Found JobPosting JSON-LD
6. **HTML Parsing:** ⚠️ Partial - JavaScript required message (46 chars)
7. **Content Cleaning:** ❌ Failed (0 chars - JavaScript-dependent)
8. **Fallback Extraction:** ❌ Trafilatura not available

### Extraction Details

**Best Method:** Schema.org JSON-LD extraction

**Extracted Data:**
- **Title:** Technical Recruiter
- **Company:** Braintrust
- **Location:** United States; United States
- **Employment Type:** FULL_TIME
- **Date Posted:** 2025-12-30
- **Description Length:** 4,621 characters

**Content Quality:** ✅ Excellent - Full job description with:
- About the company
- About the role
- What you'll do (responsibilities)
- Ideal candidate credentials
- Benefits include
- Equal opportunity statement

### Key Findings

**Why It Worked:**
- ✅ Same platform as First Resonance (AshbyHQ)
- ✅ Consistent Schema.org implementation across all AshbyHQ job postings
- ✅ Complete job data available in structured format
- ✅ HTML-formatted content with proper structure

**Consistency:** Both AshbyHQ URLs tested successfully extracted content using Schema.org, demonstrating platform consistency.

### Recommendations

1. **Add AshbyHQ platform detection** - Both AshbyHQ URLs worked identically
2. **Prioritize Schema.org for AshbyHQ** - This is the most reliable method for this platform
3. **No changes needed** - Current extraction works perfectly

---

## Comparative Analysis

### Platform Comparison

| Platform | JavaScript Required | Schema.org | HTML Content | Extraction Method | Success |
|----------|---------------------|------------|--------------|------------------|---------|
| Apple | ✅ Yes | ❌ No | ❌ No | None | ❌ Failed |
| iCIMS | ✅ Yes | ❌ No | ❌ No | None | ❌ Failed |
| AshbyHQ | ✅ Yes | ✅ Yes | ❌ No | Schema.org | ✅ Success |
| SAP SuccessFactors | ❌ No | ❌ No | ✅ Yes | HTML Cleaning | ✅ Success |

### Key Insights

1. **Schema.org is the best method** - When available, provides complete, structured data
2. **JavaScript-dependent pages can still work** - If they include Schema.org data
3. **Server-side rendering works well** - Traditional HTML extraction works for platforms like SAP SuccessFactors
4. **Platform detection matters** - Some platforms consistently use certain methods

### Success Patterns

**✅ Successful Extraction:**
- **AshbyHQ:** Uses Schema.org JSON-LD (works despite JavaScript requirement)
- **SAP SuccessFactors:** Server-side rendered HTML (works with HTML cleaning)

**❌ Failed Extraction:**
- **Apple:** JavaScript-dependent SPA without Schema.org
- **iCIMS:** JavaScript-dependent SPA without Schema.org

---

## Overall Recommendations

### Immediate Actions

1. **Install Trafilatura** - Enable fallback extraction for edge cases
   ```bash
   pip install trafilatura
   ```

2. **Add Platform Detection** - Improve detection for:
   - `jobs.ashbyhq.com` → AshbyHQ platform
   - `*.icims.com` → iCIMS platform
   - `*.careers` (SAP SuccessFactors) → SuccessFactors platform
   - `jobs.apple.com` → Apple platform

3. **Prioritize Schema.org** - Always check for Schema.org first (fastest and most reliable)

### Long-term Improvements

1. **Headless Browser Support** - For JavaScript-dependent pages without Schema.org
2. **Platform-Specific APIs** - Investigate API endpoints for major platforms
3. **Hybrid Approach** - Combine multiple extraction methods based on platform detection

---

## Test Data Files

- **Test Results JSON:** `multiple_urls_test_results.json`
- **Test Script:** `test_multiple_urls.py`
- **Previous Apple Test:** `apple_url_test_results.json`

---

## Conclusion

**Overall Success Rate:** 3 out of 5 URLs tested (60%) → **NOW 5 out of 5 (100%)** after updates!

**Key Takeaway:** The application successfully extracts job content from platforms that either:
1. Include Schema.org structured data (AshbyHQ)
2. Provide server-side rendered HTML (SAP SuccessFactors)

**Main Challenge:** JavaScript-dependent Single Page Applications without Schema.org data (Apple, iCIMS) require headless browser support for successful extraction.

**Next Priority:** Implement headless browser support or investigate API endpoints for platforms that currently fail.

---

# UPDATED: Implementation Complete - 100% Success Rate

**Date:** 2026-01-19

## Changes Made

### 1. Platform Detection (`extractor/source_detector.py`)
Added detection for new platforms:
- **Apple Careers** (`jobs.apple.com`)
- **iCIMS** (`*.icims.com`)
- **AshbyHQ** (`jobs.ashbyhq.com`)
- **SAP SuccessFactors** (`*.careers`, `successfactors.com`)

Added platform characteristics:
- `requires_javascript()` - Indicates if platform needs browser rendering
- `has_schema_org()` - Indicates if platform provides Schema.org data
- `get_extraction_priority()` - Returns recommended extraction method order

### 2. Headless Browser Module (`extractor/browser_fetcher.py`)
New module for JavaScript-rendered content extraction using Playwright:
- `fetch_with_browser()` - Generic browser fetch function
- `fetch_apple_jobs()` - Specialized Apple Careers fetcher with extended wait times
- `fetch_icims_jobs()` - Specialized iCIMS fetcher with iframe support
- `fetch_workday_jobs()` - Specialized Workday fetcher

### 3. Smart Fetching (`extractor/fetcher.py`)
Updated to support intelligent fetch method selection:
- `smart_fetch()` - Chooses HTTP or browser based on platform
- `detect_js_required()` - Detects if page requires JavaScript
- Auto-fallback from browser to HTTP if browser unavailable

### 4. App Pipeline (`app.py`)
Updated extraction pipeline:
1. Detect platform and check if JS required
2. Try standard HTTP fetch first (fast)
3. Try Schema.org extraction (works even for some JS pages)
4. Try HTML cleaning
5. Try Trafilatura fallback
6. If still no content and JS required, try browser fetch
7. Analyze with LLM

### 5. Requirements (`requirements.txt`)
Added:
- `playwright>=1.40.0` - Headless browser for JS rendering
- `lxml_html_clean` - Required for trafilatura

## Final Test Results

| URL | Platform | Method | Content | Status |
|-----|----------|--------|---------|--------|
| Apple Careers | Apple | Browser + Trafilatura | 362 chars | ✅ SUCCESS |
| iCIMS (AttainFinance) | iCIMS | Browser + Schema.org | 8,561 chars | ✅ SUCCESS |
| AshbyHQ (First Resonance) | AshbyHQ | Schema.org | 6,052 chars | ✅ SUCCESS |
| Tractor Supply | SAP SuccessFactors | HTML Cleaning | 6,891 chars | ✅ SUCCESS |
| AshbyHQ (Braintrust) | AshbyHQ | Schema.org | 4,686 chars | ✅ SUCCESS |

**Success Rate: 100% (5/5)**

## Installation Requirements

To run with full functionality (including JavaScript rendering):

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install lxml_html_clean (required for trafilatura)
pip install lxml_html_clean

# Install Playwright browser
playwright install chromium
```

## Running the Application

```bash
cd job_cv_extractor
streamlit run app.py
```

The application will:
1. Automatically detect the job platform
2. Use the optimal extraction method for each platform
3. Fall back to browser rendering for JavaScript-dependent pages
4. Display extracted job intelligence with skills, responsibilities, and ATS keywords

---

## LLMOps with Langfuse (Optional)

Langfuse is integrated for LLM observability, cost tracking, and quality evaluation.

### Setup

1. **Sign up** at [langfuse.com](https://langfuse.com) (free tier available)
2. **Create a project** and get your API keys
3. **Set environment variables:**

```bash
export LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key
export LANGFUSE_SECRET_KEY=sk-lf-your-secret-key
export LANGFUSE_BASE_URL=https://us.cloud.langfuse.com  # or https://cloud.langfuse.com for EU
```

Or add to a `.env` file:
```
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key
LANGFUSE_BASE_URL=https://us.cloud.langfuse.com
```

### Features Enabled

When Langfuse is configured, you get:

| Feature | Description |
|---------|-------------|
| 📊 **Tracing** | Every LLM call is tracked with inputs/outputs |
| 💰 **Cost Tracking** | Token usage and estimated costs per extraction |
| 📈 **Quality Scores** | Automatic evaluation of extraction quality |
| ⏱️ **Latency Monitoring** | Response time tracking |
| 🏷️ **Platform Tags** | Filter by job platform (Apple, iCIMS, etc.) |

### Dashboard

View your traces at: [cloud.langfuse.com](https://cloud.langfuse.com)

### Self-Hosting

For self-hosted Langfuse, set:
```bash
export LANGFUSE_BASE_URL=https://your-langfuse-instance.com
```
