# JIRA Work Items Template: [FEATURE_NAME]

**Input**: Generated from `/specs/[###-feature-name]/tasks.md`
**Output**: `jira/[###-feature-name]-draft.yaml`
**Contract**: YAML-based work item definitions following JIRA API schema

---

## Epic Definition

```yaml
epic:
  summary: "[FEATURE_NAME] - [Brief Epic Description]"
  description: |
    [Multi-line description from spec.md summary]
    
    **Epic Goals:**
    - [Primary business objective]
    - [Secondary objectives]
    
    **Success Criteria:**
    - [Measurable outcome 1]
    - [Measurable outcome 2]
    
    **Related Documentation:**
    - Specification: specs/[###-feature-name]/spec.md
    - Implementation Plan: specs/[###-feature-name]/plan.md
    - Task Breakdown: specs/[###-feature-name]/tasks.md
  
  labels:
    - "speckit-generated"
    - "[feature-category]"
    - "[priority-level]"
  
  components:
    - "[Component Name]"
  
  customFields:
    businessValue: "[High/Medium/Low]"
    targetRelease: "[Release Version]"
    estimatedEffort: "[Story Points or Time]"
```

---

## Story Templates

### User Story Template (from spec.md user scenarios)

```yaml
stories:
  - id: "US[#]"
    summary: "[User Story Title] - [Brief Description]"
    description: |
      **As a** [user type]
      **I want** [functionality]
      **So that** [business value]
      
      **Priority:** [P1/P2/P3] - [Priority Justification]
      
      **Acceptance Criteria:**
      [List from spec.md acceptance scenarios]
      
      **Independent Testing:**
      [How this story can be tested independently]
      
      **Definition of Done:**
      - [ ] Contract specifications defined
      - [ ] Implementation complete
      - [ ] Integration tests passing
      - [ ] Documentation updated
      - [ ] Code reviewed and approved
    
    issueType: "Story"
    priority: "[High/Medium/Low]"
    labels:
      - "user-story"
      - "[story-category]"
    
    components:
      - "[Component Name]"
    
    customFields:
      storyPoints: [Number]
      acceptanceCriteria: |
        [Detailed acceptance criteria from spec.md]
```

---

## Task Templates

### Development Task Template (from tasks.md)

```yaml
tasks:
  - id: "[TASK_ID]" # e.g., T001, T002
    parentStory: "[US#]" # Links to user story
    summary: "[Phase] - [Task Description]"
    description: |
      **Task Category:** [Setup/Implementation/Testing/Documentation]
      
      **Description:**
      [Detailed task description from tasks.md]
      
      **File Paths:**
      [Exact file paths specified in tasks.md]
      
      **Dependencies:**
      - Blocks: [List of blocking task IDs]
      - Blocked by: [List of prerequisite task IDs]
      
      **Parallel Execution:** [Yes/No - based on [P] flag]
      
      **Contract Requirements:**
      - [ ] YAML schema validation
      - [ ] API contract compliance
      - [ ] Integration contract adherence
      
      **Acceptance Criteria:**
      - [ ] Implementation matches task specification
      - [ ] All file paths created/modified as specified
      - [ ] Integration tests passing
      - [ ] Code follows constitutional principles
    
    issueType: "Sub-task"
    priority: "[Highest/High/Medium/Low]"
    labels:
      - "speckit-task"
      - "[phase-name]" # e.g., setup, implementation, testing
      - "[parallel]" # if [P] flag present
    
    components:
      - "[Component Name]"
    
    customFields:
      taskPhase: "[Setup/Implementation/Testing/Documentation]"
      estimatedHours: [Number]
      technicalComplexity: "[Low/Medium/High]"
      blockingDependencies: "[Task IDs]"
```

---

## Configuration Schema

### JIRA Project Configuration

```yaml
project:
  key: "[PROJECT_KEY]" # e.g., SPEC, WORKFLOW
  name: "[Project Name]"
  
issueTypes:
  epic: "Epic"
  story: "Story" 
  task: "Sub-task"
  
priorities:
  critical: "Highest"
  high: "High"
  medium: "Medium"
  low: "Low"

fields:
  required:
    - summary
    - description
    - issueType
    - project
  
  custom:
    storyPoints: "customfield_10016"
    businessValue: "customfield_10017"
    targetRelease: "customfield_10018"
    estimatedEffort: "customfield_10019"
    acceptanceCriteria: "customfield_10020"
    taskPhase: "customfield_10021"
    technicalComplexity: "customfield_10022"
```

---

## Workflow State Mapping

### JIRA Status → Speckit Phase Mapping

```yaml
statusMapping:
  # Planning Phase
  "To Do": 
    speckit: "not-started"
    description: "Task defined but not yet begun"
  
  "In Planning":
    speckit: "design-phase"  
    description: "Contract definition and architecture planning"
  
  # Development Phase  
  "In Progress":
    speckit: "implementation"
    description: "Active development work"
  
  "Code Review":
    speckit: "review-phase"
    description: "Pull request review and validation"
    
  # Testing Phase
  "Testing":
    speckit: "integration-testing"
    description: "Contract compliance and integration validation"
  
  # Completion
  "Done":
    speckit: "completed"
    description: "Fully implemented and validated"
  
  "Blocked":
    speckit: "blocked"
    description: "Waiting on dependencies or external factors"
```

---

## Generation Rules

### Automatic Field Population

1. **Epic Creation**: One epic per feature specification
2. **Story Mapping**: One JIRA story per user story from spec.md (prioritized P1, P2, P3)
3. **Task Breakdown**: Tasks from tasks.md grouped by user story and phase
4. **Dependency Linking**: Automatic parent-child relationships and blocking dependencies
5. **Label Generation**: Automatic labeling based on task properties and phases

### Validation Requirements

```yaml
validation:
  required:
    - Epic must reference valid spec.md file
    - Stories must map to user scenarios from spec.md
    - Tasks must include exact file paths
    - All YAML must validate against JIRA API schema
  
  constitutional:
    - Contract specifications must be defined before implementation tasks
    - Integration tests required for all cross-component tasks  
    - YAML configuration drives all workflow behavior
    - State transitions must be traceable and auditable
```

---

## Usage Workflow

1. **Generate Draft**: `python scripts/generate_jira_draft.py specs/[feature]/`
2. **Review & Edit**: Manual review of generated `jira/[feature]-draft.yaml`
3. **Validate Schema**: `python scripts/validate_jira_schema.py jira/[feature]-draft.yaml`
4. **Push to JIRA**: `python scripts/push_jira.py jira/[feature]-draft.yaml`
5. **Store Mapping**: Auto-generated `jira/[feature]-map.json` for task ID tracking

### Quality Gates

- [ ] YAML schema validation passes
- [ ] All required fields populated  
- [ ] Constitutional principles verified
- [ ] Cross-reference validation complete
- [ ] Integration contract compliance checked