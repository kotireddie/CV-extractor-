# Test Tracking System

The CV Extractor now includes an automated test tracking system that records all test runs, including URLs, status, errors, and results. This helps identify issues and improve the extractor.

## Features

- **Automatic Recording**: Every extraction attempt is automatically recorded
- **Error Tracking**: Captures error messages, error types, and failure points
- **Statistics Dashboard**: View success rates, platform breakdowns, and error analysis
- **Export Functionality**: Export all test data as JSON for analysis
- **Test History**: View recent test runs in the sidebar

## What Gets Recorded

For each test run, the system records:

- **Basic Info**:
  - URL/Job ID tested
  - Timestamp
  - Status (success, failure, partial)

- **Platform Detection**:
  - Platform detected (Greenhouse, Lever, Workday, etc.)
  - URL resolution status
  - Resolved URL (if different from original)

- **Extraction Details**:
  - Extraction method used
  - Content length extracted
  - Model used for LLM analysis
  - Tokens consumed

- **Results**:
  - Job title and company (if extracted)
  - Number of skills extracted
  - Number of responsibilities extracted
  - Number of ATS keywords extracted

- **Errors**:
  - Error message
  - Error type (Fetch Error, Content Extraction Error, LLM Analysis Error, etc.)

## How to Use

### Viewing Test History

1. Run extractions as normal - everything is automatically tracked
2. Check the sidebar for "📊 Test History" section
3. View:
   - Total runs and success rate
   - Platform breakdown
   - Error type analysis
   - Recent test runs

### Exporting Test Data

1. Click "📥 Export Test Data" in the sidebar
2. Click "Download JSON" to save all test data
3. Use the JSON file for:
   - Analyzing patterns
   - Identifying common failure points
   - Tracking improvements over time
   - Sharing with team for debugging

### Clearing History

- Click "🗑️ Clear History" in the sidebar to reset all test data
- Use this when starting a new testing session

## Data Storage

Test data is stored in: `logs/test_runs.json`

This file is automatically created and updated with each test run. The file is in JSON format and can be:
- Read directly for analysis
- Imported into other tools
- Version controlled (if desired)
- Backed up for historical tracking

## Error Types Tracked

1. **URL Validation Error**: Invalid URL format or structure
2. **Fetch Error**: Failed to fetch HTML from URL (timeout, connection error, etc.)
3. **Content Extraction Error**: Could not extract meaningful content from page
4. **LLM Analysis Error**: Failed during GPT analysis phase

## Example Use Cases

### Identifying Problem Platforms
- Export test data
- Filter by platform
- Identify which platforms have low success rates
- Focus improvement efforts on problematic platforms

### Tracking Improvements
- Export test data before making changes
- Make improvements to extractor
- Run new tests
- Compare success rates before/after

### Debugging Specific URLs
- Find failed runs in test history
- Check error messages and types
- Use resolved URLs to test manually
- Add notes for follow-up

## Notes Field

You can manually add notes to test runs by editing the JSON file directly, or by extending the tracker to include a notes field in the UI.

## Integration with Development

The test tracker integrates seamlessly with the existing logging system:
- Errors are logged to `logs/app.log`
- Test runs are stored in `logs/test_runs.json`
- Both can be used together for comprehensive debugging
