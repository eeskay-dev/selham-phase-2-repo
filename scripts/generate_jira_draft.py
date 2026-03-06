#!/usr/bin/env python3
"""
JIRA Draft Generator - Converts Spec-Kit tasks to JIRA work items

Usage:
    python scripts/generate_jira_draft.py [feature_path]
    
Examples:
    python scripts/generate_jira_draft.py specs/001-multi-brand-menu-mgmt/
    python scripts/generate_jira_draft.py  # Auto-detects current feature
"""

import os
import sys
import yaml
import re
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

class JiraDraftGenerator:
    def __init__(self, feature_path: Optional[str] = None):
        self.repo_root = Path.cwd()
        self.feature_path = self._resolve_feature_path(feature_path)
        self.feature_name = self.feature_path.name
        self.feature_number = self._extract_feature_number()
        
        # JIRA Configuration
        self.jira_config = {
            'project_key': 'SPEC',
            'issue_types': {
                'epic': 'Epic',
                'story': 'Story', 
                'task': 'Sub-task'
            },
            'priorities': {
                'P1': 'Highest',
                'P2': 'High', 
                'P3': 'Medium',
                'P4': 'Low'
            }
        }
        
    def _resolve_feature_path(self, feature_path: Optional[str]) -> Path:
        """Resolve feature path from argument or auto-detect"""
        if feature_path:
            path = Path(feature_path)
            if not path.is_absolute():
                path = self.repo_root / path
        else:
            # Auto-detect from current branch or specs directory
            specs_dir = self.repo_root / 'specs'
            if specs_dir.exists():
                # Find the most recent feature directory
                feature_dirs = [d for d in specs_dir.iterdir() if d.is_dir()]
                if feature_dirs:
                    path = sorted(feature_dirs)[-1]  # Latest by name
                else:
                    raise ValueError("No feature directories found in specs/")
            else:
                raise ValueError("No specs directory found and no feature path provided")
                
        if not path.exists():
            raise ValueError(f"Feature path does not exist: {path}")
        return path
    
    def _extract_feature_number(self) -> str:
        """Extract feature number from directory name"""
        match = re.match(r'^(\d+)', self.feature_name)
        return match.group(1) if match else "001"
    
    def load_spec_files(self) -> Dict[str, Any]:
        """Load and parse spec files"""
        spec_data = {}
        
        # Load spec.md
        spec_file = self.feature_path / 'spec.md'
        if spec_file.exists():
            spec_data['spec'] = self._parse_spec_file(spec_file)
        
        # Load tasks.md (if exists)
        tasks_file = self.feature_path / 'tasks.md'
        if tasks_file.exists():
            spec_data['tasks'] = self._parse_tasks_file(tasks_file)
        
        # Load plan.md (if exists)  
        plan_file = self.feature_path / 'plan.md'
        if plan_file.exists():
            spec_data['plan'] = self._parse_plan_file(plan_file)
            
        return spec_data
    
    def _parse_spec_file(self, spec_file: Path) -> Dict[str, Any]:
        """Parse spec.md file for user stories and requirements"""
        content = spec_file.read_text()
        
        spec_data = {
            'title': self._extract_title(content),
            'description': self._extract_description(content),
            'user_stories': self._extract_user_stories(content),
            'requirements': self._extract_requirements(content),
            'success_criteria': self._extract_success_criteria(content)
        }
        
        return spec_data
    
    def _parse_tasks_file(self, tasks_file: Path) -> Dict[str, Any]:
        """Parse tasks.md file for task breakdown"""
        content = tasks_file.read_text()
        
        return {
            'phases': self._extract_task_phases(content),
            'tasks': self._extract_tasks(content)
        }
    
    def _parse_plan_file(self, plan_file: Path) -> Dict[str, Any]:
        """Parse plan.md file for technical context"""
        content = plan_file.read_text()
        
        return {
            'technical_context': self._extract_technical_context(content),
            'architecture': self._extract_architecture(content)
        }
    
    def _extract_title(self, content: str) -> str:
        """Extract feature title from spec content"""
        match = re.search(r'^# Feature Specification: (.+)$', content, re.MULTILINE)
        return match.group(1) if match else f"Feature {self.feature_number}"
    
    def _extract_description(self, content: str) -> str:
        """Extract feature description from input section"""
        match = re.search(r'\*\*Input\*\*: User description: "([^"]+)"', content)
        if match:
            return match.group(1)
        
        # Fallback to first paragraph after title
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('# Feature Specification:'):
                # Look for description in next few lines
                for j in range(i+1, min(i+10, len(lines))):
                    if lines[j].strip() and not lines[j].startswith('**'):
                        return lines[j].strip()
        
        return f"Feature specification for {self.feature_name}"
    
    def _extract_user_stories(self, content: str) -> List[Dict[str, Any]]:
        """Extract user stories with priorities from spec content"""
        stories = []
        
        # Pattern to match user story sections
        story_pattern = r'### User Story \d+ - (.+?) \(Priority: (P\d+)\)\s*\n(.*?)(?=\n### |$)'
        matches = re.findall(story_pattern, content, re.DOTALL)
        
        for i, (title, priority, story_content) in enumerate(matches, 1):
            # Extract acceptance scenarios
            acceptance_scenarios = self._extract_acceptance_scenarios(story_content)
            
            # Extract rationale (why this priority)
            rationale_match = re.search(r'\*\*Why this priority\*\*: (.+?)(?=\n\*\*|\n\n|$)', story_content, re.DOTALL)
            rationale = rationale_match.group(1).strip() if rationale_match else ""
            
            # Extract independent test description
            test_match = re.search(r'\*\*Independent Test\*\*: (.+?)(?=\n\*\*|\n\n|$)', story_content, re.DOTALL)
            independent_test = test_match.group(1).strip() if test_match else ""
            
            story = {
                'id': f'US{i}',
                'title': title.strip(),
                'priority': priority,
                'description': story_content.split('**Why this priority**')[0].strip(),
                'rationale': rationale,
                'independent_test': independent_test,
                'acceptance_scenarios': acceptance_scenarios
            }
            stories.append(story)
        
        return stories
    
    def _extract_acceptance_scenarios(self, story_content: str) -> List[str]:
        """Extract Given/When/Then scenarios from story content"""
        scenarios = []
        
        # Find acceptance scenarios section
        scenarios_match = re.search(r'\*\*Acceptance Scenarios\*\*:\s*\n(.*?)(?=\n\*\*|\n---|\n###|$)', story_content, re.DOTALL)
        if scenarios_match:
            scenarios_text = scenarios_match.group(1)
            
            # Extract numbered scenarios with Given/When/Then format
            scenario_pattern = r'\d+\.\s+\*\*Given\*\*\s+(.+?)\s+\*\*When\*\*\s+(.+?)\s+\*\*Then\*\*\s+(.+?)(?=\n\d+\.|\n\n|$)'
            scenario_matches = re.findall(scenario_pattern, scenarios_text, re.DOTALL)
            
            for given, when, then in scenario_matches:
                scenario = f"Given {given.strip()}, When {when.strip()}, Then {then.strip()}"
                scenarios.append(scenario)
        
        return scenarios
    
    def _extract_requirements(self, content: str) -> List[Dict[str, str]]:
        """Extract functional requirements from spec content"""
        requirements = []
        
        # Pattern to match FR-XXX requirements
        req_pattern = r'- \*\*FR-(\d+)\*\*: (.+?)(?=\n- \*\*FR-|\n\n|\n###|$)'
        matches = re.findall(req_pattern, content, re.DOTALL)
        
        for req_id, req_text in matches:
            requirements.append({
                'id': f'FR-{req_id}',
                'description': req_text.strip()
            })
        
        return requirements
    
    def _extract_success_criteria(self, content: str) -> List[str]:
        """Extract success criteria from spec content"""
        criteria = []
        
        # Pattern to match SC-XXX criteria
        sc_pattern = r'- \*\*SC-(\d+)\*\*: (.+?)(?=\n- \*\*SC-|\n\n|\n###|$)'
        matches = re.findall(sc_pattern, content, re.DOTALL)
        
        for sc_id, sc_text in matches:
            criteria.append(sc_text.strip())
        
        return criteria
    
    def _extract_task_phases(self, content: str) -> List[str]:
        """Extract task phases from tasks.md"""
        phases = []
        
        # Pattern to match phase headers
        phase_pattern = r'## Phase \d+: (.+?)(?=\n\n|\n##|$)'
        matches = re.findall(phase_pattern, content, re.MULTILINE)
        
        return [phase.strip() for phase in matches]
    
    def _extract_tasks(self, content: str) -> List[Dict[str, Any]]:
        """Extract individual tasks from tasks.md"""
        tasks = []
        
        # Pattern to match task items
        task_pattern = r'- \[.\] (T\d+)(?: \[P\])? (?:\[(\w+)\])? (.+?)(?=\n- \[|\n\n|\n##|$)'
        matches = re.findall(task_pattern, content, re.DOTALL)
        
        for task_id, story_ref, description in matches:
            task = {
                'id': task_id,
                'description': description.strip(),
                'story_reference': story_ref or None,
                'parallel': '[P]' in content.split(task_id)[0].split('\n')[-1]
            }
            tasks.append(task)
        
        return tasks
    
    def _extract_technical_context(self, content: str) -> Dict[str, str]:
        """Extract technical context from plan.md"""
        context = {}
        
        # Extract language/version
        lang_match = re.search(r'\*\*Language/Version\*\*: (.+)', content)
        if lang_match:
            context['language'] = lang_match.group(1).strip()
        
        # Extract dependencies
        deps_match = re.search(r'\*\*Primary Dependencies\*\*: (.+)', content)
        if deps_match:
            context['dependencies'] = deps_match.group(1).strip()
        
        return context
    
    def _extract_architecture(self, content: str) -> Dict[str, str]:
        """Extract architecture info from plan.md"""
        return {}  # Placeholder for architecture extraction
    
    def generate_epic(self, spec_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate JIRA epic from spec data"""
        spec = spec_data.get('spec', {})
        
        epic = {
            'key': f"{self.jira_config['project_key']}-{self.feature_number}",
            'summary': spec.get('title', f"Feature {self.feature_number}"),
            'description': self._format_epic_description(spec),
            'issueType': self.jira_config['issue_types']['epic'],
            'priority': 'High',
            'labels': ['speckit-generated', 'epic', self.feature_name],
            'components': ['Platform'],
            'customFields': {
                'businessValue': 'High',
                'targetRelease': 'TBD',
                'estimatedEffort': 'TBD'
            }
        }
        
        return epic
    
    def _format_epic_description(self, spec: Dict[str, Any]) -> str:
        """Format epic description with spec details"""
        description = spec.get('description', '')
        
        # Add success criteria if available
        success_criteria = spec.get('success_criteria', [])
        if success_criteria:
            description += "\n\n**Success Criteria:**\n"
            for criterion in success_criteria:
                description += f"- {criterion}\n"
        
        # Add related documentation
        description += f"\n\n**Related Documentation:**\n"
        description += f"- Specification: specs/{self.feature_name}/spec.md\n"
        description += f"- Implementation Plan: specs/{self.feature_name}/plan.md\n"
        description += f"- Task Breakdown: specs/{self.feature_name}/tasks.md\n"
        
        return description
    
    def generate_stories(self, spec_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate JIRA stories from user stories"""
        spec = spec_data.get('spec', {})
        user_stories = spec.get('user_stories', [])
        
        stories = []
        for story in user_stories:
            jira_story = {
                'key': f"{self.jira_config['project_key']}-{self.feature_number}-{story['id']}",
                'summary': f"{story['title']} ({story['priority']})",
                'description': self._format_story_description(story),
                'issueType': self.jira_config['issue_types']['story'],
                'priority': self.jira_config['priorities'].get(story['priority'], 'Medium'),
                'labels': ['speckit-generated', 'user-story', story['priority'].lower()],
                'components': ['Platform'],
                'customFields': {
                    'storyPoints': self._estimate_story_points(story),
                    'acceptanceCriteria': '\n'.join(story['acceptance_scenarios'])
                }
            }
            stories.append(jira_story)
        
        return stories
    
    def _format_story_description(self, story: Dict[str, Any]) -> str:
        """Format story description with all details"""
        description = story['description']
        
        if story['rationale']:
            description += f"\n\n**Priority Rationale:** {story['rationale']}"
        
        if story['independent_test']:
            description += f"\n\n**Independent Testing:** {story['independent_test']}"
        
        if story['acceptance_scenarios']:
            description += "\n\n**Acceptance Scenarios:**\n"
            for scenario in story['acceptance_scenarios']:
                description += f"- {scenario}\n"
        
        description += "\n\n**Definition of Done:**\n"
        description += "- [ ] Contract specifications defined\n"
        description += "- [ ] Implementation complete\n" 
        description += "- [ ] Integration tests passing\n"
        description += "- [ ] Documentation updated\n"
        description += "- [ ] Code reviewed and approved\n"
        
        return description
    
    def _estimate_story_points(self, story: Dict[str, Any]) -> int:
        """Estimate story points based on priority and complexity"""
        priority_points = {'P1': 8, 'P2': 5, 'P3': 3}
        base_points = priority_points.get(story['priority'], 3)
        
        # Adjust based on number of acceptance scenarios
        scenario_count = len(story['acceptance_scenarios'])
        if scenario_count > 3:
            base_points += 2
        elif scenario_count > 5:
            base_points += 5
        
        return min(base_points, 13)  # Cap at 13 points
    
    def generate_tasks(self, spec_data: Dict[str, Any], stories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate JIRA tasks from spec tasks"""
        tasks_data = spec_data.get('tasks', {})
        spec_tasks = tasks_data.get('tasks', [])
        
        jira_tasks = []
        
        for task in spec_tasks:
            # Find parent story
            parent_story = self._find_parent_story(task, stories)
            
            jira_task = {
                'key': f"{self.jira_config['project_key']}-{self.feature_number}-{task['id']}",
                'summary': self._format_task_summary(task),
                'description': self._format_task_description(task),
                'issueType': self.jira_config['issue_types']['task'],
                'priority': self._determine_task_priority(task, parent_story),
                'parentStory': parent_story['key'] if parent_story else None,
                'labels': self._generate_task_labels(task),
                'components': ['Platform'],
                'customFields': {
                    'taskPhase': self._determine_task_phase(task),
                    'estimatedHours': self._estimate_task_hours(task),
                    'technicalComplexity': self._assess_complexity(task),
                    'parallelExecution': task.get('parallel', False)
                }
            }
            jira_tasks.append(jira_task)
        
        return jira_tasks
    
    def _find_parent_story(self, task: Dict[str, Any], stories: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find the parent story for a task"""
        story_ref = task.get('story_reference')
        if story_ref:
            for story in stories:
                if story_ref in story['key']:
                    return story
        return None
    
    def _format_task_summary(self, task: Dict[str, Any]) -> str:
        """Format task summary"""
        description = task['description']
        return description.split('.')[0][:100]  # First sentence, max 100 chars
    
    def _format_task_description(self, task: Dict[str, Any]) -> str:
        """Format detailed task description"""
        description = f"**Task ID:** {task['id']}\n\n"
        description += f"**Description:** {task['description']}\n\n"
        
        if task.get('parallel'):
            description += "**Parallel Execution:** This task can be executed in parallel with other tasks.\n\n"
        
        description += "**Contract Requirements:**\n"
        description += "- [ ] YAML schema validation\n"
        description += "- [ ] API contract compliance\n" 
        description += "- [ ] Integration contract adherence\n\n"
        
        description += "**Acceptance Criteria:**\n"
        description += "- [ ] Implementation matches task specification\n"
        description += "- [ ] All dependencies resolved\n"
        description += "- [ ] Integration tests passing\n"
        description += "- [ ] Code follows constitutional principles\n"
        
        return description
    
    def _determine_task_priority(self, task: Dict[str, Any], parent_story: Optional[Dict[str, Any]]) -> str:
        """Determine task priority based on parent story and task type"""
        if parent_story:
            return parent_story['priority']
        
        # Default priority based on task ID (lower numbers = higher priority)
        task_num = int(re.findall(r'\d+', task['id'])[0])
        if task_num <= 10:
            return 'Highest'
        elif task_num <= 50:
            return 'High' 
        else:
            return 'Medium'
    
    def _generate_task_labels(self, task: Dict[str, Any]) -> List[str]:
        """Generate labels for task based on content"""
        labels = ['speckit-task']
        
        description = task['description'].lower()
        
        # Add technology labels
        if any(tech in description for tech in ['api', 'rest', 'endpoint']):
            labels.append('backend')
        if any(tech in description for tech in ['ui', 'frontend', 'screen', 'interface']):
            labels.append('frontend')
        if any(tech in description for tech in ['database', 'db', 'migration', 'schema']):
            labels.append('database')
        if any(tech in description for tech in ['test', 'testing']):
            labels.append('testing')
        
        # Add phase labels
        if 'setup' in description or 'initialization' in description:
            labels.append('setup')
        if 'implementation' in description:
            labels.append('implementation')
        
        if task.get('parallel'):
            labels.append('parallel')
        
        return labels
    
    def _determine_task_phase(self, task: Dict[str, Any]) -> str:
        """Determine which development phase the task belongs to"""
        description = task['description'].lower()
        
        if any(keyword in description for keyword in ['setup', 'init', 'create project', 'structure']):
            return 'Setup'
        elif any(keyword in description for keyword in ['test', 'testing']):
            return 'Testing'
        elif any(keyword in description for keyword in ['document', 'readme', 'guide']):
            return 'Documentation'
        else:
            return 'Implementation'
    
    def _estimate_task_hours(self, task: Dict[str, Any]) -> int:
        """Estimate task hours based on complexity"""
        description = task['description'].lower()
        
        # Base estimate
        hours = 4
        
        # Adjust based on keywords
        if any(keyword in description for keyword in ['create', 'implement', 'develop']):
            hours = 8
        if any(keyword in description for keyword in ['setup', 'configure', 'install']):
            hours = 2
        if any(keyword in description for keyword in ['integration', 'api', 'service']):
            hours += 4
        if any(keyword in description for keyword in ['complex', 'algorithm', 'optimization']):
            hours += 6
        
        return min(hours, 40)  # Cap at 40 hours
    
    def _assess_complexity(self, task: Dict[str, Any]) -> str:
        """Assess technical complexity of task"""
        description = task['description'].lower()
        
        high_complexity_keywords = ['integration', 'algorithm', 'optimization', 'security', 'performance']
        medium_complexity_keywords = ['api', 'service', 'database', 'validation']
        
        if any(keyword in description for keyword in high_complexity_keywords):
            return 'High'
        elif any(keyword in description for keyword in medium_complexity_keywords):
            return 'Medium'
        else:
            return 'Low'
    
    def generate_jira_draft(self) -> Dict[str, Any]:
        """Generate complete JIRA draft YAML"""
        print(f"Generating JIRA draft for feature: {self.feature_name}")
        
        # Load spec data
        spec_data = self.load_spec_files()
        
        # Generate JIRA work items
        epic = self.generate_epic(spec_data)
        stories = self.generate_stories(spec_data)
        tasks = self.generate_tasks(spec_data, stories)
        
        # Build complete JIRA draft structure
        jira_draft = {
            'metadata': {
                'generated': datetime.now().isoformat(),
                'feature': self.feature_name,
                'feature_path': str(self.feature_path),
                'generator_version': '1.0.0'
            },
            'project': {
                'key': self.jira_config['project_key'],
                'name': 'Spec-Kit Generated Features'
            },
            'epic': epic,
            'stories': stories,
            'tasks': tasks,
            'workflow': {
                'statusMapping': {
                    'To Do': {'speckit': 'not-started'},
                    'In Planning': {'speckit': 'design-phase'},
                    'In Progress': {'speckit': 'implementation'},
                    'Code Review': {'speckit': 'review-phase'},
                    'Testing': {'speckit': 'integration-testing'},
                    'Done': {'speckit': 'completed'},
                    'Blocked': {'speckit': 'blocked'}
                }
            }
        }
        
        return jira_draft
    
    def save_draft(self, jira_draft: Dict[str, Any]) -> Path:
        """Save JIRA draft to YAML file"""
        output_path = self.repo_root / 'jira' / f'{self.feature_name}-draft.yaml'
        
        # Ensure jira directory exists
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w') as f:
            yaml.safe_dump(jira_draft, f, default_flow_style=False, sort_keys=False, width=120)
        
        print(f"JIRA draft saved to: {output_path}")
        return output_path

def main():
    parser = argparse.ArgumentParser(description='Generate JIRA draft from Spec-Kit feature')
    parser.add_argument('feature_path', nargs='?', help='Path to feature directory (auto-detects if not provided)')
    parser.add_argument('--output', '-o', help='Output file path (default: jira/{feature}-draft.yaml)')
    
    args = parser.parse_args()
    
    try:
        # Generate JIRA draft
        generator = JiraDraftGenerator(args.feature_path)
        jira_draft = generator.generate_jira_draft()
        
        # Save to file
        output_path = generator.save_draft(jira_draft)
        
        # Summary
        epic = jira_draft['epic']
        stories = jira_draft['stories'] 
        tasks = jira_draft['tasks']
        
        print(f"\n✅ JIRA Draft Generated Successfully!")
        print(f"   Epic: {epic['summary']}")
        print(f"   Stories: {len(stories)} user stories")
        print(f"   Tasks: {len(tasks)} development tasks")
        print(f"   Output: {output_path}")
        print(f"\nNext steps:")
        print(f"1. Review and edit: {output_path}")
        print(f"2. Push to JIRA: python scripts/push_jira.py {output_path}")
        
    except Exception as e:
        print(f"❌ Error generating JIRA draft: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()