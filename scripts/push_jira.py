#!/usr/bin/env python3
"""
Simple JIRA Push Script - Creates JIRA issues from generated draft

Usage:
    python scripts/push_jira.py [draft_file]
    
Environment Variables Required:
    JIRA_URL - JIRA instance URL (e.g., https://company.atlassian.net)
    JIRA_EMAIL - JIRA user email
    JIRA_TOKEN - JIRA API token
    JIRA_PROJECT - JIRA project key (e.g., SMM)
"""

import os
import sys
import yaml
import json
import requests
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

def clean_markdown(content: str) -> str:
    """Remove markdown formatting for JIRA compatibility"""
    if not content:
        return content
    
    # Remove markdown asterisks
    content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)  # **bold**
    content = re.sub(r'\*([^*]+)\*', r'\1', content)      # *italic*
    
    # Clean asterisks at line start
    lines = content.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('*') and not stripped.startswith('**'):
            cleaned = stripped.lstrip('* ').strip()
            indent = len(line) - len(line.lstrip())
            cleaned_lines.append(' ' * indent + cleaned)
        else:
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def extract_acceptance_scenarios(description: str) -> str:
    """Extract acceptance scenarios from story description"""
    if not description:
        return ""
    
    lines = description.split('\n')
    scenarios = []
    in_scenarios = False
    
    for line in lines:
        stripped = line.strip()
        if 'acceptance scenarios' in stripped.lower():
            in_scenarios = True
            scenarios.append("ACCEPTANCE SCENARIOS:")
            continue
        elif in_scenarios:
            if (stripped.startswith('**') and 
                any(word in stripped.lower() for word in ['definition of done', 'related', 'priority'])):
                break
            elif stripped:
                cleaned = clean_markdown(line)
                cleaned = cleaned.replace(',,', '\n  ')
                scenarios.append(cleaned)
    
    return '\n'.join(scenarios) if scenarios else ""

