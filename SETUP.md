# JIRA Integration Setup Guide

## Prerequisites
- Python 3.9+
- JIRA instance with API access
- GitHub repository

## Installation

### 1. Copy Files to Your Repository
```bash
# Copy the entire jira-integration tool to your project
cp -r /path/to/jira-integration/* your-project/
cd your-project
```

### 2. Install Dependencies  
```bash
pip install -r requirements.txt
```

### 3. Configure JIRA Access
```bash
# Copy configuration template
cp scripts/config/local.env.template scripts/config/local.env

# Edit with your JIRA details
nano scripts/config/local.env
```

Required configuration:
```bash
export JIRA_URL="https://your-domain.atlassian.net"
export JIRA_EMAIL="your-email@example.com"
export JIRA_TOKEN="your-personal-access-token"  
export JIRA_PROJECT="YOUR_PROJECT_KEY"
export GITHUB_REPO_URL="https://github.com/your-org/your-repo"
```

### 4. Set Up GitHub Actions (Optional)
```bash
# Add GitHub secrets for automation:
# JIRA_URL, JIRA_EMAIL, JIRA_TOKEN, JIRA_PROJECT
```

### 5. Create Your First Spec
```bash
mkdir -p specs/my-feature
echo "# My Feature" > specs/my-feature/spec.md
```

### 6. Test the Integration
```bash
# Validate configuration
python3 scripts/validate_jira_config.py

# Run in dry-run mode
export DRY_RUN="true"
python3 scripts/jira_sync.py

# Create actual issues
export DRY_RUN="false"  
python3 scripts/jira_sync.py
```

## Getting JIRA Personal Access Token

1. **Login to JIRA**: Go to your Atlassian domain
2. **Profile Settings**: Click your avatar → Account Settings
3. **Security Tab**: Go to Security section  
4. **Personal Access Tokens**: Create new token
5. **Token Scopes**: Select these permissions:
   - `read:jira-user` - Read user information
   - `read:jira-work` - Read issues and projects  
   - `write:jira-work` - Create and update issues
6. **Copy Token**: Save it securely (shown only once)

## Project Structure After Setup

```
your-project/
├── scripts/                   # JIRA integration scripts
│   ├── jira_sync.py          # Main sync script
│   ├── validate_jira_config.py
│   ├── config/local.env      # Your local configuration
│   └── templates/templates.yaml
├── .github/
│   └── workflows/jira-integration.yml
├── specs/                    # Your specification files
│   └── example-feature/      
├── requirements.txt          
└── README.md                 
```

## Usage Patterns

### Development Workflow
```bash
# 1. Create specification
mkdir specs/new-feature
echo "# New Feature Spec" > specs/new-feature/spec.md

# 2. Test sync
./scripts/config/local-setup.sh  # Interactive mode

# 3. Review JIRA issues created
```

### CI/CD Integration
- Specs in `specs/` directory automatically sync on push
- GitHub Actions handles authentication via secrets
- JIRA issues include direct links back to GitHub

## Troubleshooting

### Common Issues
- **401 Error**: Check JIRA token and email
- **404 Error**: Verify JIRA URL and project key
- **403 Error**: Ensure token has required permissions
- **Parsing Error**: Check markdown file format

### Debug Mode
```bash
export DRY_RUN="true"  # Preview without creating
python3 scripts/jira_sync.py
```

### Validation
```bash  
python3 scripts/validate_jira_config.py
```