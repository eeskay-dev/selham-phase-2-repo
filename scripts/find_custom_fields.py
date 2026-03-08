#!/usr/bin/env python3
"""
Find Custom Fields in JIRA - Comprehensive field discovery

This script will help find the exact field IDs for Story Points and Acceptance Criteria
in your JIRA instance by searching through all available fields.
"""

import os
import sys
import requests
import json
from pathlib import Path

def find_custom_fields():
    # Load JIRA configuration
    jira_url = os.getenv('JIRA_URL')
    jira_email = os.getenv('JIRA_EMAIL') 
    jira_token = os.getenv('JIRA_TOKEN')
    jira_project = os.getenv('JIRA_PROJECT')
    
    if not all([jira_url, jira_email, jira_token, jira_project]):
        print("❌ Missing JIRA environment variables")
        print("Required: JIRA_URL, JIRA_EMAIL, JIRA_TOKEN, JIRA_PROJECT")
        sys.exit(1)
        
    session = requests.Session()
    session.auth = (jira_email, jira_token)
    session.headers.update({
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    })
    
    print(f"🔍 Searching for custom fields in {jira_project} project...")
    
    try:
        # Get all fields
        response = session.get(f"{jira_url}/rest/api/2/field")
        response.raise_for_status()
        all_fields = response.json()
        
        print(f"\n📊 Found {len(all_fields)} total fields")
        
        # Look for Story Points and Acceptance Criteria
        story_points_candidates = []
        acceptance_criteria_candidates = []
        other_custom_fields = []
        
        for field in all_fields:
            field_id = field.get('id', '')
            field_name = field.get('name', '')
            field_type = field.get('schema', {}).get('type', 'unknown')
            
            if field_id.startswith('customfield_'):
                field_name_lower = field_name.lower()
                
                # Look for Story Points variations
                if any(term in field_name_lower for term in ['story point', 'storypoint', 'story_point', 'points', 'estimate']):
                    story_points_candidates.append({
                        'id': field_id,
                        'name': field_name,
                        'type': field_type
                    })
                
                # Look for Acceptance Criteria variations  
                elif any(term in field_name_lower for term in ['acceptance', 'criteria', 'ac ', 'definition of done', 'dod']):
                    acceptance_criteria_candidates.append({
                        'id': field_id,
                        'name': field_name,
                        'type': field_type
                    })
                
                # Track other potentially useful fields
                elif any(term in field_name_lower for term in ['epic', 'parent', 'business', 'value', 'priority', 'team', 'sprint']):
                    other_custom_fields.append({
                        'id': field_id,
                        'name': field_name,
                        'type': field_type
                    })
        
        # Print results
        print(f"\n🎯 STORY POINTS CANDIDATES:")
        if story_points_candidates:
            for field in story_points_candidates:
                print(f"   • {field['id']} - {field['name']} (Type: {field['type']})")
        else:
            print("   ❌ No Story Points fields found")
        
        print(f"\n📝 ACCEPTANCE CRITERIA CANDIDATES:")
        if acceptance_criteria_candidates:
            for field in acceptance_criteria_candidates:
                print(f"   • {field['id']} - {field['name']} (Type: {field['type']})")
        else:
            print("   ❌ No Acceptance Criteria fields found")
            
        print(f"\n🔧 OTHER USEFUL CUSTOM FIELDS:")
        for field in other_custom_fields:
            print(f"   • {field['id']} - {field['name']} (Type: {field['type']})")
        
        # Get create metadata for the specific project to see what fields are actually available
        print(f"\n🔍 Checking project-specific field availability for {jira_project}...")
        
        try:
            create_meta_response = session.get(f"{jira_url}/rest/api/2/issue/createmeta", params={
                'projectKeys': jira_project,
                'expand': 'projects.issuetypes.fields'
            })
            create_meta_response.raise_for_status()
            create_meta = create_meta_response.json()
            
            project_fields = {}
            if create_meta.get('projects'):
                project = create_meta['projects'][0]
                
                for issue_type in project.get('issuetypes', []):
                    type_name = issue_type.get('name')
                    fields = issue_type.get('fields', {})
                    
                    print(f"\n📋 {type_name} Issue Type Fields:")
                    
                    for field_id, field_info in fields.items():
                        if field_id.startswith('customfield_'):
                            field_name = field_info.get('name', '')
                            required = field_info.get('required', False)
                            field_type = field_info.get('schema', {}).get('type', 'unknown')
                            
                            field_name_lower = field_name.lower()
                            
                            # Highlight fields we're interested in
                            if any(term in field_name_lower for term in ['story point', 'storypoint', 'acceptance', 'criteria']):
                                status = "✅ TARGET" if not required else "✅ TARGET (Required)"
                                print(f"      {status} {field_id} - {field_name} (Type: {field_type})")
                            elif any(term in field_name_lower for term in ['epic', 'parent', 'business', 'value']):
                                print(f"      🔧 {field_id} - {field_name} (Type: {field_type})")
        
        except Exception as e:
            print(f"⚠️  Could not get project-specific field info: {e}")
            
        # Generate suggested field mapping
        print(f"\n🎯 SUGGESTED FIELD MAPPING:")
        
        field_map = {}
        
        if story_points_candidates:
            # Pick the most likely story points field
            best_sp = story_points_candidates[0]  # First one found
            field_map['storyPoints'] = best_sp['id']
            print(f"   'storyPoints': '{best_sp['id']}'  # {best_sp['name']}")
        
        if acceptance_criteria_candidates:
            # Pick the most likely acceptance criteria field
            best_ac = acceptance_criteria_candidates[0]  # First one found
            field_map['acceptanceCriteria'] = best_ac['id']
            print(f"   'acceptanceCriteria': '{best_ac['id']}'  # {best_ac['name']}")
        
        if not story_points_candidates and not acceptance_criteria_candidates:
            print("   ❌ No target fields found - your JIRA instance may not have these fields configured")
        
        print(f"\n💡 To test these fields, update your JIRA script or create them in your JIRA instance.")
        
    except Exception as e:
        print(f"❌ Error searching fields: {e}")
        sys.exit(1)

if __name__ == '__main__':
    find_custom_fields()