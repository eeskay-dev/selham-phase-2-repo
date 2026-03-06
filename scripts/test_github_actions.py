#!/usr/bin/env python3
"""
Test GitHub Actions Change Detection Logic

This script simulates the change detection logic used in the GitHub Actions workflow
to help debug and test the automation locally.

Usage:
    python3 scripts/test_github_actions.py [--simulate-pr] [--files file1 file2]
"""

import os
import sys
import argparse
from pathlib import Path
import json

def detect_changed_specs(changed_files):
    """Simulate the GitHub Actions change detection logic"""
    print("🔍 Detecting changed spec files...")
    print(f"Changed files: {changed_files}")
    
    # Extract unique spec directories
    spec_dirs = set()
    for file in changed_files:
        if file.startswith('specs/') and ('spec.md' in file or 'tasks.md' in file):
            # Extract spec directory: specs/001-feature-name/
            parts = file.split('/')
            if len(parts) >= 3:
                spec_dir = f"{parts[0]}/{parts[1]}/"
                spec_dirs.add(spec_dir)
        elif file.startswith('jira/') and file.endswith('-draft.yaml'):
            # Extract feature name from draft file: jira/001-feature-name-draft.yaml
            filename = os.path.basename(file)
            if filename.endswith('-draft.yaml'):
                feature_name = filename[:-11]  # Remove '-draft.yaml'
                spec_dir = f"specs/{feature_name}/"
                spec_dirs.add(spec_dir)
    
    spec_dirs = list(spec_dirs)
    
    if spec_dirs:
        print(f"✅ Detected {len(spec_dirs)} spec directories:")
        for dir in spec_dirs:
            print(f"   - {dir}")
        
        # Format as JSON (like GitHub Actions output)
        json_output = json.dumps(spec_dirs)
        print(f"\n📋 GitHub Actions output format:")
        print(f"specs={json_output}")
        print(f"has_changes=true")
        
        return spec_dirs, True
    else:
        print("❌ No spec changes detected")
        print(f"has_changes=false")
        return [], False

def simulate_workflow_matrix(spec_dirs):
    """Simulate the workflow matrix execution"""
    if not spec_dirs:
        print("📋 No matrix jobs would be created")
        return
    
    print(f"\n🔄 Simulating workflow matrix execution...")
    print(f"Matrix strategy: {len(spec_dirs)} jobs (max-parallel: 3)")
    
    for i, spec_dir in enumerate(spec_dirs, 1):
        feature_name = os.path.basename(spec_dir.rstrip('/'))
        print(f"\n📋 Job [{i}/{len(spec_dirs)}]: {feature_name}")
        print(f"   Spec Path: {spec_dir}")
        
        # Check if spec.md exists
        spec_file = Path(spec_dir) / 'spec.md'
        if spec_file.exists():
            print(f"   ✅ spec.md found")
        else:
            print(f"   ❌ spec.md not found")
        
        # Check if draft exists
        draft_file = Path(f"jira/{feature_name}-draft.yaml")
        if draft_file.exists():
            print(f"   📄 Existing draft: {draft_file}")
            print(f"   🔄 Would push existing draft to JIRA")
        else:
            print(f"   📝 No draft found, would generate new one")
            print(f"   🔄 Would generate draft then push to JIRA")

def main():
    parser = argparse.ArgumentParser(description='Test GitHub Actions change detection')
    parser.add_argument('--simulate-pr', action='store_true', help='Simulate PR merge with current git changes')
    parser.add_argument('--files', nargs='*', help='Manually specify changed files')
    
    args = parser.parse_args()
    
    print("🧪 GitHub Actions Change Detection Test")
    print("=" * 50)
    
    # Determine changed files
    if args.files:
        changed_files = args.files
        print(f"📝 Manual file list provided")
    elif args.simulate_pr:
        # Use git to get actual changed files
        import subprocess
        try:
            result = subprocess.run(['git', 'diff', '--name-only', 'HEAD~1', 'HEAD'], 
                                  capture_output=True, text=True, check=True)
            changed_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
            print(f"📝 Git diff detected changes")
        except subprocess.CalledProcessError:
            print("❌ Git diff failed, using empty change list")
            changed_files = []
    else:
        # Default test cases
        changed_files = [
            'specs/001-multi-brand-menu-mgmt/spec.md',
            'specs/002-payment-processing/spec.md', 
            'specs/002-payment-processing/tasks.md',
            'jira/003-user-management-draft.yaml',
            'README.md',  # Should be ignored
            'src/some-code.py'  # Should be ignored
        ]
        print(f"📝 Using default test cases")
    
    # Run detection logic
    spec_dirs, has_changes = detect_changed_specs(changed_files)
    
    # Simulate matrix execution if changes detected
    if has_changes:
        simulate_workflow_matrix(spec_dirs)
        
        print(f"\n🎯 Expected GitHub Actions Behavior:")
        print(f"   - Workflow would trigger: YES")
        print(f"   - Matrix jobs created: {len(spec_dirs)}")
        print(f"   - Features processed: {[os.path.basename(d.rstrip('/')) for d in spec_dirs]}")
        print(f"   - Max parallel execution: 3")
    else:
        print(f"\n🎯 Expected GitHub Actions Behavior:")
        print(f"   - Workflow would trigger: NO")
        print(f"   - Reason: No relevant spec changes detected")
    
    print(f"\n📋 To test specific scenarios:")
    print(f"   python3 scripts/test_github_actions.py --files specs/001-feature/spec.md")
    print(f"   python3 scripts/test_github_actions.py --simulate-pr")

if __name__ == '__main__':
    main()