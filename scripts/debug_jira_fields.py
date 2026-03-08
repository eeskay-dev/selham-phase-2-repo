#!/usr/bin/env python3
"""Debug script to discover all JIRA fields"""

import os
import sys
import requests
import json
from requests.auth import HTTPBasicAuth

def debug_jira_fields():
    """Debug JIRA fields to help configure epic linking and custom fields"""
    
    # Get credentials from environment
    jira_email = os.getenv('JIRA_EMAIL')
    jira_token = os.getenv('JIRA_TOKEN')
    jira_url = "https://selham.atlassian.net"
    jira_project = "SMM"
    
    if not jira_email or not jira_token:
        print("❌ Missing JIRA credentials. Set JIRA_EMAIL and JIRA_TOKEN environment variables.")
        return
    
    session = requests.Session()
    session.auth = HTTPBasicAuth(jira_email, jira_token)
    
    try:
        print(f"🔍 Fetching all fields from {jira_url}...")
        response = session.get(f"{jira_url}/rest/api/2/field")
        response.raise_for_status()
        fields = response.json()
        
        print(f"\n📋 Found {len(fields)} fields in JIRA:")
        print("=" * 80)
        
        # Group fields by type
        custom_fields = []
        system_fields = []
        epic_fields = []
        story_fields = []
        
        for field in fields:
            field_name = field.get('name', '')
            field_id = field.get('id', '')
            field_type = field.get('schema', {}).get('type', 'unknown')
            is_custom = field.get('custom', False)
            
            field_info = {
                'name': field_name,
                'id': field_id,
                'type': field_type,
                'custom': is_custom
            }
            
            if is_custom:
                custom_fields.append(field_info)
            else:
                system_fields.append(field_info)
            
            # Look for epic-related fields
            if any(word in field_name.lower() for word in ['epic', 'parent', 'hierarchy']):
                epic_fields.append(field_info)
            
            # Look for story-related fields
            if any(word in field_name.lower() for word in ['story', 'point', 'criteria', 'sprint']):
                story_fields.append(field_info)
        
        # Print epic-related fields
        if epic_fields:
            print(f"\n🎯 Epic/Parent-related fields ({len(epic_fields)}):")
            for field in epic_fields:
                print(f"   {field['name']} ({field['id']}) - {field['type']} {'[CUSTOM]' if field['custom'] else '[SYSTEM]'}")
        
        # Print story-related fields  
        if story_fields:
            print(f"\n📝 Story/Sprint-related fields ({len(story_fields)}):")
            for field in story_fields:
                print(f"   {field['name']} ({field['id']}) - {field['type']} {'[CUSTOM]' if field['custom'] else '[SYSTEM]'}")
        
        # Show first 20 custom fields
        print(f"\n🔧 Custom fields (showing first 20 of {len(custom_fields)}):")
        for field in custom_fields[:20]:
            print(f"   {field['name']} ({field['id']}) - {field['type']}")
        
        print(f"\n💡 System fields (showing first 20 of {len(system_fields)}):")  
        for field in system_fields[:20]:
            print(f"   {field['name']} ({field['id']}) - {field['type']}")
        
        # Try to get project-specific issue create metadata
        print(f"\n🔍 Getting project-specific field metadata...")
        try:
            create_meta_response = session.get(f"{jira_url}/rest/api/2/issue/createmeta", params={
                'projectKeys': jira_project,
                'expand': 'projects.issuetypes.fields'
            })
            create_meta_response.raise_for_status()
            create_meta = create_meta_response.json()
            
            if create_meta.get('projects'):
                project = create_meta['projects'][0]
                print(f"   Project: {project['name']} ({project['key']})")
                
                for issue_type in project.get('issuetypes', []):
                    print(f"\n   📋 {issue_type['name']} issue type fields:")
                    for field_id, field_info in issue_type.get('fields', {}).items():
                        field_name = field_info.get('name', 'Unknown')
                        required = field_info.get('required', False)
                        print(f"      {field_name} ({field_id}) {'[REQUIRED]' if required else ''}")
                        
                        # Look for epic link specifically
                        if 'epic' in field_name.lower() or 'parent' in field_name.lower():
                            print(f"         🎯 POTENTIAL EPIC LINK FIELD!")
        
        except Exception as e:
            print(f"   ⚠️  Could not fetch create metadata: {e}")
            
    except Exception as e:
        print(f"❌ Error fetching fields: {e}")

if __name__ == "__main__":
    debug_jira_fields()