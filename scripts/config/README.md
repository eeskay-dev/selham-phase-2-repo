# JIRA Sync Configuration

This directory contains configuration files for running JIRA sync locally.

## Quick Start

1. **Copy the template:**
   ```bash
   cp config/local.env.template config/local.env
   ```

2. **Edit your configuration:**
   ```bash
   nano config/local.env  # Or use your preferred editor
   ```

3. **Update required fields:**
   - `JIRA_URL`: Your Atlassian domain (e.g., `https://yourcompany.atlassian.net`)
   - `JIRA_EMAIL`: Your Atlassian account email
   - `JIRA_TOKEN`: Your personal access token
   - `JIRA_PROJECT`: Your project key (e.g., `DEV`, `TEST`)

4. **Run the sync:**
   ```bash
   source config/local.env && python3 jira_sync.py
   ```

## Interactive Setup

Use the interactive configuration script:

```bash
./config/local-setup.sh
```

This provides a menu-driven interface to:
- Validate JIRA configuration
- Run sync with current settings
- Toggle dry-run mode
- Run test suite

## Getting JIRA Credentials

### Personal Access Token (Recommended)

1. Go to: `https://your-domain.atlassian.net/secure/ViewProfile.jspa`
2. Click "Personal Access Tokens" tab
3. Create a new token with appropriate permissions:
   - **Scopes**: `read:jira-user`, `read:jira-work`, `write:jira-work`
   - **Resources**: Your JIRA instance
4. Copy the token to `JIRA_TOKEN` in your config

### Project Key

Find your project key:
1. Go to your JIRA project
2. Look in the URL: `https://domain.atlassian.net/jira/software/projects/PROJ/boards/123`
3. The key is `PROJ` in this example

## Configuration Files

- `local.env.template` - Template with example values
- `local.env` - Your actual configuration (gitignored)
- `local-setup.sh` - Interactive setup script

## Safety Features

- **Dry Run Mode**: Set `DRY_RUN="true"` to preview without creating issues
- **Validation**: Use `validate_jira_config.py` to test connectivity
- **Error Handling**: Script validates all required variables before execution

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `JIRA_URL` | Yes | Your Atlassian domain URL |
| `JIRA_EMAIL` | Yes | Your Atlassian account email |
| `JIRA_TOKEN` | Yes | Personal access token |
| `JIRA_PROJECT` | Yes | Project key (e.g., DEV, TEST) |
| `GITHUB_REPO_URL` | No | Auto-detected in CI/CD |
| `GITHUB_BRANCH` | No | Auto-detected in CI/CD |
| `DRY_RUN` | No | Set to "true" for preview mode |
| `ISSUE_TYPE_*` | No | Customize issue type mappings |

## Security Notes

- Never commit `local.env` to version control
- Use personal access tokens, not passwords
- Limit token scope to minimum required permissions
- Regularly rotate your tokens