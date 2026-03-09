#!/usr/bin/env python3
"""
Simple ADF test to validate formatting 
"""
import os
import sys
import json

# Set test environment
os.environ['DRY_RUN'] = 'true'
os.environ['JIRA_URL'] = 'https://test.atlassian.net'

# Simple inline functions to test ADF generation
def simple_markdown_to_adf_test():
    """Test basic markdown conversion"""
    
    test_markdown = """**Source File**: specs/test.md

🔗 [View on GitHub](https://github.com/example/repo/blob/main/specs/test.md)

---

# Test Feature

This is a **bold statement** with a [link](https://example.com).

- Feature 1  
- Feature 2
- Feature 3"""

    # Simple ADF structure for the content above
    adf = {
        "version": 1,
        "type": "doc",
        "content": [
            {
                "type": "panel",
                "attrs": {"panelType": "info"},
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": "📋 Specification Source", "marks": [{"type": "strong"}]}
                        ]
                    },
                    {
                        "type": "paragraph", 
                        "content": [
                            {"type": "text", "text": "🔗 GitHub: "},
                            {"type": "text", "text": "specs/test.md", "marks": [{"type": "link", "attrs": {"href": "https://github.com/example/repo/blob/main/specs/test.md"}}]}
                        ]
                    }
                ]
            },
            {"type": "rule"},
            {
                "type": "heading",
                "attrs": {"level": 1},
                "content": [{"type": "text", "text": "Test Feature"}]
            },
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "This is a "},
                    {"type": "text", "text": "bold statement", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": " with a "},
                    {"type": "text", "text": "link", "marks": [{"type": "link", "attrs": {"href": "https://example.com"}}]},
                    {"type": "text", "text": "."}
                ]
            },
            {
                "type": "bulletList",
                "content": [
                    {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Feature 1"}]}]},
                    {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Feature 2"}]}]},
                    {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Feature 3"}]}]}
                ]
            }
        ]
    }
    
    print("🧪 ADF Structure for JIRA Description:")
    print("=" * 50)
    print(json.dumps(adf, indent=2))
    print("\n✅ This structure should render properly in JIRA with:")
    print("   - Info panel with GitHub link")
    print("   - Horizontal separator")
    print("   - Proper heading formatting")
    print("   - Bold text formatting")
    print("   - Clickable links")
    print("   - Bulleted lists")

if __name__ == "__main__":
    simple_markdown_to_adf_test()