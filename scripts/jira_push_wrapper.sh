#!/bin/bash
#
# JIRA Push Wrapper Script
# ========================
#
# Easy wrapper to invoke push_jira.py with JIRA configuration and spec path.
# Handles environment setup and parameter validation.
#
# Usage:
#     ./scripts/jira_push_wrapper.sh [OPTIONS] <spec_path>
#     
# Examples:
#     ./scripts/jira_push_wrapper.sh specs/001-multi-brand-menu-mgmt/
#     ./scripts/jira_push_wrapper.sh --dry-run specs/001-multi-brand-menu-mgmt/
#     ./scripts/jira_push_wrapper.sh --github-repo hubino/selham-phase-2 specs/001-multi-brand-menu-mgmt/
#
# Environment Variables (required):
#     JIRA_URL - JIRA instance URL (e.g., https://company.atlassian.net)
#     JIRA_EMAIL - JIRA user email  
#     JIRA_TOKEN - JIRA API token
#     JIRA_PROJECT - JIRA project key (e.g., SMM)
#

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Default values
DRY_RUN=false
VERBOSE=false
GITHUB_REPO=""
GITHUB_PR=""
GITHUB_WORKFLOW=""
GITHUB_BRANCH="main"

# JIRA Configuration - override with environment variables
: ${JIRA_URL:="https://selham.atlassian.net"}
: ${JIRA_EMAIL:=""}
: ${JIRA_TOKEN:=""}
: ${JIRA_PROJECT:="SMM"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_error() {
    echo -e "${RED}❌ ERROR: $1${NC}" >&2
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Function to show usage
show_usage() {
    cat << EOF
JIRA Push Wrapper - Easy SPEC-KIT to JIRA Integration

Usage: $0 [OPTIONS] <spec_path>

Arguments:
    spec_path           Path to specification directory (e.g., specs/001-multi-brand-menu-mgmt/)

Options:
    --dry-run          Test mode - do not create actual JIRA issues
    --verbose          Verbose output
    --github-repo      GitHub repository (e.g., owner/repo)
    --github-pr        GitHub pull request number
    --github-workflow  GitHub workflow run URL
    --github-branch    Git branch name (default: main)
    --help            Show this help message

Environment Variables (required):
    JIRA_URL          JIRA instance URL (default: https://selham.atlassian.net)
    JIRA_EMAIL        JIRA user email
    JIRA_TOKEN        JIRA API token
    JIRA_PROJECT      JIRA project key (default: SPEC)

Examples:
    # Basic usage
    $0 specs/001-multi-brand-menu-mgmt/
    
    # Dry run test
    $0 --dry-run specs/001-multi-brand-menu-mgmt/
    
    # With GitHub context
    $0 --github-repo hubino/selham-phase-2 --github-pr 123 specs/001-multi-brand-menu-mgmt/
    
    # Set JIRA variables inline
    JIRA_EMAIL=user@domain.com JIRA_TOKEN=xxx $0 specs/001-multi-brand-menu-mgmt/

EOF
}

# Function to validate JIRA configuration
validate_jira_config() {
    local missing=()
    
    if [[ -z "$JIRA_URL" ]]; then
        missing+=("JIRA_URL")
    fi
    if [[ -z "$JIRA_EMAIL" ]]; then
        missing+=("JIRA_EMAIL")
    fi
    if [[ -z "$JIRA_TOKEN" ]]; then
        missing+=("JIRA_TOKEN")
    fi
    if [[ -z "$JIRA_PROJECT" ]]; then
        missing+=("JIRA_PROJECT")
    fi
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        print_error "Missing required JIRA environment variables: ${missing[*]}"
        echo
        echo "Set them before running:"
        echo "  export JIRA_URL=https://your-domain.atlassian.net"
        echo "  export JIRA_EMAIL=your-email@domain.com" 
        echo "  export JIRA_TOKEN=your-api-token"
        echo "  export JIRA_PROJECT=YOUR-PROJECT-KEY"
        echo
        echo "Or use inline variables:"
        echo "  JIRA_EMAIL=user@domain.com JIRA_TOKEN=xxx $0 $*"
        return 1
    fi
    
    return 0
}

# Function to validate spec path and find draft file
validate_spec_path() {
    local spec_path="$1"
    
    # Remove trailing slash
    spec_path="${spec_path%/}"
    
    # Check if spec path exists
    if [[ ! -d "$spec_path" ]]; then
        print_error "Spec directory does not exist: $spec_path"
        return 1
    fi
    
    # Extract feature name from path
    local feature_name
    feature_name="$(basename "$spec_path")"
    
    # Look for draft file
    local draft_file="jira/${feature_name}-draft.yaml"
    
    if [[ ! -f "$draft_file" ]]; then
        print_error "Draft file not found: $draft_file"
        print_info "Generate draft first with: python3 scripts/generate_jira_draft.py $spec_path"
        return 1
    fi
    
    echo "$draft_file"
    return 0
}

# Function to mask sensitive values for display
mask_credential() {
    local cred="$1"
    if [[ ${#cred} -le 8 ]]; then
        echo "***"
    else
        echo "${cred:0:3}***${cred: -3}"
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --github-repo)
            GITHUB_REPO="$2"
            shift 2
            ;;
        --github-pr)
            GITHUB_PR="$2"
            shift 2
            ;;
        --github-workflow)
            GITHUB_WORKFLOW="$2"
            shift 2
            ;;
        --github-branch)
            GITHUB_BRANCH="$2"
            shift 2
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        -*)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
        *)
            SPEC_PATH="$1"
            shift
            ;;
    esac
done

# Validate required arguments
if [[ -z "${SPEC_PATH:-}" ]]; then
    print_error "Spec path is required"
    show_usage
    exit 1
fi

# Change to repository root
cd "$REPO_ROOT"

print_info "JIRA Push Wrapper - SPEC-KIT Integration"
echo "=========================================="

# Validate JIRA configuration
if ! validate_jira_config; then
    exit 1
fi

# Show configuration (with masked credentials)
print_info "JIRA Configuration:"
echo "  URL: $JIRA_URL"
echo "  Project: $JIRA_PROJECT" 
echo "  Email: $(mask_credential "$JIRA_EMAIL")"
echo "  Token: $(mask_credential "$JIRA_TOKEN")"
echo

# Validate spec path and get draft file
print_info "Validating spec path: $SPEC_PATH"
if ! DRAFT_FILE=$(validate_spec_path "$SPEC_PATH"); then
    exit 1
fi

print_success "Found draft file: $DRAFT_FILE"

# Build push_jira.py command
PUSH_CMD="python3 scripts/push_jira.py \"$DRAFT_FILE\""

if [[ "$DRY_RUN" == "true" ]]; then
    PUSH_CMD="$PUSH_CMD --dry-run"
    print_warning "DRY RUN MODE: No actual JIRA issues will be created"
fi

if [[ "$VERBOSE" == "true" ]]; then
    PUSH_CMD="$PUSH_CMD --verbose"
fi

# Add GitHub context if provided
if [[ -n "$GITHUB_REPO" ]]; then
    PUSH_CMD="$PUSH_CMD --github-repo \"$GITHUB_REPO\""
fi

if [[ -n "$GITHUB_PR" ]]; then
    PUSH_CMD="$PUSH_CMD --github-pr \"$GITHUB_PR\""
fi

if [[ -n "$GITHUB_WORKFLOW" ]]; then
    PUSH_CMD="$PUSH_CMD --github-workflow \"$GITHUB_WORKFLOW\""
fi

if [[ -n "$GITHUB_BRANCH" ]]; then
    PUSH_CMD="$PUSH_CMD --github-branch \"$GITHUB_BRANCH\""
fi

# Add spec path for GitHub integration
PUSH_CMD="$PUSH_CMD --spec-path \"$SPEC_PATH/\""

# Show GitHub context if any
if [[ -n "$GITHUB_REPO$GITHUB_PR$GITHUB_WORKFLOW" ]]; then
    print_info "GitHub Integration:"
    [[ -n "$GITHUB_REPO" ]] && echo "  Repository: $GITHUB_REPO"
    [[ -n "$GITHUB_BRANCH" ]] && echo "  Branch: $GITHUB_BRANCH"
    [[ -n "$GITHUB_PR" ]] && echo "  Pull Request: #$GITHUB_PR"
    [[ -n "$GITHUB_WORKFLOW" ]] && echo "  Workflow: $GITHUB_WORKFLOW"
    echo
fi

# Export JIRA environment variables
export JIRA_URL JIRA_EMAIL JIRA_TOKEN JIRA_PROJECT

print_info "Executing push_jira.py..."
if [[ "$VERBOSE" == "true" ]]; then
    echo "Command: $PUSH_CMD"
    echo
fi

# Execute the push command
eval "$PUSH_CMD"
exit_code=$?

echo
if [[ $exit_code -eq 0 ]]; then
    print_success "JIRA push completed successfully!"
    if [[ "$DRY_RUN" != "true" ]]; then
        print_info "Check JIRA: $JIRA_URL"
    fi
else
    print_error "JIRA push failed with exit code: $exit_code"
    echo
    print_info "Troubleshooting:"
    echo "  1. Check JIRA credentials and permissions"
    echo "  2. Run with --dry-run to test configuration"
    echo "  3. Use --verbose for detailed output"
    echo "  4. See: troubleshooting/speckit-jira-integeration/"
fi

exit $exit_code