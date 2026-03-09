#!/usr/bin/env python3
"""
JIRA Configuration Validator
Helps validate JIRA project setup and suggest correct issue type mappings
"""
import os
import sys
import requests
from pathlib import Path

def check_jira_connection():
    """Check JIRA connection and available issue types"""
    
    # Get configuration
    jira_url = os.environ.get("JIRA_URL", "").rstrip("/")
    email = os.environ.get("JIRA_EMAIL")
    token = os.environ.get("JIRA_TOKEN") 
    project = os.environ.get("JIRA_PROJECT")
    
    # Validate required fields
    missing = []
    if not jira_url:
        missing.append("JIRA_URL")
    if not email:
        missing.append("JIRA_EMAIL")
    if not token:
        missing.append("JIRA_TOKEN")
    if not project:
        missing.append("JIRA_PROJECT")
    
    if missing:
        print("❌ Missing required environment variables:")
        for var in missing:
            print(f"   - {var}")
        print("\n💡 Set these environment variables and try again")
        return False
    
    print(f"🔍 Checking JIRA configuration...")
    print(f"   URL: {jira_url}")
    print(f"   Project: {project}")
    print(f"   Email: {email}")
    
    # Test connection
    try:
        auth = (email, token)
        
        # Test basic connection
        response = requests.get(
            f"{jira_url}/rest/api/3/myself",
            auth=auth,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if not response.ok:
            print(f"❌ JIRA connection failed: HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
        
        user_data = response.json()
        print(f"✅ Connected to JIRA as: {user_data.get('displayName', 'Unknown')}")
        
        # Get available issue types for project
        response = requests.get(
            f"{jira_url}/rest/api/3/issue/createmeta?projectKeys={project}&expand=projects.issuetypes",
            auth=auth,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if not response.ok:
            print(f"⚠️  Could not fetch project issue types: HTTP {response.status_code}")
            return True  # Connection works, but can't get issue types
        
        data = response.json()
        
        if not data.get("projects"):
            print(f"❌ Project '{project}' not found or not accessible")
            return False
        
        project_data = data["projects"][0]
        issue_types = [it["name"] for it in project_data.get("issuetypes", [])]
        
        print(f"\n📋 Available issue types in project '{project}':")
        for i, issue_type in enumerate(sorted(issue_types), 1):
            print(f"   {i}. {issue_type}")
        
        # Suggest mappings
        print(f"\n💡 Suggested environment variable configuration:")
        
        # Epic mapping
        if "Epic" in issue_types:
            print(f'   export ISSUE_TYPE_EPIC="Epic"')
        else:
            epic_alternatives = [t for t in issue_types if 'epic' in t.lower()]
            if epic_alternatives:
                print(f'   export ISSUE_TYPE_EPIC="{epic_alternatives[0]}"')
            else:
                print(f'   export ISSUE_TYPE_EPIC="Task"  # No Epic type found, using Task')
        
        # Story mapping
        if "Story" in issue_types:
            print(f'   export ISSUE_TYPE_STORY="Story"')
        else:
            story_alternatives = [t for t in issue_types if 'story' in t.lower()]
            if story_alternatives:
                print(f'   export ISSUE_TYPE_STORY="{story_alternatives[0]}"')
            elif "Task" in issue_types:
                print(f'   export ISSUE_TYPE_STORY="Task"  # No Story type found, using Task')
            else:
                print(f'   export ISSUE_TYPE_STORY="{issue_types[0]}"  # Using first available type')
        
        # Task mapping
        if "Sub-task" in issue_types:
            print(f'   export ISSUE_TYPE_TASK="Sub-task"')
        elif "Task" in issue_types:
            print(f'   export ISSUE_TYPE_TASK="Task"')
        else:
            task_alternatives = [t for t in issue_types if 'task' in t.lower()]
            if task_alternatives:
                print(f'   export ISSUE_TYPE_TASK="{task_alternatives[0]}"')
            else:
                print(f'   export ISSUE_TYPE_TASK="{issue_types[0]}"  # Using first available type')
        
        # Bug mapping
        if "Bug" in issue_types:
            print(f'   export ISSUE_TYPE_BUG="Bug"')
        else:
            bug_alternatives = [t for t in issue_types if any(x in t.lower() for x in ['bug', 'defect', 'issue'])]
            if bug_alternatives:
                print(f'   export ISSUE_TYPE_BUG="{bug_alternatives[0]}"')
            elif "Task" in issue_types:
                print(f'   export ISSUE_TYPE_BUG="Task"  # No Bug type found, using Task')
            else:
                print(f'   export ISSUE_TYPE_BUG="{issue_types[0]}"  # Using first available type')
        
        print(f"\n🚀 Copy and paste the export commands above, then run the JIRA sync script!")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("🔧 JIRA Configuration Validator")
    print("=" * 40)
    
    success = check_jira_connection()
    
    if success:
        print("\n✅ Validation complete!")
    else:
        print("\n❌ Validation failed!")
        sys.exit(1)