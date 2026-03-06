---
name: JIRA Integration Issue
about: Report problems with automated JIRA integration
title: "[JIRA] Integration issue with feature: [FEATURE_NAME]"
labels: ["jira-integration", "bug", "automation"]
assignees: []
---

## JIRA Integration Issue

### Feature Information
- **Feature Name**: [e.g., 001-multi-brand-menu-mgmt]
- **Spec Path**: [e.g., specs/001-multi-brand-menu-mgmt/]
- **Trigger**: [PR merge / Manual workflow / Other]

### Problem Description
<!-- Describe what went wrong with the JIRA integration -->

### Workflow Information
- **Workflow Run**: [Link to failed GitHub Actions workflow]
- **PR Number**: [If triggered by PR merge]
- **Error Stage**: [Detection / Generation / Validation / JIRA Push]

### Error Details
<!-- Paste relevant error messages from workflow logs -->
```
[Paste error logs here]
```

### Expected Behavior
<!-- What should have happened? -->

### Actual Behavior
<!-- What actually happened? -->

### JIRA Configuration
<!-- Check all that apply -->
- [ ] JIRA_URL secret is set
- [ ] JIRA_EMAIL secret is set  
- [ ] JIRA_TOKEN secret is set
- [ ] JIRA_PROJECT secret is set
- [ ] JIRA user has proper permissions
- [ ] JIRA project exists and is accessible

### Spec File Status
<!-- Check all that apply -->
- [ ] spec.md file exists and is properly formatted
- [ ] tasks.md file exists (if applicable)
- [ ] JIRA draft was generated successfully
- [ ] Draft passes validation locally

### Attempted Solutions
<!-- What have you already tried to fix this? -->

### Additional Context
<!-- Any other relevant information -->

---

## For Automated Issues

<!-- This section is auto-populated by failed workflows -->

**Workflow Details:**
- Run ID: {{ github.run_id }}
- Feature: {{ feature_name }}  
- Trigger: {{ github.event_name }}

**Quick Resolution Steps:**
1. Check workflow logs: [Workflow Link]({{ github.server_url }}/{{ github.repository }}/actions/runs/{{ github.run_id }})
2. Test locally: `python3 scripts/push_jira.py jira/{{ feature_name }}-draft.yaml --dry-run`
3. Verify JIRA configuration and permissions
4. Re-run workflow after fixes