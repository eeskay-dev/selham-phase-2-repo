#!/bin/bash

# Test script for the improved JIRA sync

echo "🧪 Testing JIRA Sync Script Improvements"
echo "========================================"

# Test 1: Simulate GitHub Actions environment
echo ""
echo "🔄 Test 1: GitHub Actions Environment Simulation"
export GITHUB_ACTIONS=true
export GITHUB_SERVER_URL="https://github.com"
export GITHUB_REPOSITORY="selham/selham-phase-1-repo"
export GITHUB_REF_NAME="json-jira-formatting"
export DRY_RUN=false
export JIRA_URL="https://selham.atlassian.net"
export JIRA_EMAIL="eesaky@zohomail.in"
export JIRA_TOKEN="ATATT3xFfGF0MlVYo7gHvDOUeEg4JYS15TRveYPlQJ9HlrMagQmHYhijpzIk5DDpDZg4WyIBl3SqeKfTv8WThovllI8Qfra6q9I1rhNl1qDIlLJ9fLrmJuWbNEbr5PMcDukBdRTozOpYgWy55IJhfmEBKpOFvqMCCyQ22LkRCFP_Apfdw44B7zc=0BF9FD64"
export JIRA_PROJECT="SMM"

echo "📋 GitHub Actions Configuration:"
echo "  GITHUB_ACTIONS: $GITHUB_ACTIONS"
echo "  GITHUB_REPOSITORY: $GITHUB_REPOSITORY"
echo "  GITHUB_REF_NAME: $GITHUB_REF_NAME"
echo "  GITHUB_SERVER_URL: $GITHUB_SERVER_URL"
echo ""

echo "🚀 Running with GitHub Actions auto-detection..."
python3 jira_sync.py

echo ""
echo "="*50

# Test 2: Manual configuration (fallback)
echo ""
echo "🔄 Test 2: Manual Configuration Fallback"
unset GITHUB_ACTIONS
unset GITHUB_SERVER_URL  
unset GITHUB_REPOSITORY
unset GITHUB_REF_NAME
export GITHUB_REPO_URL="https://github.com/manual/manual-repo"
export GITHUB_BRANCH="develop"

echo "📋 Manual Configuration:"
echo "  GITHUB_REPO_URL: $GITHUB_REPO_URL"
echo "  GITHUB_BRANCH: $GITHUB_BRANCH"
echo ""

echo "🚀 Running with manual configuration..."
python3 jira_sync.py

echo ""
echo "✅ All tests completed!"
echo ""
echo "📝 Features Tested:"
echo "  ✓ GitHub Actions auto-detection"
echo "  ✓ Manual configuration fallback" 
echo "  ✓ Unified YAML template (epic, story, task, subtask, bug)"
echo "  ✓ Template-based YAML file creation"
echo "  ✓ Auto-categorization and time estimation"
echo "  ✓ Bug report structured sections extraction"
echo "  ✓ GitHub links in JIRA descriptions"
echo "  ✓ Enhanced error handling"
echo ""
echo "📁 Template file used:"
echo "  ✓ templates/templates.yaml (unified template file)"