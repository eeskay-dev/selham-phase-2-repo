# JIRA Integration Usage Guide

This guide covers the complete SPEC-KIT + JIRA workflow for converting specifications into JIRA work items.

## Prerequisites

1. **JIRA Access**: You need a JIRA instance with appropriate permissions
2. **API Token**: Generate at https://id.atlassian.com/manage-profile/security/api-tokens  
3. **Python Dependencies**: Install with `pip3 install -r requirements.txt`

## Configuration

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Update `.env` with your JIRA details:
   ```bash
   JIRA_URL=https://your-company.atlassian.net
   JIRA_PROJECT=SPEC
   JIRA_EMAIL=your-email@company.com
   JIRA_TOKEN=your_api_token
   ```

3. Source the environment:
   ```bash
   source .env
   ```

## Workflow Steps

### 1. Generate JIRA Draft
Convert specification to reviewable JIRA YAML:

```bash
# For specific feature
python3 scripts/generate_jira_draft.py specs/001-multi-brand-menu-mgmt/

# Auto-detect latest feature  
python3 scripts/generate_jira_draft.py
```

**Output**: `jira/{feature}-draft.yaml`

### 2. Review Draft (Manual Step)
Edit the generated YAML file to review/update:
- Epic title and description
- Story priorities and acceptance criteria  
- Task assignments and complexity
- Custom field values

### 3. Push to JIRA
Create actual JIRA issues from approved draft:

```bash
# Test first (dry run)
python3 scripts/push_jira.py --dry-run

# Push to JIRA
python3 scripts/push_jira.py jira/001-multi-brand-menu-mgmt-draft.yaml
```

**Output**: 
- JIRA Epic, Stories, and Tasks created
- Mapping file: `jira/{feature}-map.json`

## JIRA Hierarchy Created

```
Epic (SPEC-001)
├── Story 1 (SPEC-001-US1) - Priority P1  
│   ├── Task 1.1 (SPEC-001-T001)
│   └── Task 1.2 (SPEC-001-T002)
├── Story 2 (SPEC-001-US2) - Priority P2
│   └── Task 2.1 (SPEC-001-T003)
└── Story N...
```

## Mapping File Structure

The mapping file tracks relationships between spec tasks and JIRA issues:

```json
{
  "mapping": {
    "SPEC-001": "PROJ-123",           // Epic  
    "SPEC-001-US1": "PROJ-124",      // Story 1
    "SPEC-001-T001": "PROJ-125"      // Task 1
  },
  "created_issues": {
    "epic": "PROJ-123",
    "stories": ["PROJ-124", "PROJ-126"],
    "tasks": ["PROJ-125", "PROJ-127"],
    "total": 4
  }
}
```

## Next Steps in Workflow

After JIRA issues are created:

1. **Business Review**: Teams review tickets in JIRA, add comments/clarifications
2. **Sync Feedback**: Run `python3 scripts/sync_jira_comments.py` (future script)
3. **Task Assignment**: Assign JIRA tasks to developers
4. **Development**: Developers create feature branches referencing JIRA tickets
5. **Implementation**: Use `/speckit implement JIRA-TICKET` for code generation

## Troubleshooting

### Connection Issues
```bash
# Test JIRA connection
python3 scripts/push_jira.py --dry-run
```

### Custom Field Mapping
If you get custom field errors, check your JIRA instance's field IDs and update the mapping in `scripts/push_jira.py`.

Common fields to verify:
- Epic Name: `customfield_10011`
- Epic Link: `customfield_10014`
- Story Points: `customfield_10016`

### Permission Issues
Ensure your JIRA user has permissions to:
- Create issues in the target project
- Link issues (for Epic/Story relationships)
- Set custom fields

## Advanced Usage

### Batch Processing
```bash
# Process multiple features
for feature in specs/*/; do
  python3 scripts/generate_jira_draft.py "$feature"
done
```

### Integration with CI/CD
```bash
# Automated JIRA creation on spec updates
git diff --name-only | grep "specs/.*/spec.md" | \
  xargs -I {} python3 scripts/generate_jira_draft.py {}
```