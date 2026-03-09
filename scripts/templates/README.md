# JIRA Sync YAML Templates

This directory contains a unified YAML template file (`templates.yaml`) for different JIRA issue types used by the JIRA sync script.

## Template Structure

### Single File Design (`templates.yaml`)
All issue type templates are consolidated into one file with this structure:

```yaml
templates:
  epic: { ... }
  story: { ... }
  task: { ... }
  subtask: { ... }
  bug: { ... }
```

## Templates

### Epic Template (`templates.yaml:epic`)
- Used for main specification files (`spec.md`)
- Includes epic-specific fields like `epic_name` and `epic_description`
- Labels: `epic`, `spec-sync`

### Story Template (`templates.yaml:story`)
- Used for individual story markdown files
- Links to parent epic via `parent` field
- Includes `acceptance_criteria` extraction
- Supports `story_points` estimation
- Labels: `story`, `spec-sync`

### Task Template (`templates.yaml:task`)
- Used for high-level tasks
- Links to parent story via `parent` field
- Includes `time_estimate` field
- Labels: `task`, `spec-sync`

### Subtask Template (`templates.yaml:subtask`)
- Used for detailed subtasks/sub-tasks
- Links to parent task/story via `parent` field
- Includes `category` for automatic classification
- Auto-categorized based on keywords:
  - `testing` - test, testing, verify
  - `backend` - api, endpoint, service  
  - `frontend` - ui, frontend, component
  - `documentation` - doc, documentation
  - `general` - default category
- Labels: `subtask`, `spec-sync`

### Bug Template (`templates.yaml:bug`)
- Used for bug reports and defect tracking
- Links to parent story/epic via `parent` field
- Includes bug-specific fields:
  - `severity` - Bug severity level
  - `environment` - Environment where bug occurs
  - `steps_to_reproduce` - Detailed reproduction steps
  - `expected_behavior` - What should happen
  - `actual_behavior` - What actually happens
- Auto-extracts structured sections from markdown:
  - `## Steps to Reproduce`
  - `## Expected Behavior` 
  - `## Actual Behavior`
- Labels: `bug`, `spec-sync`
- Default priority: `High`

## Template Variables

All templates support these placeholder variables:

- `{SUMMARY}` - Issue title (truncated to 255 chars)
- `{SOURCE_FILE}` - Relative path to source markdown file
- `{GITHUB_LINK}` - Full GitHub URL to source file
- `{CONTENT}` - Full markdown content from source file
- `{PARENT_KEY}` - JIRA key of parent issue (if applicable)

### Epic-Specific Variables
- `{EPIC_NAME}` - Epic name (same as summary)
- `{EPIC_DESCRIPTION}` - Epic description (truncated to 500 chars)

### Story-Specific Variables  
- `{ACCEPTANCE_CRITERIA}` - Extracted from "## Acceptance Criteria" section

### Task/Subtask-Specific Variables
- `{TIME_ESTIMATE}` - Estimated time (auto-assigned based on category)
- `{CATEGORY}` - Task category (auto-detected from keywords)

### Bug-Specific Variables
- `{SEVERITY}` - Bug severity level (default: "Medium")
- `{ENVIRONMENT}` - Environment where bug occurs
- `{STEPS_TO_REPRODUCE}` - Extracted from "## Steps to Reproduce" section
- `{EXPECTED_BEHAVIOR}` - Extracted from "## Expected Behavior" section
- `{ACTUAL_BEHAVIOR}` - Extracted from "## Actual Behavior" section

## Customization

You can customize the unified template by editing `templates.yaml`:

1. **Adding custom fields** - Add JIRA custom fields specific to your instance
2. **Modifying labels** - Change or add labels as needed
3. **Adjusting priorities** - Set different default priorities
4. **Adding components** - Map to specific JIRA components
5. **Custom field mapping** - Update field names to match your JIRA setup
6. **New issue types** - Add new template sections under `templates:`

### Example Customization

```yaml
templates:
  epic:
    # ... existing fields ...
    custom_fields:
      epic_theme: "{EPIC_THEME}"
      business_value: "High"
      target_release: "{TARGET_RELEASE}"
  
  custom_issue_type:
    issue_type: "Improvement"
    summary: "{SUMMARY}"
    # ... other fields ...
```

## Field Mapping Notes

- `story_points` maps to `customfield_10016` (common Scrum field)
- Custom field IDs may vary between JIRA instances
- Check your JIRA setup for exact field names/IDs
- Use JIRA REST API to discover available fields:
  ```bash
  curl -u email:token "https://your-domain.atlassian.net/rest/api/3/field"
  ```