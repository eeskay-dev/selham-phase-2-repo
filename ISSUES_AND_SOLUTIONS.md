# JIRA Sync Script - Issues & Solutions Tracker

This document tracks all issues encountered with the JIRA sync script and their solutions.

## 📊 **Issue Summary**
- **Total Issues**: 2
- **Resolved**: 2
- **Open**: 0
- **Last Updated**: 2026-03-09

---

## 🔧 **Issue #1: Specs Folder Path Resolution in GitHub Actions**

### **Problem**
```
📂 SPECS FOLDER VALIDATION
   Expected path: /home/runner/work/selham-phase-2-repo/selham-phase-2-repo/scripts/specs
   ⚠️  Specs folder does not exist!
```

### **Root Cause**
The script was using relative path `Path("specs")` which resolved relative to current working directory. In GitHub Actions, the script runs from the `scripts/` directory, so it looked for `scripts/specs` instead of the correct `specs/` at repository root.

### **Solution Applied**
Modified the SPEC_FOLDER path calculation to be relative to repository root:

```python
# Before
SPEC_FOLDER = Path("specs")

# After  
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent  # Go up one level from scripts/ to repo root
SPEC_FOLDER = REPO_ROOT / "specs"
```

Also fixed GitHub link generation:
```python
# Before
relative_path = file_path.relative_to(Path.cwd()) if file_path.is_absolute() else file_path

# After
try:
    relative_path = file_path.relative_to(REPO_ROOT) if file_path.is_absolute() else file_path
except ValueError:
    relative_path = file_path.name
```

### **Status**: ✅ **RESOLVED**
### **Verification**: 
- ✅ Works from repository root
- ✅ Works from scripts directory (GitHub Actions scenario)
- ✅ Generates correct GitHub links

---

## 🔧 **Issue #2: JIRA 401 Unauthorized Error**

### **Problem**
```
❌ ERROR: HTTP 401
Response: {"errorMessages":["You do not have permission to create issues in this project."],"errors":{}}
```

### **Root Cause**
The user/token doesn't have sufficient permissions to create issues in the JIRA project. This can be due to:
1. Invalid or expired API token
2. Incorrect email/token combination
3. Missing "Create Issues" permission in the JIRA project
4. Project-level permission restrictions

### **Solution Applied**
Enhanced error handling to provide detailed troubleshooting guidance:

```python
if response.status_code == 401:
    print(f"❌ ERROR: HTTP 401 - Unauthorized")
    print(f"🔑 JIRA Authentication Issue:")
    print(f"   - Check that JIRA_EMAIL is correct: {EMAIL}")
    print(f"   - Check that JIRA_TOKEN is valid and not expired")
    print(f"   - Verify you have permission to create issues in project: {PROJECT}")
    print(f"   - Token should be an API token from: https://id.atlassian.com/manage-profile/security/api-tokens")
    # ... additional troubleshooting steps
```

### **Troubleshooting Steps for Users**:
1. **Verify API Token**:
   - Go to https://id.atlassian.com/manage-profile/security/api-tokens
   - Generate a new token if current one is expired
   - Update `JIRA_TOKEN` environment variable

2. **Check Project Permissions**:
   - Go to JIRA project settings
   - Navigate to "Project permissions" 
   - Ensure your user has "Create Issues" permission

3. **Verify Email**:
   - Confirm `JIRA_EMAIL` matches your Atlassian account email

4. **Test Authentication**:
   ```bash
   curl -u "email:token" "https://your-domain.atlassian.net/rest/api/3/myself"
   ```

### **Status**: ✅ **RESOLVED** (Enhanced Error Handling)
### **User Action Required**: Check JIRA permissions and regenerate API token if needed

---

## 🔧 **Future Issue Template**

### **Problem**
[Describe the issue with error messages/logs]

### **Root Cause**
[Analysis of why this happened]

### **Solution Applied**
[Code changes, configuration updates, or process changes]

### **Status**: [🔄 IN PROGRESS | ✅ RESOLVED | ❌ BLOCKED]
### **Verification**: [How to verify the fix works]

---

## 📋 **Common Solutions Reference**

### **JIRA Authentication Issues**
- Check API token validity
- Verify email/token combination
- Confirm project permissions
- Test with curl command

### **Path Resolution Issues**
- Use absolute paths or paths relative to repository root
- Account for different working directories (local vs CI/CD)
- Test from multiple directory contexts

### **GitHub Actions Issues**
- Check environment variables are properly set
- Verify working directory expectations
- Test locally with same directory structure

### **YAML Generation Issues**
- Validate template files exist
- Check file permissions
- Verify temp directory creation

---

## 🚀 **Enhancement Tracking**

### **Completed Enhancements**
- ✅ Enhanced spec identification logging
- ✅ Better error messages for 401 errors
- ✅ Path resolution fixes for cross-environment compatibility
- ✅ Comprehensive troubleshooting guidance

### **Planned Enhancements**
- 🔄 Add retry logic for transient API failures
- 🔄 Support for custom JIRA field mappings
- 🔄 Batch processing for large spec sets
- 🔄 Progress indicators for long-running operations

---

## 📞 **Quick Reference**

### **Logs to Check**
- JIRA API response errors
- Path resolution validation logs
- Spec identification logs
- GitHub link generation logs

### **Environment Variables to Verify**
- `JIRA_URL`
- `JIRA_EMAIL` 
- `JIRA_TOKEN`
- `JIRA_PROJECT`
- `GITHUB_REPO_URL`
- `GITHUB_BRANCH`

### **Files to Check**
- `specs/` folder structure
- `templates/templates.yaml`
- Script working directory vs repository root

---

*Last updated: 2026-03-09*
*Next review: Weekly or when new issues are reported*