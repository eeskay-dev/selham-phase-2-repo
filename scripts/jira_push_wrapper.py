#!/usr/bin/env python3
"""
JIRA Push Wrapper
================

Easy wrapper to invoke push_jira.py with JIRA configuration and spec path.
Handles environment setup and parameter validation.

Usage:
    python3 scripts/jira_push_wrapper.py [OPTIONS] <spec_path>
    
Examples:
    python3 scripts/jira_push_wrapper.py specs/001-multi-brand-menu-mgmt/
    python3 scripts/jira_push_wrapper.py --dry-run specs/001-multi-brand-menu-mgmt/
    python3 scripts/jira_push_wrapper.py --github-repo hubino/selham-phase-2 specs/001-multi-brand-menu-mgmt/

Environment Variables (required):
    JIRA_URL - JIRA instance URL (e.g., https://company.atlassian.net)
    JIRA_EMAIL - JIRA user email
    JIRA_TOKEN - JIRA API token
    JIRA_PROJECT - JIRA project key (e.g., SMM)
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

class JiraPushWrapper:
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.repo_root = self.script_dir.parent
        self.push_script = self.script_dir / "push_jira.py"
        
        # Default JIRA configuration - override with environment variables
        self.jira_config = {
            'JIRA_URL': os.environ.get('JIRA_URL', 'https://selham.atlassian.net'),
            'JIRA_EMAIL': os.environ.get('JIRA_EMAIL', ''),
            'JIRA_TOKEN': os.environ.get('JIRA_TOKEN', ''),
            'JIRA_PROJECT': os.environ.get('JIRA_PROJECT', 'SMM')
        }
    
    def print_error(self, message):
        print(f"❌ ERROR: {message}", file=sys.stderr)
    
    def print_success(self, message):
        print(f"✅ {message}")
    
    def print_info(self, message):
        print(f"💡 {message}")
    
    def print_warning(self, message):
        print(f"⚠️  WARNING: {message}")
    
    def validate_environment(self):
        """Validate required environment variables"""
        missing_vars = []
        
        for var_name, var_value in self.jira_config.items():
            if not var_value:
                missing_vars.append(var_name)
        
        if missing_vars:
            self.print_error(f"Missing required environment variables: {', '.join(missing_vars)}")
            self.print_info("Set the following environment variables:")
            print()
            print("export JIRA_URL=https://your-domain.atlassian.net")
            print("export JIRA_EMAIL=your-email@domain.com")
            print("export JIRA_TOKEN=your-api-token")
            print("export JIRA_PROJECT=YOUR-PROJECT-KEY")
            print()
            self.print_info("Or create a .env file in the repository root with these values")
            return False
        
        return True
    
    def validate_spec_path(self, spec_path):
        """Validate and normalize spec path"""
        spec_dir = Path(spec_path)
        
        # Make path absolute if relative
        if not spec_dir.is_absolute():
            spec_dir = self.repo_root / spec_dir
        
        # Check if spec directory exists
        if not spec_dir.exists():
            self.print_error(f"Spec directory does not exist: {spec_dir}")
            return None, None
        
        if not spec_dir.is_dir():
            self.print_error(f"Spec path is not a directory: {spec_dir}")
            return None, None
        
        # Look for spec.md file
        spec_file = spec_dir / "spec.md"
        if not spec_file.exists():
            self.print_error(f"spec.md not found in directory: {spec_dir}")
            return None, None
        
        # Extract feature name from directory
        feature_name = spec_dir.name
        
        # Look for corresponding draft file
        draft_file = self.repo_root / "jira" / f"{feature_name}-draft.yaml"
        
        if not draft_file.exists():
            self.print_warning(f"Draft file not found: {draft_file}")
            self.print_info("You may need to run generate_jira_draft.py first")
            
            # Try to generate draft automatically
            generate_script = self.script_dir / "generate_jira_draft.py"
            if generate_script.exists():
                self.print_info(f"Attempting to generate draft for {spec_path}")
                try:
                    subprocess.run([
                        sys.executable, str(generate_script), str(spec_path)
                    ], check=True, cwd=self.repo_root)
                    self.print_success(f"Generated draft file: {draft_file}")
                except subprocess.CalledProcessError as e:
                    self.print_error(f"Failed to generate draft file: {e}")
                    return None, None
            else:
                self.print_error("generate_jira_draft.py not found")
                return None, None
        
        return str(draft_file), feature_name
    
    def run_push_script(self, draft_file, args):
        """Execute the push_jira.py script with proper environment and arguments"""
        
        # Set up environment
        env = os.environ.copy()
        env.update(self.jira_config)
        
        # Build command
        cmd = [sys.executable, str(self.push_script), draft_file]
        
        # Add optional arguments
        if args.dry_run:
            cmd.append("--dry-run")
        
        if args.verbose:
            cmd.append("--verbose")
        
        # Add GitHub integration parameters
        if args.github_repo:
            cmd.extend(["--github-repo", args.github_repo])
        
        if args.github_pr:
            cmd.extend(["--github-pr", args.github_pr])
        
        if args.github_workflow:
            cmd.extend(["--github-workflow", args.github_workflow])
        
        if args.github_branch:
            cmd.extend(["--github-branch", args.github_branch])
        
        if args.spec_path:
            cmd.extend(["--spec-path", args.spec_path])
        
        # Print configuration summary
        print("🔧 JIRA Push Configuration:")
        print(f"   JIRA URL: {self.jira_config['JIRA_URL']}")
        print(f"   JIRA Project: {self.jira_config['JIRA_PROJECT']}")
        print(f"   Draft File: {draft_file}")
        if args.github_repo:
            print(f"   GitHub Repo: {args.github_repo}")
        if args.dry_run:
            print(f"   Mode: DRY RUN")
        print()
        
        # Execute command
        try:
            result = subprocess.run(cmd, env=env, cwd=self.repo_root, check=False)
            return result.returncode == 0
        except Exception as e:
            self.print_error(f"Failed to execute push script: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(
        description='Wrapper for push_jira.py with environment setup',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('spec_path', help='Path to spec directory (e.g., specs/001-multi-brand-menu-mgmt/)')
    parser.add_argument('--dry-run', action='store_true', help='Test mode - do not create actual JIRA issues')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    # GitHub Integration Parameters
    parser.add_argument('--github-repo', help='GitHub repository name (e.g., owner/repo)')
    parser.add_argument('--github-pr', help='GitHub pull request number')
    parser.add_argument('--github-workflow', help='GitHub workflow run URL')
    parser.add_argument('--github-branch', default='main', help='Git branch name (default: main)')
    
    args = parser.parse_args()
    
    # Initialize wrapper
    wrapper = JiraPushWrapper()
    
    # Validate environment
    if not wrapper.validate_environment():
        sys.exit(1)
    
    # Validate and process spec path
    draft_file, feature_name = wrapper.validate_spec_path(args.spec_path)
    if not draft_file:
        sys.exit(1)
    
    # Set spec_path for GitHub integration
    args.spec_path = f"specs/{feature_name}/"
    
    # Run the push script
    wrapper.print_info(f"Pushing {feature_name} to JIRA...")
    
    success = wrapper.run_push_script(draft_file, args)
    
    if success:
        wrapper.print_success("JIRA push completed successfully!")
    else:
        wrapper.print_error("JIRA push failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()