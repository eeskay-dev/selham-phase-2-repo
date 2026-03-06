# GitHub Actions JIRA Integration Setup 

## Issue: Deprecated actions/upload-artifact@v3

### Error Description
The GitHub Actions workflow fails due to using a deprecated version of `actions/upload-artifact@v3`.

### Error Trace
```
Prepare all required actions
Getting action download info
Error: This request has been automatically failed because it uses a deprecated version of `actions/upload-artifact: v3`. Learn more: https://github.blog/changelog/2024-04-16-deprecation-notice-v3-of-the-artifact-actions/
##[debug]GitHub.DistributedTask.WebApi.UnresolvableActionDownloadInfoException: This request has been automatically failed because it uses a deprecated version of `actions/upload-artifact: v3`. Learn more: https://github.blog/changelog/2024-04-16-deprecation-notice-v3-of-the-artifact-actions/
```

### Root Cause
GitHub deprecated `actions/upload-artifact@v3` as of April 16, 2024. Workflows using this version automatically fail.

### Solution Steps

1. **Identify deprecated action usage**
   ```bash
   grep -r "actions/upload-artifact@v3" .github/workflows/
   ```

2. **Update to latest version**
   - Change `actions/upload-artifact@v3` to `actions/upload-artifact@v4`
   - The v4 API is compatible with v3 for basic usage

3. **Verify the fix**
   ```yaml
   # Before (deprecated)
   - uses: actions/upload-artifact@v3
   
   # After (current)
   - uses: actions/upload-artifact@v4
   ```

4. **Validate YAML syntax**
   ```bash
   # Validate workflow file syntax
   python3 -c "import yaml; yaml.safe_load(open('.github/workflows/jira-integration.yml', 'r').read()); print('✅ YAML is valid')"
   ```

5. **Test the workflow**
   - Commit and push the changes
   - Trigger a manual workflow run to validate
   - Check that artifacts are uploaded successfully

### Fixed Configuration

Updated `.github/workflows/jira-integration.yml` with latest action versions:

```yaml
# Updated GitHub Actions (all latest versions)
- uses: actions/checkout@v4           # ✅ Current
- uses: actions/setup-python@v5       # 🔄 Updated from v4  
- uses: actions/upload-artifact@v4    # 🔄 Updated from v3 (CRITICAL FIX)
- uses: actions/github-script@v7      # 🔄 Updated from v6

# Archive JIRA Artifacts step (main fix)
- name: Archive JIRA Artifacts
  if: always()
  uses: actions/upload-artifact@v4  # Updated from v3
  with:
    name: jira-artifacts-${{ steps.feature.outputs.feature_name }}
    path: |
      jira/${{ steps.feature.outputs.feature_name }}-draft.yaml
      jira/${{ steps.feature.outputs.feature_name }}-map.json
      push_output.log
    retention-days: 30
```

### Status
✅ **RESOLVED** - Updated to actions/upload-artifact@v4

### Prevention
- Regularly check for deprecated GitHub Actions
- Use Dependabot or similar tools to track action updates
- Monitor GitHub changelog for deprecation notices