# GitHub Actions JIRA Integration Setup 

## Issue: JIRA Authentication Failure (401 Unauthorized)

### Error Description
The GitHub Actions workflow fails due to JIRA authentication issues when attempting to create issues.

### Error Trace
```
Run feature_name="001-multi-brand-menu-mgmt"
🚀 Pushing 001-multi-brand-menu-mgmt to JIRA...
✅ JIRA Configuration:
   URL: https://selham.atlassian.net
   Project: ***
   Email: ***
Loading JIRA draft: /home/runner/work/selham-phase-2-repo/selham-phase-2-repo/jira/001-multi-brand-menu-mgmt-draft.yaml
✅ Draft loaded successfully
   Feature: 001-multi-brand-menu-mgmt
   Epic: Multi-Brand Menu Management System
   Stories: 6
   Tasks: 0
❌ JIRA connection failed: 401 Client Error: Unauthorized for url: ***rest/api/2/myself
   Status: 401
   Response: Client must be authenticated to access this resource.
✅ Successfully pushed to JIRA
```

### Root Cause Analysis
The 401 Unauthorized error indicates that JIRA authentication is failing. Common causes:

1. **Invalid API Token**: Using expired or incorrect JIRA API token
2. **Wrong Email**: JIRA_EMAIL doesn't match the account associated with the API token
3. **Missing Secrets**: GitHub repository secrets are not properly configured
4. **Token Permissions**: API token lacks necessary JIRA permissions

### Solution Steps

#### 1. Verify JIRA API Token
```bash
# Test JIRA authentication manually
curl -u 'your-email@domain.com:your-api-token' \\
  'https://your-domain.atlassian.net/rest/api/2/myself'
```

Expected response: JSON with user information
- ✅ Success: `{"accountId": "...", "displayName": "..."}`
- ❌ 401 Error: Check token and email
- ❌ 403 Error: Token lacks permissions

#### 2. Generate New JIRA API Token
1. **Login to JIRA** → Profile → Security → API tokens
2. **Create token** with descriptive name (e.g., "GitHub Actions SPEC-KIT")
3. **Copy token immediately** (cannot be viewed again)
4. **Test token** using curl command above

#### 3. Configure GitHub Repository Secrets
Navigate to: `Repository → Settings → Secrets and variables → Actions`

Add/Update required secrets:
```
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@domain.com
JIRA_TOKEN=your-api-token-here
JIRA_PROJECT=YOUR-PROJECT-KEY
```

**Critical Notes:**
- Use **API token**, not password for JIRA_TOKEN
- Email must match the account that created the API token
- URL should not include trailing slash
- Project key is typically uppercase (e.g., "SPEC", "DEV")

#### 4. Verify Token Permissions
The API token account needs:
- **Browse Projects** permission
- **Create Issues** permission
- **Edit Issues** permission (for linking)
- **Assignable User** permission

#### 5. Test Configuration
```bash
# Manual test with actual credentials
export JIRA_URL="https://your-domain.atlassian.net"
export JIRA_EMAIL="your-email@domain.com"
export JIRA_TOKEN="your-api-token"
export JIRA_PROJECT="YOUR-PROJECT"

# Test authentication
python3 scripts/push_jira.py jira/001-multi-brand-menu-mgmt-draft.yaml --dry-run
```

### Enhanced Script Diagnostics

The updated `push_jira.py` script now provides detailed diagnostics:

```
🔍 Testing JIRA authentication...
✅ JIRA connection validated
   User: John Doe
   Account ID: 5b10ac8d82e05b22cc7d4ef5
🔍 Testing project access...
✅ Project access validated: SPEC-KIT Project
   Project Key: SPEC
```

**Authentication failure diagnostics:**
```
❌ JIRA Authentication Failed (401 Unauthorized)
🔍 Troubleshooting steps:
   1. Verify JIRA_EMAIL is correct: joh***doe
   2. Check JIRA_TOKEN is valid API token (not password)
   3. Ensure API token has not expired
   4. Verify JIRA URL is correct: https://domain.atlassian.net
   5. Test manually: curl -u 'email:TOKEN' https://domain.atlassian.net/rest/api/2/myself
```

### Common Issues & Solutions

#### Issue: Email Mismatch
**Problem**: JIRA_EMAIL doesn't match API token account
**Solution**: Use the exact email address associated with the JIRA account

#### Issue: Expired Token
**Problem**: API token has been revoked or expired
**Solution**: Generate new API token and update GitHub secrets

#### Issue: Wrong JIRA URL
**Problem**: Incorrect Atlassian domain or URL format
**Solution**: Use format `https://your-domain.atlassian.net` (no trailing slash)

#### Issue: Project Access
**Problem**: User lacks access to specified project
**Solution**: Contact JIRA admin for project permissions

#### Issue: Corporate Network
**Problem**: GitHub Actions can't reach JIRA due to firewall
**Solution**: Ensure JIRA Cloud is accessible from GitHub's IP ranges

### Status

✅ **AUTHENTICATION ENHANCED** - Improved error diagnostics and troubleshooting guidance  
✅ **WORKFLOW UPDATED** - Better error detection and specific guidance for different failure types  
✅ **SCRIPT IMPROVED** - Detailed authentication validation with step-by-step troubleshooting  

### Enhanced Features

**Script Improvements:**
- Masked credential display for security
- Detailed 401/403/404 error diagnostics  
- Step-by-step troubleshooting guidance
- Manual test command suggestions

**Workflow Enhancements:**
- Specific error type detection (401, 403, 404)
- Contextual troubleshooting guidance
- Enhanced failure issue creation with solutions
- Direct link to troubleshooting documentation

### Prevention
- Store API tokens securely and rotate periodically
- Monitor JIRA token expiration dates
- Use service account for automation tokens
- Test authentication changes in dry-run mode first