#!/bin/bash

# JIRA Sync Local Configuration Script
# This script helps you set up and run JIRA sync locally

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIG_FILE="$SCRIPT_DIR/local.env"

echo "🔧 JIRA Sync Local Configuration"
echo "================================"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Configuration file not found: $CONFIG_FILE"
    echo "💡 Please create the configuration file first:"
    echo "   cp $SCRIPT_DIR/local.env.template $CONFIG_FILE"
    echo "   # Edit $CONFIG_FILE with your JIRA credentials"
    exit 1
fi

# Load configuration
echo "📋 Loading configuration from: $CONFIG_FILE"
source "$CONFIG_FILE"

# Validate required variables
missing_vars=()
[ -z "$JIRA_URL" ] && missing_vars+=("JIRA_URL")
[ -z "$JIRA_EMAIL" ] && missing_vars+=("JIRA_EMAIL")
[ -z "$JIRA_TOKEN" ] && missing_vars+=("JIRA_TOKEN")
[ -z "$JIRA_PROJECT" ] && missing_vars+=("JIRA_PROJECT")

if [ ${#missing_vars[@]} -gt 0 ] && [ "$DRY_RUN" != "true" ]; then
    echo "❌ Missing required variables: ${missing_vars[*]}"
    echo "💡 Please update $CONFIG_FILE with your JIRA credentials"
    exit 1
fi

# Display current configuration
echo ""
echo "📊 Current Configuration:"
echo "   JIRA_URL: $JIRA_URL"
echo "   JIRA_EMAIL: $JIRA_EMAIL"
echo "   JIRA_PROJECT: $JIRA_PROJECT"
echo "   GITHUB_REPO_URL: $GITHUB_REPO_URL"
echo "   GITHUB_BRANCH: $GITHUB_BRANCH"
echo "   DRY_RUN: $DRY_RUN"
echo ""

# Change to project root
cd "$PROJECT_ROOT"
echo "📁 Working directory: $PROJECT_ROOT"

# Check if specs directory exists
if [ ! -d "specs" ]; then
    echo "⚠️  WARNING: No 'specs' directory found in $PROJECT_ROOT"
    echo "💡 Make sure you're running this from the correct project directory"
fi

# Function to run validation
run_validation() {
    echo ""
    echo "🔍 Validating JIRA configuration..."
    python3 scripts/validate_jira_config.py
}

# Function to run sync
run_sync() {
    echo ""
    echo "🚀 Running JIRA sync..."
    python3 scripts/jira_sync.py
}

# Function to run tests
run_tests() {
    echo ""
    echo "🧪 Running JIRA sync tests..."
    cd scripts && ./test_jira_sync.sh && cd ..
}

# Menu system
while true; do
    echo ""
    echo "📋 What would you like to do?"
    echo "   1) Validate JIRA configuration"
    echo "   2) Run JIRA sync (current DRY_RUN=$DRY_RUN)"
    echo "   3) Run test suite"
    echo "   4) Toggle DRY_RUN mode"
    echo "   5) Show current configuration"
    echo "   6) Exit"
    echo ""
    read -p "Select option (1-6): " choice

    case $choice in
        1)
            if [ "$DRY_RUN" = "true" ] || [ ${#missing_vars[@]} -eq 0 ]; then
                run_validation
            else
                echo "❌ Cannot validate: Missing required JIRA credentials"
                echo "💡 Please update $CONFIG_FILE or enable DRY_RUN mode"
            fi
            ;;
        2)
            run_sync
            ;;
        3)
            run_tests
            ;;
        4)
            if [ "$DRY_RUN" = "true" ]; then
                export DRY_RUN="false"
                echo "✅ DRY_RUN mode disabled - will create actual JIRA issues!"
                echo "⚠️  WARNING: Make sure your JIRA credentials are correct!"
            else
                export DRY_RUN="true"
                echo "✅ DRY_RUN mode enabled - will only preview without creating issues"
            fi
            ;;
        5)
            echo ""
            echo "📊 Current Configuration:"
            echo "   JIRA_URL: $JIRA_URL"
            echo "   JIRA_EMAIL: $JIRA_EMAIL"
            echo "   JIRA_PROJECT: $JIRA_PROJECT"
            echo "   GITHUB_REPO_URL: $GITHUB_REPO_URL"
            echo "   GITHUB_BRANCH: $GITHUB_BRANCH"
            echo "   DRY_RUN: $DRY_RUN"
            echo "   Config file: $CONFIG_FILE"
            ;;
        6)
            echo "👋 Goodbye!"
            exit 0
            ;;
        *)
            echo "❌ Invalid option. Please select 1-6."
            ;;
    esac
done