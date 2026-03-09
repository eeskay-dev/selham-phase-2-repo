# JIRA Sync Integration Tool

A streamlined tool for automatically synchronizing specification files with JIRA issues. Converts markdown specifications into structured JIRA epics, stories, and tasks with proper linking back to GitHub.

## ✨ Features

- **Auto-sync** markdown specs to JIRA issues (Epic → Stories → Tasks)
- **GitHub Integration** with direct links in JIRA descriptions
- **Flexible Templates** for different issue types
- **Performance Optimized** for large specification files
- **GitHub Actions** support for CI/CD integration
- **Local Development** with easy configuration

## 🚀 Quick Start

### 1. Setup
```bash
# Clone or copy the scripts to your repository
git clone <this-repo> jira-integration
cd jira-integration

# Copy configuration template
cp scripts/config/local.env.template scripts/config/local.env
```

### 2. Configure JIRA Credentials
Edit `scripts/config/local.env`:
```bash
# Required JIRA settings
export JIRA_URL="https://your-domain.atlassian.net"
export JIRA_EMAIL="your-email@example.com" 
export JIRA_TOKEN="your-personal-access-token"
export JIRA_PROJECT="YOUR_PROJECT_KEY"

# GitHub settings (auto-detected in GitHub Actions)
export GITHUB_REPO_URL="https://github.com/your-org/your-repo"
export GITHUB_BRANCH="main"

# Execution mode
export DRY_RUN="true"  # Set to "false" to create actual issues
```

### 3. Prepare Your Specs
Create specification files in a `specs/` directory:
```
specs/
  feature-name/
    spec.md          # Creates Epic
    requirements.md  # Creates Story with subtasks
    other-specs.md   # Creates additional Stories
```

### 4. Run Sync
```bash
# Interactive mode
./scripts/config/local-setup.sh

# Or direct execution
source scripts/config/local.env && python3 scripts/jira_sync.py
```
## 📁 Project Structure

```
├── scripts/                    # Core JIRA integration
│   ├── jira_sync.py           # Main sync script
│   ├── validate_jira_config.py # Configuration validator
│   ├── config/                # Local configuration
│   └── templates/             # JIRA issue templates
├── .github/                   # GitHub integration
│   ├── workflows/            # GitHub Actions workflows
│   └── ISSUE_TEMPLATE/       # Issue templates
├── specs/                    # Your specification files (create this)
└── README.md                 # This file
```

## 🔧 JIRA Setup

### Getting Personal Access Token
1. Go to: `https://your-domain.atlassian.net/secure/ViewProfile.jspa`
2. Click "Personal Access Tokens" tab
3. Create token with scopes: `read:jira-user`, `read:jira-work`, `write:jira-work`

### Issue Type Mapping
The tool automatically maps to available JIRA issue types:
- Epic → Epic (or first available type)
- Story → Story (or Task/Epic fallback)  
- Task → Sub-task (or Task fallback)
- Bug → Bug (or Task fallback)

## 📝 Specification Format

### Epic (spec.md)
```markdown
# Feature Name
Description of the feature...

## User Scenarios & Testing
Content that becomes epic description...
```

### Story (other .md files)
```markdown  
# Story Title
Story description...

## Section 1
- Task item 1
- Task item 2

## Section 2  
- Another task
```

## ⚙️ GitHub Actions

Copy `.github/workflows/jira-integration.yml` to enable automatic sync on push:

```yaml
name: JIRA Integration
on:
  push:
    paths: ['specs/**']
jobs:
  sync-jira:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Sync to JIRA
        env:
          JIRA_URL: ${{ secrets.JIRA_URL }}
          JIRA_EMAIL: ${{ secrets.JIRA_EMAIL }}  
          JIRA_TOKEN: ${{ secrets.JIRA_TOKEN }}
          JIRA_PROJECT: ${{ secrets.JIRA_PROJECT }}
          DRY_RUN: "false"
        run: |
          pip install -r requirements.txt
          python3 scripts/jira_sync.py
```

## 🛠️ Customization

### Templates
Edit `scripts/templates/templates.yaml` to customize issue creation:
- Issue types and fields
- Labels and priorities  
- Custom field mappings

### Issue Type Mappings
Set environment variables to override defaults:
```bash
export ISSUE_TYPE_EPIC="Epic"
export ISSUE_TYPE_STORY="User Story"  
export ISSUE_TYPE_TASK="Sub-task"
export ISSUE_TYPE_BUG="Defect"
```

## 🔍 Troubleshooting

### Common Issues
1. **401 Authentication Error**: Check JIRA credentials and token permissions
2. **400 Hierarchy Error**: Verify issue type hierarchy in your JIRA project  
3. **No specs found**: Ensure `specs/` directory exists with `.md` files

### Debug Mode
```bash
export DRY_RUN="true"  # Preview without creating issues
python3 scripts/jira_sync.py
```

### Validation
```bash
python3 scripts/validate_jira_config.py  # Test JIRA connection
```

## 📄 License

MIT License - Feel free to adapt for your projects.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Test with your JIRA instance  
4. Submit a pull request

---

**Made with ❤️ for seamless spec-to-JIRA workflows**
       PR reviews
       spec updates

    are synced back into:

       spec.md
       plan.md
       tasks.md

    Specs become the final design history.