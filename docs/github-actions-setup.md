# GitHub Actions JIRA Integration Setup

This guide explains how to configure the automated JIRA integration that triggers when PRs are merged to main.

## GitHub Secrets Configuration

The workflow requires the following GitHub repository secrets to be configured:

### Required Secrets

Navigate to **Settings → Secrets and variables → Actions** in your GitHub repository and add:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `JIRA_URL` | Your JIRA instance URL | `https://company.atlassian.net` |
| `JIRA_EMAIL` | JIRA user email | `automation@company.com` |
| `JIRA_TOKEN` | JIRA API token | `ATATxxxxxxxxxxxxx` |
| `JIRA_PROJECT` | JIRA project key | `SPEC` |

### Generating JIRA API Token

1. Go to [Atlassian Account Security](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click **Create API token**
3. Enter a label (e.g., "GitHub Actions Integration")
4. Copy the generated token and add it as `JIRA_TOKEN` secret

## Workflow Triggers

The GitHub Action automatically triggers on:

### 1. PR Merge to Main
```yaml
# Triggers when PRs are merged that modify:
- specs/*/spec.md        # Specification files
- specs/*/tasks.md       # Task files  
- jira/*-draft.yaml      # JIRA draft files
```

### 2. Manual Trigger
```yaml
# Manual workflow dispatch with options:
- feature_path: "specs/001-multi-brand-menu-mgmt/"  # Specific feature
- dry_run: true/false    # Test mode
```

## Workflow Process

### Automatic Flow (PR Merge)
1. **Detection**: Identifies changed spec files in merged PR
2. **Generation**: Creates JIRA draft (if not exists)
3. **Validation**: Validates draft structure and content
4. **Push to JIRA**: Creates Epic → Stories → Tasks hierarchy
5. **Notification**: Comments on PR with JIRA links
6. **Artifacts**: Saves draft and mapping files

### Manual Flow (Workflow Dispatch)
```bash
# Trigger via GitHub UI or CLI
gh workflow run jira-integration.yml \
  -f feature_path="specs/001-multi-brand-menu-mgmt/" \
  -f dry_run=true
```

## Workflow Features

### 🔍 Smart Detection
- Detects multiple changed features in single PR
- Processes each feature independently
- Skips unchanged specifications

### 🛡️ Safety Features
- **Dry-run mode**: Test without creating JIRA issues
- **Validation gates**: YAML structure and content validation
- **Parallel processing**: Limited to 3 concurrent JIRA operations
- **Failure isolation**: One feature failure doesn't block others

### 📋 Output & Artifacts
- **PR Comments**: Success notifications with JIRA links
- **Issue Creation**: Automatic issues for failures
- **Artifacts**: Draft files, mapping files, logs (30-day retention)
- **Workflow Summary**: Detailed processing report

### 🔄 Error Handling
- **Configuration validation**: Checks JIRA secrets
- **Connection testing**: Validates JIRA access
- **Graceful failures**: Creates GitHub issues for manual resolution
- **Detailed logging**: Comprehensive error reporting

## Example Workflow Results

### Successful Processing
```
🎉 JIRA Integration Successful!

Feature: 001-multi-brand-menu-mgmt
Epic Created: SPEC-001

📋 Next Steps:
1. Review JIRA epic and stories  
2. Assign tasks to development teams
3. Begin implementation using /speckit implement SPEC-001
```

### Multiple Features
```
✅ Successfully processed all spec changes

Features Processed:
- 📋 001-multi-brand-menu-mgmt → JIRA Epic Created
- 📋 002-payment-processing → JIRA Epic Created
```

## Troubleshooting

### Common Issues

**1. Missing Secrets**
```
❌ Missing JIRA configuration secrets!
Required secrets: JIRA_URL, JIRA_EMAIL, JIRA_TOKEN, JIRA_PROJECT
```
*Solution*: Add all required secrets in GitHub repository settings

**2. JIRA Connection Failed**
```
❌ JIRA connection failed: 401 Unauthorized
```
*Solution*: Verify JIRA_EMAIL and JIRA_TOKEN are correct and user has permissions

**3. No Changes Detected**
```
No spec changes detected
```
*Solution*: Ensure PR modifies files in `specs/*/` directories with `.md` extensions

**4. Draft Validation Failed**
```
❌ Draft validation failed: Missing sections: ['epic']
```
*Solution*: Check spec.md format and run `python3 scripts/generate_jira_draft.py` locally

### Manual Recovery

If workflow fails, you can manually process:

```bash
# Generate draft locally
python3 scripts/generate_jira_draft.py specs/001-multi-brand-menu-mgmt/

# Test push (dry-run)
python3 scripts/push_jira.py --dry-run

# Push to JIRA
python3 scripts/push_jira.py jira/001-multi-brand-menu-mgmt-draft.yaml
```

## Permissions Required

### JIRA User Permissions
- Create issues in target project
- Link issues (Epic/Story relationships)  
- Set custom fields (Story Points, etc.)
- Browse projects and issues

### GitHub Repository Permissions
- **Actions**: Write (to run workflows)
- **Contents**: Read (to checkout code)
- **Issues**: Write (to create failure issues)
- **Pull requests**: Write (to comment on PRs)

## Advanced Configuration

### Custom Field Mapping
Update field IDs in `scripts/push_jira.py` if your JIRA instance uses different custom fields:

```python
field_mapping = {
    'storyPoints': 'customfield_10016',      # Adjust for your instance
    'acceptanceCriteria': 'customfield_10017',
    'businessValue': 'customfield_10020'
}
```

### Workflow Customization
Modify `.github/workflows/jira-integration.yml` to:
- Change trigger conditions
- Add additional validation steps
- Customize notification messages
- Adjust processing limits

The GitHub Action provides a complete automation bridge between SPEC-KIT specifications and JIRA project management, ensuring seamless integration without manual intervention.