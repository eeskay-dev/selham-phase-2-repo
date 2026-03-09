#!/usr/bin/env python3
"""
JIRA Field Discovery Script
Discovers available fields for your JIRA project and issue types
"""

import os
import requests
import json
import sys
from pathlib import Path

# JIRA Configuration
JIRA_URL = os.environ.get("JIRA_URL", "").rstrip("/")
EMAIL = os.environ.get("JIRA_EMAIL")
TOKEN = os.environ.get("JIRA_TOKEN")
PROJECT = os.environ.get("JIRA_PROJECT")

def discover_project_fields():
    """Discover all available fields for the project"""
    
    if not all([JIRA_URL, EMAIL, TOKEN, PROJECT]):
        print("❌ ERROR: Missing JIRA configuration")
        print("   Required: JIRA_URL, JIRA_EMAIL, JIRA_TOKEN, JIRA_PROJECT")
        return False
    
    auth = (EMAIL, TOKEN)
    
    print(f"🔍 Discovering fields for project: {PROJECT}")
    print(f"   JIRA URL: {JIRA_URL}")
    print("=" * 60)
    
    # Get issue types first
    issue_types_url = f"{JIRA_URL}/rest/api/3/issue/createmeta?projectKeys={PROJECT}"
    
    try:
        response = requests.get(issue_types_url, auth=auth)
        if not response.ok:
            print(f"❌ ERROR: HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
        
        data = response.json()
        if not data.get("projects"):
            print("❌ ERROR: No projects found or no permission")
            return False
        
        project_data = data["projects"][0]
        issue_types = project_data.get("issuetypes", [])
        
        print(f"📋 Available Issue Types ({len(issue_types)}):") 
        for it in issue_types:
            print(f"   - {it['name']} (ID: {it['id']})")
        
        print("\\n" + "=" * 60)
        
        # Get detailed field info for each issue type
        all_fields = set()
        
        for issue_type in issue_types:
            type_name = issue_type['name']
            print(f"\\n🔍 Fields for {type_name}:")
            
            fields_url = f"{JIRA_URL}/rest/api/3/issue/createmeta?projectKeys={PROJECT}&issuetypeNames={type_name}&expand=projects.issuetypes.fields"
            
            field_response = requests.get(fields_url, auth=auth)
            if field_response.ok:
                field_data = field_response.json()
                if (field_data.get("projects") and 
                    len(field_data["projects"]) > 0 and
                    field_data["projects"][0].get("issuetypes") and
                    len(field_data["projects"][0]["issuetypes"]) > 0):
                    
                    fields = field_data["projects"][0]["issuetypes"][0].get("fields", {})
                    
                    standard_fields = []
                    custom_fields = []
                    
                    for field_id, field_info in fields.items():
                        field_name = field_info.get("name", "Unknown")
                        field_required = field_info.get("required", False)
                        
                        all_fields.add((field_id, field_name, field_required))
                        
                        if field_id.startswith("customfield_"):
                            custom_fields.append((field_id, field_name, field_required))
                        else:
                            standard_fields.append((field_id, field_name, field_required))
                    
                    print(f"   📌 Standard Fields ({len(standard_fields)}):")
                    for field_id, name, required in sorted(standard_fields):
                        req_marker = " [REQUIRED]" if required else ""
                        print(f"      {field_id}: {name}{req_marker}")
                    
                    print(f"   🔧 Custom Fields ({len(custom_fields)}):")
                    for field_id, name, required in sorted(custom_fields):
                        req_marker = " [REQUIRED]" if required else ""
                        print(f"      {field_id}: {name}{req_marker}")
            else:
                print(f"   ❌ Could not fetch fields: HTTP {field_response.status_code}")
        
        # Generate summary
        print("\\n" + "=" * 60)
        print("📊 SUMMARY")
        print("=" * 60)
        
        all_standard = [f for f in all_fields if not f[0].startswith("customfield_")]
        all_custom = [f for f in all_fields if f[0].startswith("customfield_")]
        
        print(f"Total unique fields: {len(all_fields)}")
        print(f"Standard fields: {len(all_standard)}")
        print(f"Custom fields: {len(all_custom)}")
        
        # Generate template suggestions
        print(f"\\n🛠️  RECOMMENDED FIELD MAPPINGS:")
        print(f"Add these to your templates.json field_mappings section:")
        print(f"{{")
        
        common_mappings = {
            "story_points": ["Story Points", "Story Point", "Points"],
            "epic_name": ["Epic Name", "Epic"],
            "epic_link": ["Epic Link", "Epic"],
            "sprint": ["Sprint", "Sprints"]
        }
        
        for mapping_key, possible_names in common_mappings.items():
            found_field = None
            for field_id, field_name, _ in all_custom:
                if any(pn.lower() in field_name.lower() for pn in possible_names):
                    found_field = field_id
                    break
            
            if found_field:
                print(f'  "{mapping_key}": "{found_field}",  # {field_name}')
            else:
                print(f'  "{mapping_key}": "customfield_XXXXX",  # Not found - check manually')
        
        print(f"}}")
        
        print(f"\\n💡 TIPS:")
        print(f"   - Copy the field mappings above to templates.json")
        print(f"   - Remove custom_fields from templates if you don't need them")
        print(f"   - Test with DRY_RUN=true first")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    print("🔍 JIRA FIELD DISCOVERY TOOL")
    print("=" * 60)
    
    if discover_project_fields():
        print("\\n✅ Field discovery completed successfully!")
    else:
        print("\\n❌ Field discovery failed!")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())