class SimpleJiraPusher:
    def __init__(self, draft_file: str = None):
        # Load configuration
        self.jira_url = os.getenv('JIRA_URL')
        self.jira_email = os.getenv('JIRA_EMAIL') 
        self.jira_token = os.getenv('JIRA_TOKEN')
        self.jira_project = os.getenv('JIRA_PROJECT')
        
        if not all([self.jira_url, self.jira_email, self.jira_token, self.jira_project]):
            print("❌ Missing JIRA environment variables:")
            print("   JIRA_URL, JIRA_EMAIL, JIRA_TOKEN, JIRA_PROJECT")
            sys.exit(1)
        
        # Setup session
        self.session = requests.Session()
        self.session.auth = (self.jira_email, self.jira_token)
        self.session.headers = {'Content-Type': 'application/json'}
        
        # Draft file
        self.draft_file = self._find_draft_file(draft_file)
        
    def _find_draft_file(self, draft_file: str) -> Path:
        """Find draft file"""
        if draft_file:
            path = Path(draft_file)
            if not path.is_absolute():
                path = Path.cwd() / path
        else:
            # Find latest draft
            jira_dir = Path.cwd() / 'jira'
            if jira_dir.exists():
                drafts = list(jira_dir.glob('*-draft.yaml'))
                if drafts:
                    path = sorted(drafts)[-1]
                else:
                    print("❌ No draft files found")
                    sys.exit(1)
            else:
                print("❌ No jira directory found")
                sys.exit(1)
        
        if not path.exists():
            print(f"❌ Draft file not found: {path}")
            sys.exit(1)
        return path
    
    def load_draft(self) -> Dict[str, Any]:
        """Load YAML draft"""
        print(f"📄 Loading: {self.draft_file}")
        with open(self.draft_file, 'r') as f:
            draft = yaml.safe_load(f)
        
        print(f"✅ Loaded: {draft['metadata']['feature']}")
        return draft
    
    def test_connection(self) -> bool:
        """Test JIRA connection"""
        try:
            response = self.session.get(f"{self.jira_url}/rest/api/2/myself")
            response.raise_for_status()
            user = response.json()
            print(f"✅ Connected as: {user.get('displayName', 'Unknown')}")
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print("❌ Authentication failed - check JIRA_EMAIL and JIRA_TOKEN")
            else:
                print(f"❌ JIRA error: {e}")
            return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def get_issue_types(self) -> List[str]:
        """Get available issue types"""
        try:
            response = self.session.get(f"{self.jira_url}/rest/api/2/project/{self.jira_project}")
            response.raise_for_status()
            project = response.json()
            
            types = []
            for issue_type in project.get('issueTypes', []):
                types.append(issue_type['name'])
            
            print(f"📋 Issue types: {types}")
            return types
        except Exception as e:
            print(f"⚠️  Could not get issue types: {e}")
            return ['Task', 'Epic']
    
    def map_issue_type(self, requested: str, available: List[str]) -> str:
        """Map requested issue type to available"""
        if requested in available:
            return requested
        
        # Simple mapping
        mappings = {
            'Story': 'Task',
            'User Story': 'Task',
            'Feature': 'Epic'
        }
        
        mapped = mappings.get(requested, 'Task')
        if mapped not in available:
            mapped = available[0] if available else 'Task'
        
        if mapped != requested:
            print(f"   🔄 Mapping '{requested}' → '{mapped}'")
        
        return mapped
    
    def create_epic(self, epic_data: Dict[str, Any]) -> Optional[str]:
        """Create epic"""
        print(f"\n📋 Creating Epic: {epic_data['summary']}")
        
        # Clean description
        description = clean_markdown(epic_data['description'])
        
        # Add GitHub link
        feature = epic_data.get('key', 'unknown')
        github_link = f"\n\n🔗 GitHub: https://github.com/your-org/your-repo/tree/main/specs/{feature.split('-')[0]}"
        description += github_link
        
        payload = {
            "fields": {
                "project": {"key": self.jira_project},
                "summary": epic_data['summary'],
                "description": description,
                "issuetype": {"name": epic_data['issueType']},
                "priority": {"name": epic_data.get('priority', 'Medium')}
            }
        }
        
        try:
            response = self.session.post(f"{self.jira_url}/rest/api/2/issue", json=payload)
            response.raise_for_status()
            result = response.json()
            key = result['key']
            print(f"✅ Epic created: {key}")
            return key
        except Exception as e:
            print(f"❌ Epic creation failed: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"   Response: {e.response.text}")
            return None
    
    def create_story(self, story_data: Dict[str, Any], epic_key: str) -> Optional[str]:
        """Create story"""
        print(f"   📝 Creating: {story_data['summary']}")
        
        # Clean description and add acceptance scenarios
        description = clean_markdown(story_data['description'])
        
        # Add acceptance scenarios
        scenarios = extract_acceptance_scenarios(story_data['description'])
        if not scenarios and story_data.get('customFields', {}).get('acceptanceCriteria'):
            criteria = story_data['customFields']['acceptanceCriteria']
            scenarios = "ACCEPTANCE SCENARIOS:\n" + criteria.replace(',,', '\n  ')
        
        if scenarios:
            description += f"\n\n{'-'*50}\n{scenarios}\n{'-'*50}"
        
        # Add GitHub link
        feature = story_data.get('key', 'unknown')
        github_link = f"\n\n🔗 GitHub: https://github.com/your-org/your-repo/tree/main/specs/{feature.split('-')[0]}"
        description += github_link
        
        payload = {
            "fields": {
                "project": {"key": self.jira_project},
                "summary": story_data['summary'],
                "description": description,
                "issuetype": {"name": story_data['issueType']},
                "priority": {"name": story_data.get('priority', 'Medium')}
            }
        }
        
        # Link to epic
        if epic_key:
            payload["fields"]["parent"] = {"key": epic_key}
        
        try:
            response = self.session.post(f"{self.jira_url}/rest/api/2/issue", json=payload)
            response.raise_for_status()
            result = response.json()
            key = result['key']
            print(f"      ✅ Story created: {key}")
            return key
        except Exception as e:
            print(f"      ❌ Story creation failed: {e}")
            return None
    
    def push_to_jira(self) -> bool:
        """Main push function"""
        # Load draft
        draft = self.load_draft()
        
        # Test connection
        if not self.test_connection():
            return False
        
        # Get issue types
        issue_types = self.get_issue_types()
        
        print(f"\n🚀 Pushing to JIRA project: {self.jira_project}")
        
        # Create epic
        epic_data = draft['epic'].copy()
        epic_data['issueType'] = self.map_issue_type(epic_data['issueType'], issue_types)
        epic_key = self.create_epic(epic_data)
        
        if not epic_key:
            print("❌ Failed to create epic")
            return False
        
        # Create stories
        story_count = 0
        for story_data in draft['stories']:
            story_copy = story_data.copy()
            story_copy['issueType'] = self.map_issue_type(story_copy['issueType'], issue_types)
            
            if self.create_story(story_copy, epic_key):
                story_count += 1
        
        print(f"\n🎉 Success!")
        print(f"   Epic: {epic_key}")
        print(f"   Stories: {story_count} created")
        print(f"   URL: {self.jira_url}/browse/{epic_key}")
        
        return True

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Push JIRA draft to JIRA')
    parser.add_argument('draft_file', nargs='?', help='Draft YAML file')
    args = parser.parse_args()
    
    pusher = SimpleJiraPusher(args.draft_file)
    success = pusher.push_to_jira()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()