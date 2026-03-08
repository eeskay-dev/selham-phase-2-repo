#!/usr/bin/env python3
"""
JIRA Push Script - Creates JIRA issues from generated draft

Usage:
    python scripts/push_jira.py [draft_file]
    
Examples:
    python scripts/push_jira.py jira/001-multi-brand-menu-mgmt-draft.yaml
    python scripts/push_jira.py  # Auto-detects latest draft
    
Environment Variables Required:
    JIRA_URL - JIRA instance URL (e.g., https://company.atlassian.net)
    JIRA_EMAIL - JIRA user email
    JIRA_TOKEN - JIRA API token
    JIRA_PROJECT - JIRA project key (e.g., SPEC)
"""

import os
import sys
import yaml
import json
import requests
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

class JiraPusher:
    def __init__(self, draft_file: Optional[str] = None, dry_run: bool = False, github_context: Optional[Dict[str, str]] = None):
        self.repo_root = Path.cwd()
        self.draft_file = self._resolve_draft_file(draft_file)
        self.dry_run = dry_run
        self.github_context = github_context or {}
        
        # Load JIRA configuration
        self._load_jira_config()
        
        # Initialize JIRA session
        self.session = requests.Session()
        self.session.auth = (self.jira_email, self.jira_token)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Issue creation tracking
        self.created_issues = {
            'epic': None,
            'stories': {},
            'tasks': {}
        }
        
        # Extract feature name for GitHub integration
        self.feature_name = self.draft_file.stem.replace('-draft', '')
        
        # Mapping for spec-to-jira references
        self.spec_jira_mapping = {}
        
    def _load_jira_config(self):
        """Load JIRA configuration from environment variables"""
        self.jira_url = os.environ.get('JIRA_URL', '').rstrip('/')
        self.jira_email = os.environ.get('JIRA_EMAIL')
        self.jira_token = os.environ.get('JIRA_TOKEN') 
        self.jira_project = os.environ.get('JIRA_PROJECT')
        
        # Validate required configuration
        missing = []
        if not self.jira_url:
            missing.append('JIRA_URL')
        if not self.jira_email:
            missing.append('JIRA_EMAIL') 
        if not self.jira_token:
            missing.append('JIRA_TOKEN')
        if not self.jira_project:
            missing.append('JIRA_PROJECT')
            
        if missing and not self.dry_run:
            print(f"❌ ERROR: Missing required environment variables: {', '.join(missing)}")
            print(f"💡 Set environment variables or use --dry-run flag for testing")
            print(f"Example:")
            print(f"  export JIRA_URL=https://company.atlassian.net")
            print(f"  export JIRA_EMAIL=user@company.com")
            print(f"  export JIRA_TOKEN=your_api_token")
            print(f"  export JIRA_PROJECT=SPEC")
            sys.exit(1)
            
        if not self.dry_run:
            print(f"✅ JIRA Configuration:")
            print(f"   URL: {self.jira_url}")
            print(f"   Project: {self.jira_project}")
            print(f"   Email: {self._mask_credential(self.jira_email)}")
            print(f"   Token: {self._mask_credential(self.jira_token)}")
        
    def _mask_credential(self, credential: str) -> str:
        """Mask sensitive credentials for safe display"""
        if not credential:
            return "***MISSING***"
        if len(credential) <= 8:
            return "***"
        return f"{credential[:3]}***{credential[-3:]}"
        
    def _resolve_draft_file(self, draft_file: Optional[str]) -> Path:
        """Resolve draft file path from argument or auto-detect"""
        if draft_file:
            path = Path(draft_file)
            if not path.is_absolute():
                path = self.repo_root / path
        else:
            # Auto-detect latest draft file
            jira_dir = self.repo_root / 'jira'
            if jira_dir.exists():
                draft_files = list(jira_dir.glob('*-draft.yaml'))
                if draft_files:
                    path = sorted(draft_files)[-1]  # Latest by name
                else:
                    raise ValueError("No draft files found in jira/ directory")
            else:
                raise ValueError("No jira directory found and no draft file provided")
                
        if not path.exists():
            raise ValueError(f"Draft file does not exist: {path}")
        return path
    
    def load_draft(self) -> Dict[str, Any]:
        """Load JIRA draft from YAML file"""
        print(f"Loading JIRA draft: {self.draft_file}")
        
        with open(self.draft_file, 'r') as f:
            draft = yaml.safe_load(f)
        
        # Validate draft structure
        required_sections = ['metadata', 'project', 'epic', 'stories']
        for section in required_sections:
            if section not in draft:
                raise ValueError(f"Missing required section in draft: {section}")
        
        print(f"✅ Draft loaded successfully")
        print(f"   Feature: {draft['metadata']['feature']}")
        print(f"   Epic: {draft['epic']['summary']}")
        print(f"   Stories: {len(draft['stories'])}")
        print(f"   Tasks: {len(draft.get('tasks', []))}")
        
        return draft
    
    def validate_jira_connection(self) -> bool:
        """Validate JIRA connection and permissions"""
        if self.dry_run:
            print("🔧 DRY RUN: Skipping JIRA connection validation")
            return True
            
        print("🔍 Testing JIRA authentication...")
        
        try:
            # Test connection with myself endpoint
            response = self.session.get(f"{self.jira_url}/rest/api/2/myself")
            
            if response.status_code == 401:
                print(f"❌ JIRA Authentication Failed (401 Unauthorized)")
                print(f"🔍 Troubleshooting steps:")
                print(f"   1. Verify JIRA_EMAIL is correct: {self._mask_credential(self.jira_email)}")
                print(f"   2. Check JIRA_TOKEN is valid API token (not password)")
                print(f"   3. Ensure API token has not expired")
                print(f"   4. Verify JIRA URL is correct: {self.jira_url}")
                print(f"   5. Test manually: curl -u '{self.jira_email}:TOKEN' {self.jira_url}/rest/api/2/myself")
                return False
            elif response.status_code == 403:
                print(f"❌ JIRA Permission Denied (403 Forbidden)")
                print(f"🔍 The credentials are valid but lack necessary permissions")
                print(f"   Contact JIRA admin to grant API access")
                return False
                
            response.raise_for_status()
            
            user_info = response.json()
            print(f"✅ JIRA connection validated")
            print(f"   User: {user_info.get('displayName', 'Unknown')}")
            print(f"   Account ID: {user_info.get('accountId', 'Unknown')}")
            
            # Validate project exists
            print(f"🔍 Testing project access...")
            response = self.session.get(f"{self.jira_url}/rest/api/2/project/{self.jira_project}")
            
            if response.status_code == 404:
                print(f"❌ JIRA Project Not Found (404)")
                print(f"🔍 Project '{self.jira_project}' does not exist or is not accessible")
                print(f"   Check project key and permissions")
                return False
            elif response.status_code == 403:
                print(f"❌ JIRA Project Access Denied (403)")
                print(f"🔍 User lacks permission to access project '{self.jira_project}'")
                print(f"   Contact JIRA admin to grant project access")
                return False
                
            response.raise_for_status()
            
            project_info = response.json()
            print(f"✅ Project access validated: {project_info.get('name', self.jira_project)}")
            print(f"   Project Key: {project_info.get('key', 'Unknown')}")
            
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ JIRA connection failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Status: {e.response.status_code}")
                print(f"   Response: {e.response.text}")
            print(f"🔍 Network troubleshooting:")
            print(f"   1. Check internet connectivity")
            print(f"   2. Verify JIRA URL is reachable: {self.jira_url}")
            print(f"   3. Check firewall/proxy settings")
            return False
    
    def create_epic(self, epic_data: Dict[str, Any]) -> Optional[str]:
        """Create JIRA epic and return issue key"""
        print(f"\n📋 Creating Epic: {epic_data['summary']}")
        
        # Build JIRA issue payload with GitHub context
        description_with_github = epic_data['description'] + self._build_github_section(self.feature_name)
        issue_payload = {
            "fields": {
                "project": {"key": self.jira_project},
                "summary": epic_data['summary'],
                "description": self._format_adf_description(description_with_github),
                "issuetype": {"name": epic_data['issueType']},
                "priority": {"name": epic_data['priority']},
                "labels": epic_data.get('labels', []),
            }
        }
        
        # Add epic name for Epic issue type
        if epic_data['issueType'] == 'Epic':
            issue_payload["fields"]["customfield_10011"] = epic_data['summary']  # Epic Name field
        
        # Add custom fields if present
        custom_fields = epic_data.get('customFields', {})
        for field_name, field_value in custom_fields.items():
            # Map custom field names to JIRA field IDs (these may need adjustment)
            field_mapping = {
                'businessValue': 'customfield_10020',
                'targetRelease': 'customfield_10021', 
                'estimatedEffort': 'customfield_10022'
            }
            
            if field_name in field_mapping:
                issue_payload["fields"][field_mapping[field_name]] = field_value
        
        if self.dry_run:
            print(f"🔧 DRY RUN: Would create epic with payload:")
            print(f"   Summary: {issue_payload['fields']['summary']}")
            print(f"   Type: {issue_payload['fields']['issuetype']['name']}")
            epic_key = f"DRY-{epic_data['key']}"
        else:
            try:
                response = self.session.post(
                    f"{self.jira_url}/rest/api/2/issue",
                    json=issue_payload
                )
                response.raise_for_status()
                
                result = response.json()
                epic_key = result['key']
                
                print(f"✅ Epic created: {epic_key}")
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Failed to create epic: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    print(f"   Response: {e.response.text}")
                return None
        
        # Track created epic
        self.created_issues['epic'] = epic_key
        self.spec_jira_mapping[epic_data['key']] = epic_key
        
        return epic_key
    
    def _build_github_section(self, feature_name: str) -> str:
        """Build GitHub integration section for JIRA descriptions"""
        if not self.github_context:
            return ""
        
        github_section = "\n\n---\n**🔗 GitHub Integration**\n"
        
        # Repository link
        repo_name = self.github_context.get('repo')
        if repo_name:
            repo_url = f"https://github.com/{repo_name}"
            github_section += f"* Repository: [{repo_name}]({repo_url})\n"
        
        # Specification file link
        spec_path = self.github_context.get('spec_path')
        branch = self.github_context.get('branch', 'main')
        if repo_name and spec_path:
            spec_url = f"https://github.com/{repo_name}/blob/{branch}/{spec_path}spec.md"
            github_section += f"* Specification: [{spec_path}spec.md]({spec_url})\n"
        
        # Pull request link
        pr_number = self.github_context.get('pr_number')
        if repo_name and pr_number:
            pr_url = f"https://github.com/{repo_name}/pull/{pr_number}"
            github_section += f"* Pull Request: [#{pr_number}]({pr_url})\n"
        
        # Workflow run link
        workflow_url = self.github_context.get('workflow_url')
        if workflow_url:
            github_section += f"* Workflow Run: [View Details]({workflow_url})\n"
        
        # Feature directory link
        if repo_name and feature_name:
            feature_url = f"https://github.com/{repo_name}/tree/{branch}/specs/{feature_name}"
            github_section += f"* Feature Directory: [specs/{feature_name}/]({feature_url})\n"
        
        return github_section
    
    def create_stories(self, stories_data: List[Dict[str, Any]], epic_key: str) -> List[str]:
        """Create JIRA stories under epic and return issue keys"""
        print(f"\n📝 Creating {len(stories_data)} Stories under Epic {epic_key}")
        
        story_keys = []
        
        for i, story_data in enumerate(stories_data, 1):
            print(f"   [{i}/{len(stories_data)}] {story_data['summary']}")
            
            # Build JIRA issue payload with GitHub context  
            story_description_with_github = story_data['description'] + self._build_github_section(self.feature_name)
            issue_payload = {
                "fields": {
                    "project": {"key": self.jira_project},
                    "summary": story_data['summary'],
                    "description": self._format_adf_description(story_description_with_github),
                    "issuetype": {"name": story_data['issueType']},
                    "priority": {"name": story_data['priority']},
                    "labels": story_data.get('labels', []),
                }
            }
            
            # Link to epic
            if epic_key and not self.dry_run:
                issue_payload["fields"]["customfield_10014"] = epic_key  # Epic Link field
            
            # Add custom fields
            custom_fields = story_data.get('customFields', {})
            for field_name, field_value in custom_fields.items():
                field_mapping = {
                    'storyPoints': 'customfield_10016',
                    'acceptanceCriteria': 'customfield_10017'
                }
                
                if field_name in field_mapping:
                    issue_payload["fields"][field_mapping[field_name]] = field_value
            
            if self.dry_run:
                story_key = f"DRY-{story_data['key']}"
                print(f"      🔧 DRY RUN: Would create {story_key}")
            else:
                try:
                    response = self.session.post(
                        f"{self.jira_url}/rest/api/2/issue",
                        json=issue_payload
                    )
                    response.raise_for_status()
                    
                    result = response.json()
                    story_key = result['key']
                    
                    print(f"      ✅ Story created: {story_key}")
                    
                except requests.exceptions.RequestException as e:
                    print(f"      ❌ Failed to create story: {e}")
                    if hasattr(e, 'response') and e.response is not None:
                        print(f"         Response: {e.response.text}")
                    continue
            
            # Track created story
            story_keys.append(story_key)
            self.created_issues['stories'][story_data['key']] = story_key
            self.spec_jira_mapping[story_data['key']] = story_key
        
        print(f"✅ Created {len(story_keys)} stories successfully")
        return story_keys
    
    def create_tasks(self, tasks_data: List[Dict[str, Any]], stories_mapping: Dict[str, str]) -> List[str]:
        """Create JIRA tasks under stories and return issue keys"""
        if not tasks_data:
            print(f"\n📋 No tasks to create")
            return []
            
        print(f"\n🔧 Creating {len(tasks_data)} Tasks under Stories")
        
        task_keys = []
        
        for i, task_data in enumerate(tasks_data, 1):
            print(f"   [{i}/{len(tasks_data)}] {task_data['summary']}")
            
            # Find parent story
            parent_story_key = None
            if task_data.get('parentStory'):
                parent_story_key = stories_mapping.get(task_data['parentStory'])
            
            # Build JIRA issue payload with GitHub context
            task_description_with_github = task_data['description'] + self._build_github_section(self.feature_name)
            issue_payload = {
                "fields": {
                    "project": {"key": self.jira_project},
                    "summary": task_data['summary'],
                    "description": self._format_adf_description(task_description_with_github),
                    "issuetype": {"name": task_data['issueType']},
                    "priority": {"name": task_data['priority']},
                    "labels": task_data.get('labels', []),
                }
            }
            
            # Link to parent story
            if parent_story_key and not self.dry_run:
                issue_payload["fields"]["parent"] = {"key": parent_story_key}
            
            # Add custom fields
            custom_fields = task_data.get('customFields', {})
            for field_name, field_value in custom_fields.items():
                field_mapping = {
                    'taskPhase': 'customfield_10023',
                    'estimatedHours': 'customfield_10024',
                    'technicalComplexity': 'customfield_10025',
                    'parallelExecution': 'customfield_10026'
                }
                
                if field_name in field_mapping:
                    issue_payload["fields"][field_mapping[field_name]] = field_value
            
            if self.dry_run:
                task_key = f"DRY-{task_data['key']}"
                parent_info = f" → {parent_story_key}" if parent_story_key else ""
                print(f"      🔧 DRY RUN: Would create {task_key}{parent_info}")
            else:
                try:
                    response = self.session.post(
                        f"{self.jira_url}/rest/api/2/issue",
                        json=issue_payload
                    )
                    response.raise_for_status()
                    
                    result = response.json()
                    task_key = result['key']
                    
                    parent_info = f" → {parent_story_key}" if parent_story_key else ""
                    print(f"      ✅ Task created: {task_key}{parent_info}")
                    
                except requests.exceptions.RequestException as e:
                    print(f"      ❌ Failed to create task: {e}")
                    if hasattr(e, 'response') and e.response is not None:
                        print(f"         Response: {e.response.text}")
                    continue
            
            # Track created task
            task_keys.append(task_key)
            self.created_issues['tasks'][task_data['key']] = task_key
            self.spec_jira_mapping[task_data['key']] = task_key
        
        print(f"✅ Created {len(task_keys)} tasks successfully")
        return task_keys
    
    def _format_adf_description(self, description: str) -> Dict[str, Any]:
        """Convert markdown description to Atlassian Document Format (ADF)"""
        # Simple ADF conversion - can be enhanced for full markdown support
        paragraphs = []
        
        for paragraph in description.split('\n\n'):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            # Handle bullet lists
            if paragraph.startswith('- '):
                list_items = []
                for line in paragraph.split('\n'):
                    if line.startswith('- '):
                        list_items.append({
                            "type": "listItem",
                            "content": [{
                                "type": "paragraph",
                                "content": [{"type": "text", "text": line[2:]}]
                            }]
                        })
                
                if list_items:
                    paragraphs.append({
                        "type": "bulletList",
                        "content": list_items
                    })
            else:
                # Regular paragraph
                paragraphs.append({
                    "type": "paragraph", 
                    "content": [{"type": "text", "text": paragraph}]
                })
        
        return {
            "version": 1,
            "type": "doc",
            "content": paragraphs if paragraphs else [{
                "type": "paragraph",
                "content": [{"type": "text", "text": description[:32000]}]
            }]
        }
    
    def save_mapping_file(self, feature_name: str) -> Path:
        """Save spec-to-JIRA mapping file"""
        mapping_file = self.repo_root / 'jira' / f'{feature_name}-map.json'
        
        mapping_data = {
            'metadata': {
                'generated': datetime.now().isoformat(),
                'feature': feature_name,
                'draft_file': str(self.draft_file),
                'jira_url': self.jira_url,
                'jira_project': self.jira_project
            },
            'mapping': self.spec_jira_mapping,
            'created_issues': {
                'epic': self.created_issues['epic'],
                'stories': list(self.created_issues['stories'].values()),
                'tasks': list(self.created_issues['tasks'].values()),
                'total': len(self.spec_jira_mapping)
            }
        }
        
        with open(mapping_file, 'w') as f:
            json.dump(mapping_data, f, indent=2)
        
        print(f"\n💾 Mapping file saved: {mapping_file}")
        return mapping_file
    
    def push_to_jira(self) -> bool:
        """Main method to push draft to JIRA"""
        try:
            # Load draft
            draft = self.load_draft()
            
            # Validate JIRA connection
            if not self.validate_jira_connection():
                return False
            
            feature_name = draft['metadata']['feature']
            
            print(f"\n🚀 Pushing {feature_name} to JIRA...")
            if self.dry_run:
                print(f"🔧 DRY RUN MODE: No actual JIRA issues will be created")
            
            # Create Epic
            epic_key = self.create_epic(draft['epic'])
            if not epic_key:
                print(f"❌ Failed to create epic, aborting")
                return False
            
            # Create Stories
            story_keys = self.create_stories(draft['stories'], epic_key)
            
            # Create Tasks (if any)
            task_keys = []
            if 'tasks' in draft and draft['tasks']:
                task_keys = self.create_tasks(draft['tasks'], self.created_issues['stories'])
            
            # Save mapping file
            mapping_file = self.save_mapping_file(feature_name)
            
            # Summary
            print(f"\n🎉 JIRA Push Complete!")
            print(f"   Epic: {epic_key}")
            print(f"   Stories: {len(story_keys)} created")
            print(f"   Tasks: {len(task_keys)} created")
            print(f"   Mapping: {mapping_file}")
            
            if not self.dry_run:
                print(f"   JIRA URL: {self.jira_url}/browse/{epic_key}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to push to JIRA: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Push JIRA draft to JIRA instance')
    parser.add_argument('draft_file', nargs='?', help='JIRA draft YAML file (auto-detects if not provided)')
    parser.add_argument('--dry-run', action='store_true', help='Test mode - do not create actual JIRA issues')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    # GitHub Integration Parameters
    parser.add_argument('--github-repo', help='GitHub repository name (e.g., owner/repo)')
    parser.add_argument('--github-pr', help='GitHub pull request number')
    parser.add_argument('--github-workflow', help='GitHub workflow run URL')
    parser.add_argument('--spec-path', help='Relative path to spec file in repository')
    parser.add_argument('--github-branch', help='Git branch name', default='main')
    
    args = parser.parse_args()
    
    try:
        # Build GitHub context from arguments
        github_context = {}
        if args.github_repo:
            github_context['repo'] = args.github_repo
        if args.github_pr:
            github_context['pr_number'] = args.github_pr
        if args.github_workflow:
            github_context['workflow_url'] = args.github_workflow
        if args.spec_path:
            github_context['spec_path'] = args.spec_path
        if args.github_branch:
            github_context['branch'] = args.github_branch
        
        pusher = JiraPusher(args.draft_file, args.dry_run, github_context)
        success = pusher.push_to_jira()
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()