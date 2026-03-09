# JIRA Sync Script Improvements

## Overview
The JIRA sync script has been enhanced with two major improvements:

1. **Temporary YAML Files**: Creates intermediate YAML files for each JIRA item to avoid ADF (Atlassian Document Format) conversion issues
2. **GitHub Links**: Automatically adds GitHub source file links to each JIRA issue

## New Features

### 1. YAML-Based Processing
- Creates temporary YAML files for each JIRA item (Epic, Story, Task)
- YAML structure includes metadata like source file path, GitHub link, and content
- Eliminates markdown-to-ADF conversion issues
- YAML files are preserved for debugging (can be manually cleaned up)

### 2. GitHub Integration
- **Auto-Detection**: Automatically detects GitHub repository URL and branch when running in GitHub Actions
- **Manual Configuration**: Falls back to manual environment variables when not in CI
- **GitHub Actions Variables Used**:
  - `GITHUB_ACTIONS=true` - Triggers auto-detection
  - `GITHUB_SERVER_URL` - GitHub server URL (usually https://github.com)  
  - `GITHUB_REPOSITORY` - Repository in "owner/repo" format
  - `GITHUB_REF_NAME` - Branch name
  - `GITHUB_HEAD_REF` - For pull requests
- Links are added to JIRA issue descriptions with format: `**Source File:** [path/file.md](github_url)`

### 3. Enhanced Error Handling
- Better error messages with YAML file references
- Preserved temp files for debugging failed uploads
- Improved dry run output showing GitHub links

## Configuration

### GitHub Actions (Automatic)
When running in GitHub Actions, repository information is auto-detected:
```yaml
# In GitHub Actions workflow - no manual GitHub config needed!
env:
  JIRA_URL: ${{ secrets.JIRA_URL }}
  JIRA_EMAIL: ${{ secrets.JIRA_EMAIL }}
  JIRA_TOKEN: ${{ secrets.JIRA_TOKEN }}
  JIRA_PROJECT: ${{ secrets.JIRA_PROJECT }}
  # GitHub URL and branch auto-detected from GitHub Actions context
```

### Manual/Local Development
```bash
# JIRA Configuration (required)
export JIRA_URL="https://your-domain.atlassian.net"
export JIRA_EMAIL="your-email@domain.com"
export JIRA_TOKEN="your-api-token"
export JIRA_PROJECT="YOUR_PROJECT_KEY"

# GitHub Configuration (manual fallback)
export GITHUB_REPO_URL="https://github.com/your-org/your-repo"
export GITHUB_BRANCH="main"  # Optional, defaults to "main"

# Optional Settings
export DRY_RUN="true"  # Test without creating issues
```

### New Dependencies
- `PyYAML==6.0.1` - Added to requirements.txt for YAML processing

## Usage

### Basic Usage
```bash
cd selham-phase-1-repo/scripts
python jira_sync.py
```

### Test Mode
```bash
export DRY_RUN=true
python jira_sync.py
```

### With Custom GitHub Settings
```bash
export GITHUB_REPO_URL="https://github.com/my-org/my-repo"
export GITHUB_BRANCH="develop"
python jira_sync.py
```

## YAML File Structure

Each JIRA item gets a temporary YAML file with this structure:

```yaml
issue_type: Epic  # or Story, Sub-task
summary: "Issue Title (truncated to 255 chars)"
description:
  source_file: "specs/001-example/spec.md"
  github_link: "https://github.com/org/repo/blob/main/specs/001-example/spec.md"
  content: |
    Original markdown content from the file...
parent: "PROJ-123"  # Only for Stories and Tasks
```

## JIRA Issue Description Format

Each JIRA issue will have an enhanced description:

```markdown
**Source File:** [specs/001-example/spec.md](https://github.com/org/repo/blob/main/specs/001-example/spec.md)

---

[Original markdown content from the source file]
```

## Troubleshooting

### Issue Type Configuration

#### Problem: "Issue types are not available in your project"
```
❌ ERROR: These issue types are not available in your project:
   - Story (Story)
   - Task (Sub-task)
```

#### Solution 1: Use Configuration Validator
```bash
cd scripts
export JIRA_URL="https://your-domain.atlassian.net"
export JIRA_EMAIL="your-email@domain.com"
export JIRA_TOKEN="your-api-token"
export JIRA_PROJECT="YOUR_PROJECT_KEY"

python3 validate_jira_config.py
```

This will show you exactly which issue types are available in your JIRA project and suggest the correct configuration.

#### Solution 2: Manual Configuration
Set environment variables to match your JIRA project's available issue types:

```bash
# Common JIRA configurations:

# For basic JIRA projects (Task-based):
export ISSUE_TYPE_EPIC="Epic"
export ISSUE_TYPE_STORY="Task"
export ISSUE_TYPE_TASK="Task" 
export ISSUE_TYPE_BUG="Bug"

# For Scrum projects:
export ISSUE_TYPE_EPIC="Epic"
export ISSUE_TYPE_STORY="Story"
export ISSUE_TYPE_TASK="Sub-task"
export ISSUE_TYPE_BUG="Bug"

# For custom JIRA setups:
export ISSUE_TYPE_EPIC="Initiative"      # or your epic equivalent
export ISSUE_TYPE_STORY="Feature"        # or your story equivalent  
export ISSUE_TYPE_TASK="Task"           # or your task equivalent
export ISSUE_TYPE_BUG="Defect"          # or your bug equivalent
```

#### Automatic Fallbacks
The script now includes automatic fallback logic:

- **Story** → Task → Epic (if Story not available)
- **Sub-task** → Task → Story → Epic (if Sub-task not available)  
- **Bug** → Task → Story (if Bug not available)

### GitHub Actions Configuration

### GitHub Actions Configuration
Update your GitHub Actions workflow with the correct issue types:

```yaml
env:
  JIRA_URL: ${{ secrets.JIRA_URL }}
  JIRA_EMAIL: ${{ secrets.JIRA_EMAIL }}
  JIRA_TOKEN: ${{ secrets.JIRA_TOKEN }}
  JIRA_PROJECT: ${{ secrets.JIRA_PROJECT }}
  
  # Use your JIRA project's actual issue types:
  ISSUE_TYPE_EPIC: "Epic"
  ISSUE_TYPE_STORY: "Task"      # if no "Story" type available
  ISSUE_TYPE_TASK: "Task"       # if no "Sub-task" type available
  ISSUE_TYPE_BUG: "Bug"
```

### Error Recovery
- Temporary YAML files are created in `/tmp/jira_sync_[random]/`
- Files are preserved after execution for debugging
- Clean up manually: `rm -rf /tmp/jira_sync_*`

### Dry Run Testing
```bash
export DRY_RUN=true
python jira_sync.py
```

This shows:
- YAML file names that would be created
- GitHub links that would be added
- JIRA issue hierarchy
- No actual JIRA issues are created

## Error Recovery

If sync fails:
1. Check the temp YAML directory shown in output
2. Review YAML files for formatting issues
3. Validate GitHub URLs are accessible
4. Check JIRA API permissions for the project

## Migration Notes

### From Old Script
- No changes needed to existing markdown files
- Environment variables are backward compatible
- Add new GitHub configuration variables
- Install PyYAML dependency

### Benefits Over Previous Version
- **Reliability**: YAML intermediate format reduces ADF conversion errors
- **Traceability**: GitHub links provide direct access to source files
- **Debugging**: Preserved YAML files help troubleshoot issues
- **Maintainability**: Cleaner separation between parsing and JIRA creation