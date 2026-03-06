#!/usr/bin/env python3
"""
GitHub Actions JIRA Integration Validation

This script helps validate that GitHub Actions is properly configured
for JIRA integration before pushing changes.

Usage:
    python3 scripts/validate_github_setup.py
"""

import os
import sys
from pathlib import Path

def check_workflow_files():
    """Check if workflow files exist and are properly configured"""
    print("🔍 Checking GitHub Actions workflow files...")
    
    workflow_file = Path('.github/workflows/jira-integration.yml')
    if workflow_file.exists():
        print(f"✅ Workflow file found: {workflow_file}")
        
        # Basic content checks
        content = workflow_file.read_text()
        required_elements = [
            'on:',
            'pull_request:',
            'types: [closed]',
            'JIRA_URL: ${{ secrets.JIRA_URL }}',
            'generate-and-push-jira:',
            'scripts/generate_jira_draft.py',
            'scripts/push_jira.py'
        ]
        
        missing = []
        for element in required_elements:
            if element not in content:
                missing.append(element)
        
        if missing:
            print(f"❌ Workflow missing required elements:")
            for item in missing:
                print(f"   - {item}")
            return False
        else:
            print(f"✅ Workflow contains all required elements")
            return True
    else:
        print(f"❌ Workflow file not found: {workflow_file}")
        print(f"   Expected location: .github/workflows/jira-integration.yml")
        return False

def check_script_files():
    """Check if required scripts exist and are executable"""
    print(f"\n🔍 Checking JIRA integration scripts...")
    
    scripts = [
        'scripts/generate_jira_draft.py',
        'scripts/push_jira.py', 
        'scripts/test_github_actions.py'
    ]
    
    all_good = True
    for script in scripts:
        script_path = Path(script)
        if script_path.exists():
            if os.access(script_path, os.X_OK):
                print(f"✅ {script} (executable)")
            else:
                print(f"⚠️  {script} (not executable)")
                print(f"   Run: chmod +x {script}")
        else:
            print(f"❌ {script} (missing)")
            all_good = False
    
    return all_good

def check_dependencies():
    """Check if required dependencies are available"""
    print(f"\n🔍 Checking Python dependencies...")
    
    try:
        import yaml
        print(f"✅ PyYAML available")
    except ImportError:
        print(f"❌ PyYAML not found")
        print(f"   Run: pip install -r requirements.txt")
        return False
    
    try:
        import requests
        print(f"✅ requests available")
    except ImportError:
        print(f"❌ requests not found")
        print(f"   Run: pip install -r requirements.txt") 
        return False
    
    return True

def check_repository_structure():
    """Check if repository has proper structure for JIRA integration"""
    print(f"\n🔍 Checking repository structure...")
    
    required_dirs = [
        'specs',
        'jira',
        '.github/workflows',
        'scripts'
    ]
    
    all_good = True
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"✅ {dir_path}/ directory exists")
        else:
            print(f"❌ {dir_path}/ directory missing")
            all_good = False
    
    # Check for any spec files
    specs_dir = Path('specs')
    if specs_dir.exists():
        spec_files = list(specs_dir.glob('*/spec.md'))
        if spec_files:
            print(f"✅ Found {len(spec_files)} spec file(s)")
            for spec_file in spec_files[:3]:  # Show first 3
                print(f"   - {spec_file}")
            if len(spec_files) > 3:
                print(f"   - ... and {len(spec_files) - 3} more")
        else:
            print(f"⚠️  No spec.md files found in specs/ subdirectories")
    
    return all_good

def show_secret_configuration_guide():
    """Show instructions for configuring GitHub secrets"""
    print(f"\n🔐 GitHub Secrets Configuration Required:")
    print(f"")
    print(f"Go to: Settings → Secrets and variables → Actions")
    print(f"")
    print(f"Add these repository secrets:")
    
    secrets = [
        ('JIRA_URL', 'https://company.atlassian.net', 'Your JIRA instance URL'),
        ('JIRA_EMAIL', 'automation@company.com', 'JIRA user email'),
        ('JIRA_TOKEN', 'ATATxxxxxxxxxxxxx', 'JIRA API token'),
        ('JIRA_PROJECT', 'SPEC', 'JIRA project key')
    ]
    
    print(f"")
    for name, example, description in secrets:
        print(f"   {name}")
        print(f"     Description: {description}")
        print(f"     Example: {example}")
        print(f"")
    
    print(f"📋 Generate API Token at:")
    print(f"   https://id.atlassian.com/manage-profile/security/api-tokens")

def test_local_jira_scripts():
    """Test if JIRA scripts work locally"""
    print(f"\n🧪 Testing local JIRA scripts...")
    
    # Check if we can run the scripts
    try:
        import subprocess
        
        # Test generate_jira_draft.py help
        result = subprocess.run(['python3', 'scripts/generate_jira_draft.py', '--help'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ generate_jira_draft.py script works")
        else:
            print(f"❌ generate_jira_draft.py script error")
            print(f"   {result.stderr.strip()}")
            return False
        
        # Test push_jira.py help  
        result = subprocess.run(['python3', 'scripts/push_jira.py', '--help'],
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ push_jira.py script works")
        else:
            print(f"❌ push_jira.py script error")
            print(f"   {result.stderr.strip()}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing scripts: {e}")
        return False

def main():
    print("🔧 GitHub Actions JIRA Integration Validation")
    print("=" * 55)
    
    checks = [
        ("Repository Structure", check_repository_structure),
        ("Workflow Files", check_workflow_files), 
        ("Script Files", check_script_files),
        ("Dependencies", check_dependencies),
        ("Local Scripts", test_local_jira_scripts)
    ]
    
    results = {}
    for name, check_func in checks:
        results[name] = check_func()
    
    # Summary
    print(f"\n📊 Validation Summary")
    print(f"=" * 25)
    
    passed = sum(results.values())
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {name}")
    
    print(f"\nOverall: {passed}/{total} checks passed")
    
    if passed == total:
        print(f"\n🎉 All validations passed!")
        print(f"✅ Repository is ready for GitHub Actions JIRA integration")
        print(f"")
        print(f"Next steps:")
        print(f"1. Configure GitHub repository secrets (see below)")
        print(f"2. Create a PR with spec changes")  
        print(f"3. Merge PR to trigger automatic JIRA integration")
        
        show_secret_configuration_guide()
    else:
        print(f"\n⚠️  Some validations failed")
        print(f"❌ Fix the issues above before using GitHub Actions")
        print(f"")
        print(f"Common fixes:")
        print(f"- pip install -r requirements.txt")
        print(f"- chmod +x scripts/*.py")
        print(f"- Create missing directories")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)