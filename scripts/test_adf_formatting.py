#!/usr/bin/env python3
"""
Test ADF formatting generation
"""
import os
import sys
sys.path.insert(0, '.')

# Set minimal environment to avoid validation errors
os.environ['DRY_RUN'] = 'true'
os.environ['JIRA_URL'] = 'https://test.atlassian.net'
os.environ['JIRA_EMAIL'] = 'test@example.com'
os.environ['JIRA_TOKEN'] = 'test-token'
os.environ['JIRA_PROJECT'] = 'TEST'

from jira_sync import markdown_to_adf, json_to_adf_description
import json

def test_markdown_to_adf():
    """Test markdown to ADF conversion"""
    
    print("🧪 Testing Markdown to ADF Conversion")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        {
            "name": "Bold text",
            "markdown": "This is **bold text** and this is normal.",
            "expect": "Should have strong marks"
        },
        {
            "name": "Links", 
            "markdown": "Check out [GitHub](https://github.com) for code.",
            "expect": "Should have link marks with href"
        },
        {
            "name": "Headers",
            "markdown": "# Main Title\n## Sub Title\nSome content",
            "expect": "Should have heading nodes"
        },
        {
            "name": "Lists",
            "markdown": "- Item 1\n- Item 2\n- Item 3",
            "expect": "Should have bulletList structure"
        },
        {
            "name": "Horizontal rule",
            "markdown": "Before rule\n---\nAfter rule",
            "expect": "Should have rule node"
        }
    ]
    
    for test in test_cases:
        print(f"\n📋 Test: {test['name']}")
        print(f"Input: {test['markdown'][:50]}...")
        print(f"Expected: {test['expect']}")
        
        adf = markdown_to_adf(test['markdown'])
        print(f"ADF Structure:")
        print(json.dumps(adf, indent=2)[:200] + "...")

def test_description_formatting():
    """Test the complete description formatting"""
    
    print("\n🧪 Testing JIRA Description Generation")
    print("=" * 50)
    
    test_json_data = {
        "description": {
            "source_file": "specs/test/example.md",
            "github_link": "https://github.com/example/repo/blob/main/specs/test/example.md", 
            "content": """# Feature Overview

This is a **test feature** with the following requirements:

- Must support multiple users
- Should have [API documentation](https://api.example.com)
- Include proper error handling

## Acceptance Criteria

- ✅ User can login
- ✅ System handles errors gracefully
- ⚠️ Performance testing needed

---

**Note**: This is just a test specification."""
        }
    }
    
    adf = json_to_adf_description(test_json_data)
    
    print("Generated ADF Description:")
    print(json.dumps(adf, indent=2))
    
    # Validate structure
    if adf.get("version") == 1 and adf.get("type") == "doc":
        print("\n✅ Valid ADF document structure")
        
        content = adf.get("content", [])
        print(f"✅ Content blocks: {len(content)}")
        
        # Check for panel (info box)
        has_panel = any(block.get("type") == "panel" for block in content)
        if has_panel:
            print("✅ Info panel for GitHub link found")
        else:
            print("⚠️  No info panel found")
            
        # Check for rule separator
        has_rule = any(block.get("type") == "rule" for block in content)
        if has_rule:
            print("✅ Rule separator found")
        else:
            print("⚠️  No rule separator found")
            
        # Check for formatted content
        has_headings = any(block.get("type") == "heading" for block in content)
        if has_headings:
            print("✅ Formatted headings found")
        else:
            print("⚠️  No formatted headings found")
            
    else:
        print("❌ Invalid ADF document structure")

if __name__ == "__main__":
    test_markdown_to_adf()
    test_description_formatting()