#!/usr/bin/env python3
"""
JSON Template Validation Script for JIRA Sync
Tests the new JSON-based template system and validates structure
"""

import json
import sys
from pathlib import Path

# Add the scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def validate_templates_json():
    """Validate the templates.json file structure"""
    templates_file = Path(__file__).parent / "templates" / "templates.json"
    
    print("🔍 Validating JSON Templates...")
    print(f"   Template file: {templates_file}")
    
    if not templates_file.exists():
        print("❌ ERROR: templates.json file not found!")
        return False
    
    try:
        with open(templates_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print("✅ JSON syntax is valid")
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON syntax: {e}")
        return False
    
    # Validate structure
    required_sections = ['templates', 'field_mappings', 'default_values']
    missing_sections = [s for s in required_sections if s not in data]
    
    if missing_sections:
        print(f"⚠️  WARNING: Missing sections: {', '.join(missing_sections)}")
    else:
        print("✅ All required sections present")
    
    # Validate templates
    if 'templates' in data:
        required_templates = ['epic', 'story', 'task', 'bug']
        available_templates = list(data['templates'].keys())
        missing_templates = [t for t in required_templates if t not in available_templates]
        
        print(f"📋 Available templates: {', '.join(available_templates)}")
        
        if missing_templates:
            print(f"⚠️  Missing templates: {', '.join(missing_templates)}")
        else:
            print("✅ All required templates present")
        
        # Validate each template structure
        for template_name, template_data in data['templates'].items():
            print(f"\n🔍 Validating template: {template_name}")
            
            required_fields = ['summary', 'issue_type', 'description', 'labels']
            template_fields = list(template_data.keys())
            missing_fields = [f for f in required_fields if f not in template_fields]
            
            if missing_fields:
                print(f"   ⚠️  Missing fields: {', '.join(missing_fields)}")
            else:
                print("   ✅ Required fields present")
            
            # Check description structure
            if 'description' in template_data and isinstance(template_data['description'], dict):
                desc_fields = ['source_file', 'github_link', 'content']
                desc_missing = [f for f in desc_fields if f not in template_data['description']]
                if desc_missing:
                    print(f"   ⚠️  Missing description fields: {', '.join(desc_missing)}")
                else:
                    print("   ✅ Description structure valid")
    
    return True

def test_template_loading():
    """Test template loading functionality"""
    print("\n🧪 Testing Template Loading...")
    
    try:
        # Import after adding to path
        from jira_sync import load_template, get_field_mappings, get_default_values
        
        # Test loading each template type
        test_types = ['Epic', 'Story', 'Task', 'Bug']
        
        for issue_type in test_types:
            try:
                template = load_template(issue_type)
                print(f"   ✅ {issue_type} template loaded successfully")
                
                # Check for required placeholders
                summary = template.get('summary', '')
                if '{SUMMARY}' in summary:
                    print(f"      ✅ Summary placeholder found")
                else:
                    print(f"      ⚠️  Summary placeholder missing")
                    
            except Exception as e:
                print(f"   ❌ {issue_type} template failed: {e}")
        
        # Test field mappings
        try:
            mappings = get_field_mappings()
            print(f"   ✅ Field mappings loaded: {len(mappings)} mappings")
        except Exception as e:
            print(f"   ❌ Field mappings failed: {e}")
        
        # Test default values
        try:
            defaults = get_default_values()
            print(f"   ✅ Default values loaded: {len(defaults)} defaults")
        except Exception as e:
            print(f"   ❌ Default values failed: {e}")
            
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        return False
    
    return True

def main():
    """Main validation function"""
    print("=" * 60)
    print("JSON TEMPLATE VALIDATION FOR JIRA SYNC")
    print("=" * 60)
    
    success = True
    
    # Step 1: Validate JSON structure
    if not validate_templates_json():
        success = False
    
    # Step 2: Test template loading
    if not test_template_loading():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ALL VALIDATIONS PASSED!")
        print("✅ JSON templates are ready for JIRA sync")
    else:
        print("❌ VALIDATION FAILED!")
        print("🔧 Please fix the issues above before running JIRA sync")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)