# SPEC-KIT + JIRA Workflow Management

Complete automation for converting specifications into JIRA work items with GitHub Actions integration.

## 🚀 Quick Start

### Automated Workflow (Recommended)
1. **Configure GitHub Secrets**: See [Setup Guide](docs/github-actions-setup.md)
2. **Create Specification**: Add `spec.md` in `specs/###-feature-name/`
3. **Create Pull Request**: Include your specification changes
4. **Merge PR**: Automatic JIRA integration triggers on merge to main

### Manual Workflow
```bash
# Generate JIRA draft from specification
python3 scripts/generate_jira_draft.py specs/001-feature-name/

# Review and edit generated draft
edit jira/001-feature-name-draft.yaml

# Push to JIRA (test first)
python3 scripts/push_jira.py --dry-run
python3 scripts/push_jira.py
```

## 📋 Complete Workflow

### 1. Product Requirement
   - Product Manager creates specification
   - File: `specs/<feature>/spec.md`

### 2. Architecture Planning
   - Architect runs: `speckit plan`
   - Generates: `spec.md`, `plan.md`, `tasks.md`

### 3. 🤖 **Automated JIRA Integration** (GitHub Actions)
   - **Trigger**: PR merge to main branch
   - **Detection**: Automatically finds changed specifications
   - **Generation**: Creates JIRA draft from spec files
   - **Push**: Creates Epic → Stories → Tasks hierarchy
   - **Notification**: Comments on PR with JIRA links

### 4. Manual JIRA Integration (Alternative)
   Script converts spec to reviewable JIRA draft:
   ```bash
   python3 scripts/generate_jira_draft.py
   ```
   Output: `jira/<feature>-draft.yaml`

### 5. Manual Review
   - Architect/Product Manager reviews generated draft
   - Updates: epic title, stories, task descriptions, acceptance criteria

### 6. Push to JIRA (Manual)
   After approval:
   ```bash
   python3 scripts/push_jira.py
   ```
   Creates: Epic → Stories → Tasks hierarchy

### 7. Store Mapping
   - Auto-generated mapping file: `jira/<feature>-map.json`
   - Maps spec task IDs to JIRA issue keys

7. Business Review
   - Business teams review tickets in JIRA.
   - They may:
       add comments
       clarify requirements
       update ticket content

8. Sync Feedback to Specs
   - Script pulls JIRA comments:

       python scripts/sync_jira_comments.py

   - Updates:
       specs/<feature>/tasks.md

9. Task Assignment
   - JIRA assigns tasks to developers.

10. Developer Creates Feature Branch
    Example:

       feature/PROJ-123-product-api

11. Implementation with Spec-Kit
    Developer runs:

       speckit implement PROJ-123

    Generates:
       service skeleton
       API structure
       test scaffolding

12. Development
    Developer:
       updates code
       runs tests
       validates implementation

13. Pull Request
    Developer creates PR referencing JIRA ticket.

14. Code Review
    Reviewers:
       comment
       approve
       request changes

15. Merge
    After PR merge:
       JIRA ticket marked Done.

16. Continuous Documentation
    Discussions from:
       JIRA comments
       PR reviews
       spec updates

    are synced back into:

       spec.md
       plan.md
       tasks.md

    Specs become the final design history.