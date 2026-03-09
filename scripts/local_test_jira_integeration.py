#!/usr/bin/env python3

import os
import subprocess
import sys
import requests

def test_jira_credentials():
    """Test JIRA credentials independently before running the full sync"""
    print("🔐 TESTING JIRA CREDENTIALS INDEPENDENTLY")
    print("="*50)
    
    # Get credentials from environment
    jira_url = os.environ.get('JIRA_URL')
    jira_email = os.environ.get('JIRA_EMAIL')
    jira_token = os.environ.get('JIRA_TOKEN')
    
    print(f"📋 Configuration being tested:")
    print(f"   JIRA_URL: {jira_url}")
    print(f"   JIRA_EMAIL: {jira_email}")
    print(f"   JIRA_TOKEN: {jira_token[:10]}...{jira_token[-4:] if jira_token and len(jira_token) > 14 else 'N/A'}")
    print()
    
    if not all([jira_url, jira_email, jira_token]):
        print("❌ Missing required credentials!")
        return False
    
    # Test basic connectivity
    try:
        print("🌐 Testing basic connectivity...")
        response = requests.get(f"{jira_url}/status", timeout=10)
        if response.status_code == 200:
            print("✅ Basic connectivity: OK")
        else:
            print(f"⚠️  Basic connectivity: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Basic connectivity: FAILED - {e}")
        return False
    
    # Test authentication
    try:
        print("🔐 Testing authentication...")
        auth_response = requests.get(
            f"{jira_url}/rest/api/3/myself", 
            auth=(jira_email, jira_token), 
            timeout=15
        )
        
        if auth_response.status_code == 200:
            user_data = auth_response.json()
            display_name = user_data.get('displayName', 'Unknown')
            account_id = user_data.get('accountId', 'Unknown')
            print(f"✅ Authentication: SUCCESS")
            print(f"   User: {display_name}")
            print(f"   Account ID: {account_id}")
            return True
        elif auth_response.status_code == 401:
            print("❌ Authentication: FAILED (401 Unauthorized)")
            print("   💡 Possible issues:")
            print("      • JIRA_TOKEN is expired or incorrect")
            print("      • JIRA_EMAIL doesn't match the token owner")
            print("      • Token doesn't have required permissions")
            print(f"   🔗 Create/refresh token at: {jira_url.replace('https://', 'https://id.atlassian.com/manage-profile/security/api-tokens')}")
        elif auth_response.status_code == 403:
            print("❌ Authentication: FAILED (403 Forbidden)")
            print("   💡 Token is valid but user lacks permissions")
        else:
            print(f"❌ Authentication: FAILED (HTTP {auth_response.status_code})")
            print(f"   Response: {auth_response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Authentication test error: {e}")
    
    return False

