# Enhanced JIRA Integration - Configuration Guide

## Overview

The JIRA sync script has been completely enhanced with JSON formatting and improved error handling. This guide helps you configure it for your specific JIRA instance.

## Key Enhancements

### ✅ JSON Templates
- **Before**: YAML-based templates
- **After**: JSON-based templates with better structure
- **Benefits**: Better parsing, validation, and IDE support

### ✅ Field Validation
- **Before**: Hard-coded custom field IDs that often failed
- **After**: Dynamic field discovery and validation
- **Benefits**: Graceful handling of missing fields, continues processing on errors

### ✅ Error Resilience
- **Before**: Script stopped on first error
- **After**: Continues processing and provides detailed error summary
- **Benefits**: Partial success, better debugging information

### ✅ Enhanced Logging
- **Before**: Basic success/failure messages  
- **After**: Detailed progress tracking and field mapping info
- **Benefits**: Better troubleshooting and transparency

## Setup Steps

### 1. Environment Configuration

```bash
# Required JIRA settings
export JIRA_URL="https://your-domain.atlassian.net"
export JIRA_EMAIL="your-email@company.com" 
export JIRA_TOKEN="your-api-token"
export JIRA_PROJECT="YOUR_PROJECT_KEY"

# Optional GitHub settings (auto-detected in GitHub Actions)
export GITHUB_REPO_URL="https://github.com/your-org/your-repo"
export GITHUB_BRANCH="main"

# Optional issue type overrides
export ISSUE_TYPE_EPIC="Epic"
export ISSUE_TYPE_STORY="Story"  
export ISSUE_TYPE_TASK="Task"
export ISSUE_TYPE_BUG="Bug"
```

### 2. Discover Available Fields

Run the field discovery script to see what's available in your JIRA:

```bash
python3 scripts/discover_jira_fields.py
```

This will show:
- All available issue types
- Standard fields for each type
- Custom fields with their IDs
- Recommended field mappings for templates.json

### 3. Choose Template Configuration

#### Option A: Simple Templates (Recommended)
Use `templates-simple.json` - no custom fields, just core JIRA functionality:

```bash
# Rename the simple template to be the main one
mv scripts/templates/templates-simple.json scripts/templates/templates.json
```

#### Option B: Full Templates  
Keep `templates.json` but update the `field_mappings` section based on your field discovery results.

### 4. Test Configuration

Always test with dry-run first:

```bash
DRY_RUN=true python3 scripts/jira_sync.py
```

### 5. Run Live Sync

Once dry-run looks good:

```bash
python3 scripts/jira_sync.py
```

## Template Structure

### JSON Template Format
```json
{
  "templates": {
    "epic": {
      "summary": "{SUMMARY}",
      "issue_type": "Epic",
      "description": {
        "source_file": "{SOURCE_FILE}",
        "github_link": "{GITHUB_LINK}",
        "content": "{CONTENT}"
      },
      "labels": ["epic", "auto-generated"],
      "priority": "High"
    }
  },
  "field_mappings": {
    "story_points": "customfield_10016",
    "epic_name": "customfield_10011"
  },
  "default_values": {
    "priority": "Medium",
    "story_points": 3
  }
}
```

### Available Placeholders
- `{SUMMARY}` - Issue title from markdown
- `{SOURCE_FILE}` - Relative path to spec file
- `{GITHUB_LINK}` - Full GitHub URL to spec
- `{CONTENT}` - Full markdown content
- `{PARENT_KEY}` - Parent issue key (for stories/tasks)
- `{EPIC_NAME}` - Epic title (for epics)
- `{ACCEPTANCE_CRITERIA}` - Extracted from "## Acceptance Criteria" section
- `{CATEGORY}` - Auto-detected task category
- `{TIME_ESTIMATE}` - Auto-generated time estimate

## Error Handling

### Common Issues & Solutions

#### Custom Field Errors
```
Field 'customfield_10100' cannot be set. It is not on the appropriate screen, or unknown.
```

**Solution**: 
1. Run field discovery script
2. Update `field_mappings` in templates.json
3. Or use templates-simple.json

#### Issue Type Not Found
```
Issue type 'Story' not found
```

**Solution**:
1. Set environment variables for your issue types:
   ```bash
   export ISSUE_TYPE_STORY="User Story"  # or whatever your JIRA uses
   ```

#### Permission Errors
```
HTTP 401 - Unauthorized
```

**Solution**:
1. Verify JIRA_TOKEN is valid
2. Check project permissions
3. Regenerate API token if needed

### Resilient Processing

The enhanced script will:
- ✅ Continue processing after individual failures
- ✅ Skip unavailable custom fields automatically  
- ✅ Provide detailed error summaries
- ✅ Show success rates and partial results
- ✅ Preserve JSON files for debugging

## Integration Examples

### GitHub Actions Workflow
```yaml
name: Sync JIRA Issues
on:
  push:
    paths: ['specs/**/*.md']

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: pip install requests
    - name: Sync to JIRA
      env:
        JIRA_URL: ${{ secrets.JIRA_URL }}
        JIRA_EMAIL: ${{ secrets.JIRA_EMAIL }}
        JIRA_TOKEN: ${{ secrets.JIRA_TOKEN }}
        JIRA_PROJECT: ${{ secrets.JIRA_PROJECT }}
      run: python3 scripts/jira_sync.py
```

### Local Development
```bash
# Load config from file
source scripts/config/local.env

# Test changes
DRY_RUN=true python3 scripts/jira_sync.py

# Apply changes  
python3 scripts/jira_sync.py
```

## Advanced Configuration

### Custom Issue Type Mapping
```bash
# For non-standard JIRA setups
export ISSUE_TYPE_EPIC="Initiative"
export ISSUE_TYPE_STORY="User Story"  
export ISSUE_TYPE_TASK="Development Task"
export ISSUE_TYPE_BUG="Defect"
```

### Field Mapping Customization
Update `templates.json`:
```json
{
  "field_mappings": {
    "story_points": "customfield_10025",    # Your story points field
    "epic_name": "customfield_10018",       # Your epic name field  
    "sprint": "customfield_10020",          # Your sprint field
    "team": "customfield_10030"             # Your team field
  }
}
```

## Troubleshooting

### Debug Mode
Set environment variables for more verbose output:
```bash
export DEBUG=true
DRY_RUN=true python3 scripts/jira_sync.py
```

### Field Discovery
Use the discovery script to understand your JIRA setup:
```bash
python3 scripts/discover_jira_fields.py > my_jira_fields.txt
```

### Validation
Test templates before running:
```bash
python3 scripts/test_json_templates.py
```

## Support

If you encounter issues:
1. Run field discovery script
2. Check error logs in detail
3. Test with templates-simple.json first
4. Validate JIRA permissions and configuration
5. Use DRY_RUN=true for testing