# SPEC-KIT Bidirectional GitHub-JIRA Integration

## Overview
Complete bidirectional integration between GitHub specifications and JIRA work items, providing seamless traceability from specifications through implementation.

## Enhanced Features

### 🔗 Bidirectional Linking
- **GitHub → JIRA**: All JIRA items (Epics, Stories, Tasks) include GitHub context
- **JIRA → GitHub**: Direct links to repository, specifications, PRs, and workflow runs
- **Complete Traceability**: Spec → GitHub → JIRA → Implementation workflow

### 📋 JIRA Item Enhancements
Each JIRA item now includes a "GitHub Integration" section with:
- **Repository Link**: Direct link to GitHub repository
- **Feature Directory**: Link to complete spec folder (`specs/feature-name/`)
- **Pull Request**: Link to originating PR (when available)
- **Workflow Run**: Link to GitHub Actions run for CI/CD traceability

### ⚙️ GitHub Actions Integration
Enhanced workflow automatically passes GitHub context:
- Repository identifier (`owner/repo`)
- Branch name for accurate spec links
- Pull request number (for PR-triggered runs)
- Workflow run URL for CI/CD visibility

## Implementation Details

### Script Enhancements
Enhanced `scripts/push_jira.py` with new arguments:
```bash
python3 scripts/push_jira.py DRAFT_FILE \\
  --github-repo "owner/repo" \\
  --github-branch "branch-name" \\
  --github-pr "123" \\
  --github-workflow "https://github.com/owner/repo/actions/runs/456"
```

### Workflow Integration
GitHub Actions workflow automatically detects and passes context:
- **PR Merge**: Repository, branch, PR number, workflow URL
- **Manual Trigger**: Repository, branch, workflow URL
- **Both Modes**: Dry-run and production enhanced

### JIRA Description Format
Example GitHub integration section added to descriptions:
```markdown
---
**🔗 GitHub Integration**
* Repository: [owner/repo](https://github.com/owner/repo)
* Feature Directory: [specs/feature-name/](https://github.com/owner/repo/tree/main/specs/feature-name)
* Pull Request: [#123](https://github.com/owner/repo/pull/123)
* Workflow Run: [View Details](https://github.com/owner/repo/actions/runs/456)
```

## Benefits

### 🎯 Developer Experience
- **One-Click Navigation**: From JIRA items back to specifications
- **Complete Context**: Full traceability across tools
- **Seamless Integration**: No manual linking required

### 📊 Project Management
- **Visibility**: Clear connection between specs and work items
- **Traceability**: Track from requirements through implementation
- **Automation**: GitHub Actions handles context automatically

### 🔧 CI/CD Integration
- **Workflow Links**: Direct access to build/deployment status
- **PR Tracking**: Link work items to originating changes
- **Branch Context**: Accurate links regardless of branch

## Usage

### Automatic (Recommended)
GitHub Actions workflow handles integration automatically:
1. PR merged with spec changes → JIRA items created with GitHub context
2. Manual workflow trigger → Repository context included
3. All JIRA items contain bidirectional links

### Manual
For manual testing or custom scenarios:
```bash
python3 scripts/push_jira.py jira/feature-draft.yaml \\
  --github-repo "hubino/selham-phase-2" \\
  --github-branch "main" \\
  --github-pr "123" \\
  --github-workflow "https://github.com/hubino/selham-phase-2/actions/runs/456"
```

## Validation
All enhancements tested and validated:
- ✅ GitHub context properly parsed and included
- ✅ JIRA descriptions enhanced with clickable links
- ✅ Both PR merge and manual trigger scenarios supported
- ✅ Dry-run mode includes GitHub integration testing
- ✅ ADF (Atlassian Document Format) conversion handles enhanced content

## Result
**Complete SPEC-KIT + GitHub + JIRA Integration Achieved!**

Seamless bidirectional workflow providing full traceability from specifications through implementation with one-click navigation and automatic context passing through CI/CD pipelines.