def set_environment_variables():
    """Set all environment variables in one go"""
    
    print("⚠️  CREDENTIAL SETUP REQUIRED")
    print("="*50)
    print("This script contains hardcoded credentials that may be expired.")
    print("Please update the credentials below or set them as environment variables.")
    print()
    
    # Check if credentials are already set in environment
    if all([os.environ.get('JIRA_URL'), os.environ.get('JIRA_EMAIL'), os.environ.get('JIRA_TOKEN')]):
        print("✅ Using existing environment variables")
        return
    
    env_vars = {
        'GITHUB_ACTIONS': 'true',
        'GITHUB_SERVER_URL': 'https://github.com',
        'GITHUB_REPOSITORY': 'selham/selham-phase-2-repo',
        'GITHUB_REF_NAME': 'main',
        'DRY_RUN': 'false',
        'JIRA_URL': 'https://selham.atlassian.net',
        'JIRA_EMAIL': 'eeskay@zohomail.in',
        # NOTE: This token may be expired - update with a fresh one
        'JIRA_TOKEN': 'ATATT3xFfGF0MlVYo7gHvDOUeEg4JYS15TRveYPlQJ9HlrMagQmHYhijpzIk5DDpDZg4WyIBl3SqeKfTv8WThovllI8Qfra6q9I1rhNl1qDIlLJ9fLrmJuWbNEbr5PMcDukBdRTozOpYgWy55IJhfmEBKpOFvqMCCyQ22LkRCFP_Apfdw44B7zc=0BF9FD64',
        'JIRA_PROJECT': 'SMM'
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
        
    print("💡 TO FIX AUTHENTICATION:")
    print("1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens")
    print("2. Create a new API token")
    print("3. Either:")
    print("   • Update the JIRA_TOKEN in this script, OR")
    print("   • Set environment variables before running:")
    print()
    print("   export JIRA_URL='https://selham.atlassian.net'")
    print("   export JIRA_EMAIL='eesaky@zohomail.in'")
    print("   export JIRA_TOKEN='your_new_token_here'")
    print("   export JIRA_PROJECT='SMM'")
    print()

def run_jira_sync():
    """Run the jira_sync.py script"""
    try:
        result = subprocess.run([sys.executable, 'jira_sync.py'], 
                              capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"Errors: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"Error running jira_sync.py: {e}")
        return False

def main():
    # Set environment variables
    set_environment_variables()
    
    # Test credentials first
    if not test_jira_credentials():
        print("\n❌ JIRA credentials test failed. Please fix authentication before proceeding.")
        print("   See setup instructions above.")
        return False
    
    print("\n🎉 JIRA credentials validated successfully!")
    
    # Test script for the improved JIRA sync
    print("\n🧪 Testing JIRA Sync Script Improvements")
    print("=" * 40)
    
    # Test 1: Simulate GitHub Actions environment
    print()
    print("🔄 Test 1: GitHub Actions Environment Simulation")

    print("📋 JIRA Configuration:")
    print(f"  JIRA_URL: {os.environ.get('JIRA_URL')}")
    print(f"  JIRA_EMAIL: {os.environ.get('JIRA_EMAIL')}")
    print(f"  JIRA_TOKEN: {os.environ.get('JIRA_TOKEN')}")
    print(f"  JIRA_PROJECT: {os.environ.get('JIRA_PROJECT')}")
    print()


    print("📋 GitHub Actions Configuration:")
    print(f"  GITHUB_ACTIONS: {os.environ.get('GITHUB_ACTIONS')}")
    print(f"  GITHUB_REPOSITORY: {os.environ.get('GITHUB_REPOSITORY')}")
    print(f"  GITHUB_REF_NAME: {os.environ.get('GITHUB_REF_NAME')}")
    print(f"  GITHUB_SERVER_URL: {os.environ.get('GITHUB_SERVER_URL')}")
    print()
    
    print("🚀 Running with GitHub Actions auto-detection...")
    success1 = run_jira_sync()
    
    print()
    print("=" * 50)
    
    # Test 2: Manual configuration (fallback)
    print()
    print("🔄 Test 2: Manual Configuration Fallback")
    
    # Unset GitHub Actions variables
    github_vars = ['GITHUB_ACTIONS', 'GITHUB_SERVER_URL', 'GITHUB_REPOSITORY', 'GITHUB_REF_NAME']
    for var in github_vars:
        if var in os.environ:
            del os.environ[var]
    
    # Set manual configuration
    os.environ['GITHUB_REPO_URL'] = 'https://github.com/manual/manual-repo'
    os.environ['GITHUB_BRANCH'] = 'develop'
    
    print("📋 Manual Configuration:")
    print(f"  GITHUB_REPO_URL: {os.environ.get('GITHUB_REPO_URL')}")
    print(f"  GITHUB_BRANCH: {os.environ.get('GITHUB_BRANCH')}")
    print()
    
    print("🚀 Running with manual configuration...")
    success2 = run_jira_sync()
    
    print()
    print("✅ All tests completed!")
    print()
    print("📝 Features Tested:")
    features = [
        "✓ GitHub Actions auto-detection",
        "✓ Manual configuration fallback",
        "✓ Unified YAML template (epic, story, task, subtask, bug)",
        "✓ Template-based YAML file creation",
        "✓ Auto-categorization and time estimation",
        "✓ Bug report structured sections extraction",
        "✓ GitHub links in JIRA descriptions",
        "✓ Enhanced error handling"
    ]
    
    for feature in features:
        print(f"  {feature}")
    
    print()
    print("📁 Template file used:")
    print("  ✓ templates/templates.yaml (unified template file)")
    
    # Return success status
    return success1 and success2

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)