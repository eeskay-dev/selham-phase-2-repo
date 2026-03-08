# JIRA Push Wrapper Usage Guide

## Overview
The JIRA Push Wrapper provides an easy way to invoke `push_jira.py` with proper environment setup and parameter validation.

## Available Wrappers

### 1. Python Wrapper (Recommended)
```bash
python3 scripts/jira_push_wrapper.py [OPTIONS] <spec_path>
```

### 2. Bash Wrapper
```bash
./scripts/jira_push_wrapper.sh [OPTIONS] <spec_path>
```

## Setup

### 1. Environment Variables
Set the required JIRA configuration:

```bash
export JIRA_URL=https://your-domain.atlassian.net
export JIRA_EMAIL=your-email@domain.com
export JIRA_TOKEN=your-api-token
export JIRA_PROJECT=YOUR-PROJECT-KEY
```

### 2. Using .env File (Recommended)
```bash
# Copy the example file
cp .env.example .env

# Edit with your values
nano .env
```

## Usage Examples

### Basic Usage
```bash
# Push spec to JIRA
python3 scripts/jira_push_wrapper.py specs/001-multi-brand-menu-mgmt/

# Dry run (test without creating issues)
python3 scripts/jira_push_wrapper.py --dry-run specs/001-multi-brand-menu-mgmt/
```

### With GitHub Integration  
```bash
python3 scripts/jira_push_wrapper.py \\
  --github-repo hubino/selham-phase-2 \\
  --github-branch main \\
  --github-pr 123 \\
  specs/001-multi-brand-menu-mgmt/
```

### Verbose Output
```bash
python3 scripts/jira_push_wrapper.py --verbose --dry-run specs/001-multi-brand-menu-mgmt/
```

## Features

### ✅ Automatic Draft Generation
- Automatically generates JIRA draft if missing
- Uses `generate_jira_draft.py` behind the scenes

### ✅ Environment Validation  
- Validates all required JIRA environment variables
- Provides helpful error messages and setup instructions

### ✅ Path Validation
- Validates spec directory exists
- Checks for required `spec.md` file
- Resolves relative paths automatically

### ✅ GitHub Integration
- Supports all GitHub context parameters
- Adds bidirectional linking to JIRA issues

### ✅ Security
- No hardcoded credentials in scripts
- Uses environment variables or .env files
- Masks sensitive data in output

## Troubleshooting

### Missing Environment Variables
```
❌ ERROR: Missing required environment variables: JIRA_EMAIL, JIRA_TOKEN
💡 Set the following environment variables:

export JIRA_URL=https://your-domain.atlassian.net
export JIRA_EMAIL=your-email@domain.com  
export JIRA_TOKEN=your-api-token
export JIRA_PROJECT=YOUR-PROJECT-KEY
```

**Solution**: Set environment variables or create `.env` file

### Spec Directory Not Found
```
❌ ERROR: Spec directory does not exist: /path/to/specs/feature-name
```

**Solution**: Check the path and ensure spec directory exists with `spec.md` file

### Draft File Missing  
```
⚠️  WARNING: Draft file not found: jira/feature-name-draft.yaml
💡 You may need to run generate_jira_draft.py first
💡 Attempting to generate draft for specs/feature-name/
✅ Generated draft file: jira/feature-name-draft.yaml
```

**Automatic**: Wrapper automatically generates missing draft files

### JIRA Authentication Issues
See detailed troubleshooting in:
- `troubleshooting/speckit-jira-integeration/002_github-action-failure.md`

## Command Options

| Option | Description | Example |
|--------|-------------|---------|
| `spec_path` | Path to spec directory | `specs/001-multi-brand-menu-mgmt/` |
| `--dry-run` | Test mode, no actual JIRA issues created | `--dry-run` |
| `--verbose` | Detailed output | `--verbose` |
| `--github-repo` | GitHub repository (owner/repo) | `--github-repo hubino/selham-phase-2` |
| `--github-pr` | Pull request number | `--github-pr 123` |
| `--github-workflow` | Workflow run URL | `--github-workflow https://...` |
| `--github-branch` | Git branch name | `--github-branch main` |

## Integration with CI/CD

The wrapper is designed to work seamlessly with GitHub Actions and other CI/CD systems:

```yaml
- name: Push to JIRA
  run: |
    python3 scripts/jira_push_wrapper.py \\
      --github-repo ${{ github.repository }} \\
      --github-branch ${{ github.ref_name }} \\
      --github-pr ${{ github.event.pull_request.number }} \\
      specs/001-multi-brand-menu-mgmt/
```