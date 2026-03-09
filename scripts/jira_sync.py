import os
import requests
import json
import tempfile
import shutil
import copy
from pathlib import Path

# ---------------------------------------
# Configuration
# ---------------------------------------

JIRA_URL = os.environ.get("JIRA_URL", "").rstrip("/")
EMAIL = os.environ.get("JIRA_EMAIL")
TOKEN = os.environ.get("JIRA_TOKEN")
PROJECT = os.environ.get("JIRA_PROJECT")

# GitHub repository configuration - auto-detect from GitHub Actions or manual config
def get_github_config():
    """Auto-detect GitHub configuration from GitHub Actions environment or use manual config"""
    
    # Check if running in GitHub Actions
    if os.environ.get("GITHUB_ACTIONS") == "true":
        # Auto-detect from GitHub Actions environment
        github_server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
        github_repo = os.environ.get("GITHUB_REPOSITORY")  # format: "owner/repo"
        
        # Determine branch - try multiple sources
        github_branch = (
            os.environ.get("GITHUB_REF_NAME") or  # Simple branch/tag name
            os.environ.get("GITHUB_HEAD_REF") or  # For pull requests
            os.environ.get("GITHUB_REF", "").replace("refs/heads/", "").replace("refs/tags/", "") or
            "main"
        )
        
        if github_repo:
            repo_url = f"{github_server}/{github_repo}"
            print(f"🔍 Auto-detected GitHub Actions environment:")
            print(f"   Repository: {github_repo}")
            print(f"   Branch: {github_branch}")
            print(f"   Server: {github_server}")
            return repo_url, github_branch
        else:
            print(f"⚠️  WARNING: In GitHub Actions but GITHUB_REPOSITORY not found")
    
    # Fallback to manual configuration
    repo_url = os.environ.get("GITHUB_REPO_URL", "https://github.com/your-org/your-repo")
    branch = os.environ.get("GITHUB_BRANCH", "main")
    
    # Check if using default values
    if repo_url == "https://github.com/your-org/your-repo":
        print(f"⚠️  WARNING: Using default GitHub repo URL. Set GITHUB_REPO_URL environment variable.")
    
    return repo_url, branch

GITHUB_REPO_URL, GITHUB_BRANCH = get_github_config()

# Issue type mappings (can be overridden via environment variables)
ISSUE_TYPE_EPIC = os.environ.get("ISSUE_TYPE_EPIC", "Epic")
ISSUE_TYPE_STORY = os.environ.get("ISSUE_TYPE_STORY", "Story")
ISSUE_TYPE_TASK = os.environ.get("ISSUE_TYPE_TASK", "Sub-task")
ISSUE_TYPE_BUG = os.environ.get("ISSUE_TYPE_BUG", "Bug")

DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"

# Validate configuration
if not DRY_RUN:
    missing = []
    if not JIRA_URL:
        missing.append("JIRA_URL")
    if not EMAIL:
        missing.append("JIRA_EMAIL")
    if not TOKEN:
        missing.append("JIRA_TOKEN")
    if not PROJECT:
        missing.append("JIRA_PROJECT")
    
    if missing:
        print(f"❌ ERROR: Missing required environment variables: {', '.join(missing)}")
        print(f"💡 JIRA_URL should be like: https://your-domain.atlassian.net")
        exit(1)
    
    print(f"✅ Configuration loaded:")
    print(f"   JIRA_URL: {JIRA_URL}")
    print(f"   PROJECT: {PROJECT}")
    print(f"   EMAIL: {EMAIL}")
    print(f"   GITHUB_REPO_URL: {GITHUB_REPO_URL}")
    print(f"   GITHUB_BRANCH: {GITHUB_BRANCH}")
    print(f"   GITHUB_ACTIONS: {os.environ.get('GITHUB_ACTIONS', 'false')}")

auth = (EMAIL, TOKEN)

# Determine the repository root directory
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent  # Go up one level from scripts/ to repo root
SPEC_FOLDER = REPO_ROOT / "specs"
TEMP_JSON_DIR = Path(tempfile.mkdtemp(prefix="jira_sync_"))
TEMPLATE_DIR = Path(__file__).parent / "templates"

# Validate specs folder and show initial structure
print(f"\n📂 SPECS FOLDER VALIDATION")
print(f"   Expected path: {SPEC_FOLDER.absolute()}")
if SPEC_FOLDER.exists():
    print(f"   ✅ Specs folder exists")
    # Count markdown files
    all_md = list(SPEC_FOLDER.glob("**/*.md"))
    spec_md = list(SPEC_FOLDER.glob("**/spec.md"))
    other_md = [f for f in all_md if f.name != "spec.md"]
    print(f"   📋 Found {len(spec_md)} epic specs (spec.md)")
    print(f"   📄 Found {len(other_md)} story specs (other .md files)")
    print(f"   📊 Total markdown files: {len(all_md)}")
else:
    print(f"   ⚠️  Specs folder does not exist!")
    print(f"   💡 Create the folder and add spec files to proceed")

# Performance optimizations - caching
_template_cache = {}
_issue_type_mapping = None
_field_mapping_cache = None

# Enhanced JSON-based JIRA field mapping
def get_field_mappings():
    """Load and cache JIRA field mappings from templates.json"""
    global _field_mapping_cache
    
    if _field_mapping_cache is None:
        templates_file = TEMPLATE_DIR / "templates.json"
        if templates_file.exists():
            with open(templates_file, 'r', encoding='utf-8') as f:
                all_templates = json.load(f)
                _field_mapping_cache = all_templates.get('field_mappings', {})
        else:
            _field_mapping_cache = {}
    
    return _field_mapping_cache

def get_available_fields(project_key, issue_type_name):
    """Get available fields for a specific project and issue type"""
    url = f"{JIRA_URL}/rest/api/3/issue/createmeta?projectKeys={project_key}&issuetypeNames={issue_type_name}&expand=projects.issuetypes.fields"
    
    try:
        response = requests.get(url, auth=auth, headers={"Content-Type": "application/json"})
        if response.ok:
            data = response.json()
            if data.get("projects") and len(data["projects"]) > 0:
                project = data["projects"][0]
                if project.get("issuetypes") and len(project["issuetypes"]) > 0:
                    issue_type = project["issuetypes"][0]
                    return list(issue_type.get("fields", {}).keys())
    except Exception as e:
        print(f"⚠️  Warning: Could not fetch available fields: {e}")
    
    return []

def validate_custom_fields(json_data, available_fields=None):
    """Validate and filter custom fields that are actually available in JIRA"""
    if not json_data.get('custom_fields') or available_fields is None:
        return {}
    
    field_mappings = get_field_mappings()
    default_mappings = {
        'business_value': 'customfield_10100',
        'technical_complexity': 'customfield_10101', 
        'category': 'customfield_10102',
        'time_estimate': 'customfield_10103',
        'epic_name': 'customfield_10011',
        'epic_link': 'customfield_10014'
    }
    
    # Merge default mappings with loaded mappings
    all_mappings = {**default_mappings, **field_mappings}
    
    valid_fields = {}
    skipped_fields = []
    
    for field_name, field_value in json_data['custom_fields'].items():
        if field_name in all_mappings and field_value:
            jira_field_id = all_mappings[field_name]
            if jira_field_id in available_fields:
                valid_fields[jira_field_id] = field_value
            else:
                skipped_fields.append(f"{field_name} ({jira_field_id})")
    
    if skipped_fields:
        print(f"     ⚠️  Skipped unavailable custom fields: {', '.join(skipped_fields)}")
    
    return valid_fields

def get_default_values():
    """Load default values from templates.json"""
    templates_file = TEMPLATE_DIR / "templates.json"
    if templates_file.exists():
        with open(templates_file, 'r', encoding='utf-8') as f:
            all_templates = json.load(f)
            return all_templates.get('default_values', {})
    return {}

# ---------------------------------------
# JIRA API
# ---------------------------------------

def markdown_to_adf(text):
    """Enhanced markdown to ADF conversion with proper formatting"""
    if not text or not text.strip():
        return {
            "version": 1,
            "type": "doc",
            "content": [{
                "type": "paragraph",
                "content": [{"type": "text", "text": ""}]
            }]
        }
    
    adf_content = []
    lines = text.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Skip empty lines between blocks
        if not stripped:
            i += 1
            continue
        
        # Headers (# ## ### etc)
        if stripped.startswith('#'):
            level = 0
            for char in stripped:
                if char == '#':
                    level += 1
                else:
                    break
            text_content = stripped[level:].strip()
            adf_content.append({
                "type": "heading",
                "attrs": {"level": min(level, 6)},
                "content": parse_inline_markdown(text_content)
            })
            i += 1
        
        # Horizontal rule (--- or ***)
        elif stripped in ('---', '***', '___'):
            adf_content.append({"type": "rule"})
            i += 1
        
        # Code blocks (```)
        elif stripped.startswith('```'):
            code_lines = []
            language = stripped[3:].strip()
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            i += 1  # Skip closing ```
            adf_content.append({
                "type": "codeBlock",
                "attrs": {"language": language or "text"},
                "content": [{"type": "text", "text": '\n'.join(code_lines)}]
            })
        
        # Bullet lists (- or *)
        elif stripped.startswith(('- ', '* ')):
            list_items = []
            while i < len(lines) and lines[i].strip().startswith(('- ', '* ')):
                item_text = lines[i].strip()[2:]
                list_items.append({
                    "type": "listItem",
                    "content": [{
                        "type": "paragraph",
                        "content": parse_inline_markdown(item_text)
                    }]
                })
                i += 1
            adf_content.append({
                "type": "bulletList",
                "content": list_items
            })
        
        # Regular paragraph
        else:
            para_lines = []
            while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(('#', '```', '>', '-', '*', '1.')):
                para_lines.append(lines[i].strip())
                i += 1
            
            if para_lines:
                para_text = ' '.join(para_lines)
                adf_content.append({
                    "type": "paragraph",
                    "content": parse_inline_markdown(para_text)
                })
    
    if not adf_content:
        adf_content = [{
            "type": "paragraph",
            "content": [{"type": "text", "text": text[:32000]}]
        }]
    
    return {
        "version": 1,
        "type": "doc",
        "content": adf_content
    }


def markdown_to_adf_original(text):
    """Original complex markdown to ADF conversion (kept as backup)"""
    if not text or not text.strip():
        return {
            "version": 1,
            "type": "doc",
            "content": [{
                "type": "paragraph",
                "content": [{"type": "text", "text": ""}]
            }]
        }
    
    adf_content = []
    lines = text.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Skip empty lines between blocks
        if not stripped:
            i += 1
            continue
        
        # Headers (# ## ### etc)
        if stripped.startswith('#'):
            level = 0
            for char in stripped:
                if char == '#':
                    level += 1
                else:
                    break
            text_content = stripped[level:].strip()
            adf_content.append({
                "type": "heading",
                "attrs": {"level": min(level, 6)},
                "content": parse_inline_markdown(text_content)
            })
            i += 1
        
        # Code blocks (```)
        elif stripped.startswith('```'):
            code_lines = []
            language = stripped[3:].strip()
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            i += 1  # Skip closing ```
            adf_content.append({
                "type": "codeBlock",
                "attrs": {"language": language or "text"},
                "content": [{"type": "text", "text": '\n'.join(code_lines)}]
            })
        
        # Blockquotes (>)
        elif stripped.startswith('>'):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                quote_lines.append(lines[i].strip()[1:].strip())
                i += 1
            adf_content.append({
                "type": "blockquote",
                "content": [{
                    "type": "paragraph",
                    "content": parse_inline_markdown(' '.join(quote_lines))
                }]
            })
        
        # Bullet lists (- or *)
        elif stripped.startswith(('- ', '* ')):
            list_items = []
            while i < len(lines) and lines[i].strip().startswith(('- ', '* ')):
                item_text = lines[i].strip()[2:]
                # Handle checkboxes
                if item_text.startswith('['):
                    checked = item_text[1] == 'x'
                    item_text = ('✓ ' if checked else '☐ ') + item_text[3:].strip()
                
                list_items.append({
                    "type": "listItem",
                    "content": [{
                        "type": "paragraph",
                        "content": parse_inline_markdown(item_text)
                    }]
                })
                i += 1
            adf_content.append({
                "type": "bulletList",
                "content": list_items
            })
        
        # Numbered lists (1. 2. etc)
        elif stripped and stripped[0].isdigit() and '. ' in stripped:
            list_items = []
            while i < len(lines):
                line_stripped = lines[i].strip()
                if line_stripped and line_stripped[0].isdigit() and '. ' in line_stripped:
                    item_text = line_stripped.split('. ', 1)[1]
                    list_items.append({
                        "type": "listItem",
                        "content": [{
                            "type": "paragraph",
                            "content": parse_inline_markdown(item_text)
                        }]
                    })
                    i += 1
                else:
                    break
            adf_content.append({
                "type": "orderedList",
                "content": list_items
            })
        
        # Horizontal rule (--- or ***)
        elif stripped in ('---', '***', '___'):
            adf_content.append({"type": "rule"})
            i += 1
        
        # Regular paragraph
        else:
            para_lines = []
            while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(('#', '```', '>', '-', '*', '1.')):
                para_lines.append(lines[i].strip())
                i += 1
            
            if para_lines:
                para_text = ' '.join(para_lines)
                adf_content.append({
                    "type": "paragraph",
                    "content": parse_inline_markdown(para_text)
                })
    
    if not adf_content:
        adf_content = [{
            "type": "paragraph",
            "content": [{"type": "text", "text": text[:32000]}]
        }]
    
    return {
        "version": 1,
        "type": "doc",
        "content": adf_content
    }


def parse_inline_markdown(text):
    """Enhanced inline markdown parsing for proper ADF formatting"""
    if not text:
        return [{"type": "text", "text": ""}]
    
    content = []
    i = 0
    current_text = ""
    
    while i < len(text):
        # Bold (**text** or __text__)
        if text[i:i+2] in ('**', '__'):
            if current_text:
                content.append({"type": "text", "text": current_text})
                current_text = ""
            
            marker = text[i:i+2]
            i += 2
            bold_text = ""
            while i < len(text) - 1:
                if text[i:i+2] == marker:
                    break
                bold_text += text[i]
                i += 1
            
            if bold_text:
                content.append({
                    "type": "text",
                    "text": bold_text,
                    "marks": [{"type": "strong"}]
                })
            i += 2
        
        # Italic (*text* or _text_)
        elif text[i] in ('*', '_') and (i == 0 or text[i-1] not in ('*', '_')):
            if current_text:
                content.append({"type": "text", "text": current_text})
                current_text = ""
            
            marker = text[i]
            i += 1
            italic_text = ""
            while i < len(text):
                if text[i] == marker and (i+1 >= len(text) or text[i+1] not in ('*', '_')):
                    break
                italic_text += text[i]
                i += 1
            
            if italic_text:
                content.append({
                    "type": "text",
                    "text": italic_text,
                    "marks": [{"type": "em"}]
                })
            i += 1
        
        # Inline code (`code`)
        elif text[i] == '`':
            if current_text:
                content.append({"type": "text", "text": current_text})
                current_text = ""
            
            i += 1
            code_text = ""
            while i < len(text) and text[i] != '`':
                code_text += text[i]
                i += 1
            
            if code_text:
                content.append({
                    "type": "text",
                    "text": code_text,
                    "marks": [{"type": "code"}]
                })
            i += 1
        
        # Links [text](url)
        elif text[i] == '[':
            if current_text:
                content.append({"type": "text", "text": current_text})
                current_text = ""
            
            i += 1
            link_text = ""
            while i < len(text) and text[i] != ']':
                link_text += text[i]
                i += 1
            
            i += 1  # Skip ]
            if i < len(text) and text[i] == '(':
                i += 1
                url = ""
                while i < len(text) and text[i] != ')':
                    url += text[i]
                    i += 1
                i += 1  # Skip )
                
                content.append({
                    "type": "text",
                    "text": link_text,
                    "marks": [{"type": "link", "attrs": {"href": url}}]
                })
            else:
                current_text += '[' + link_text + ']'
        
        # Regular text
        else:
            current_text += text[i]
            i += 1
    
    if current_text:
        content.append({"type": "text", "text": current_text})
    
    if not content:
        content = [{"type": "text", "text": ""}]
    
    return content


def parse_inline_markdown_original(text):
    """Original complex inline markdown parsing (kept as backup)"""
    if not text:
        return [{"type": "text", "text": ""}]
    
    content = []
    i = 0
    current_text = ""
    
    while i < len(text):
        # Bold (**text** or __text__)
        if text[i:i+2] in ('**', '__'):
            if current_text:
                content.append({"type": "text", "text": current_text})
                current_text = ""
            
            marker = text[i:i+2]
            i += 2
            bold_text = ""
            while i < len(text) - 1:
                if text[i:i+2] == marker:
                    break
                bold_text += text[i]
                i += 1
            
            if bold_text:
                content.append({
                    "type": "text",
                    "text": bold_text,
                    "marks": [{"type": "strong"}]
                })
            i += 2
        
        # Italic (*text* or _text_)
        elif text[i] in ('*', '_') and (i == 0 or text[i-1] not in ('*', '_')):
            if current_text:
                content.append({"type": "text", "text": current_text})
                current_text = ""
            
            marker = text[i]
            i += 1
            italic_text = ""
            while i < len(text):
                if text[i] == marker and (i+1 >= len(text) or text[i+1] not in ('*', '_')):
                    break
                italic_text += text[i]
                i += 1
            
            if italic_text:
                content.append({
                    "type": "text",
                    "text": italic_text,
                    "marks": [{"type": "em"}]
                })
            i += 1
        
        # Inline code (`code`)
        elif text[i] == '`':
            if current_text:
                content.append({"type": "text", "text": current_text})
                current_text = ""
            
            i += 1
            code_text = ""
            while i < len(text) and text[i] != '`':
                code_text += text[i]
                i += 1
            
            if code_text:
                content.append({
                    "type": "text",
                    "text": code_text,
                    "marks": [{"type": "code"}]
                })
            i += 1
        
        # Links [text](url)
        elif text[i] == '[':
            if current_text:
                content.append({"type": "text", "text": current_text})
                current_text = ""
            
            i += 1
            link_text = ""
            while i < len(text) and text[i] != ']':
                link_text += text[i]
                i += 1
            
            i += 1  # Skip ]
            if i < len(text) and text[i] == '(':
                i += 1
                url = ""
                while i < len(text) and text[i] != ')':
                    url += text[i]
                    i += 1
                i += 1  # Skip )
                
                content.append({
                    "type": "text",
                    "text": link_text,
                    "marks": [{"type": "link", "attrs": {"href": url}}]
                })
            else:
                current_text += '[' + link_text + ']'
        
        # Regular text
        else:
            current_text += text[i]
            i += 1
    
    if current_text:
        content.append({"type": "text", "text": current_text})
    
    if not content:
        content = [{"type": "text", "text": ""}]
    
    return content


def get_cached_template(issue_type):
    """Get cached template to avoid repeated file I/O"""
    if issue_type not in _template_cache:
        _template_cache[issue_type] = load_template(issue_type)
    return _template_cache[issue_type]


def load_template(issue_type):
    """Load JSON template for specific issue type from single templates file"""
    # Dynamic template mapping that adapts to actual issue types
    template_map = {
        ISSUE_TYPE_EPIC: "epic",
        ISSUE_TYPE_STORY: "story", 
        ISSUE_TYPE_TASK: "task",
        ISSUE_TYPE_BUG: "bug",
        "Sub-task": "subtask",
        "Subtask": "subtask",  # JIRA Subtask type
        "Task": "task",  # Standard Task type
        "Story": "story",  # Standard Story type
        "Epic": "epic",  # Standard Epic type
        "Bug": "bug"  # Standard Bug type
    }
    
    template_key = template_map.get(issue_type)
    
    # If no direct mapping found, try to infer from issue type name
    if not template_key:
        issue_lower = issue_type.lower()
        if 'epic' in issue_lower:
            template_key = "epic"
        elif 'story' in issue_lower:
            template_key = "story"
        elif 'bug' in issue_lower or 'defect' in issue_lower:
            template_key = "bug"
        elif 'task' in issue_lower or 'sub' in issue_lower:
            template_key = "task"
        else:
            template_key = "task"  # Default fallback
    
    templates_file = TEMPLATE_DIR / "templates.json"
    
    if not templates_file.exists():
        raise FileNotFoundError(f"Templates file not found: {templates_file}")
    
    with open(templates_file, 'r', encoding='utf-8') as f:
        all_templates = json.load(f)
    
    if 'templates' not in all_templates or template_key not in all_templates['templates']:
        # Fallback to task template if specific template not found
        if template_key != "task" and "task" in all_templates.get('templates', {}):
            print(f"⚠️  Template '{template_key}' not found, using 'task' template for {issue_type}")
            template_key = "task"
        else:
            raise ValueError(f"Template '{template_key}' not found in {templates_file}")
    
    return all_templates['templates'][template_key]


def create_json_for_item(title, description, file_path, issue_type, parent_key=None, **kwargs):
    """Create a JIRA item JSON file from unified template"""
    
    # Generate GitHub link - use relative path from repository root
    try:
        relative_path = file_path.relative_to(REPO_ROOT) if file_path.is_absolute() else file_path
    except ValueError:
        # Fallback if path is not within repo root
        relative_path = file_path.name
    github_link = f"{GITHUB_REPO_URL}/blob/{GITHUB_BRANCH}/{relative_path}"
    
    print(f"   🔗 Generated GitHub Link: {github_link}")
    
    # Load template data (cached)
    template_data = get_cached_template(issue_type)
    
    # Extract acceptance criteria from description if it's a story
    acceptance_criteria = ""
    if issue_type == ISSUE_TYPE_STORY and "## Acceptance Criteria" in description:
        parts = description.split("## Acceptance Criteria", 1)
        if len(parts) == 2:
            acceptance_criteria = parts[1].strip()
    
    # Extract bug-specific sections
    steps_to_reproduce = ""
    expected_behavior = ""
    actual_behavior = ""
    severity = kwargs.get('severity', 'Medium')
    environment = kwargs.get('environment', 'Development')
    
    if issue_type == ISSUE_TYPE_BUG:
        if "## Steps to Reproduce" in description:
            parts = description.split("## Steps to Reproduce", 1)
            if len(parts) == 2:
                remaining = parts[1]
                if "## Expected Behavior" in remaining:
                    steps_parts = remaining.split("## Expected Behavior", 1)
                    steps_to_reproduce = steps_parts[0].strip()
                    if len(steps_parts) == 2:
                        expected_parts = steps_parts[1]
                        if "## Actual Behavior" in expected_parts:
                            exp_parts = expected_parts.split("## Actual Behavior", 1)
                            expected_behavior = exp_parts[0].strip()
                            if len(exp_parts) == 2:
                                actual_behavior = exp_parts[1].strip()
                        else:
                            expected_behavior = expected_parts.strip()
                else:
                    steps_to_reproduce = remaining.strip()
    
    # Prepare template variables
    template_vars = {
        "SUMMARY": title[:255],  # JIRA summary limit
        "SOURCE_FILE": str(relative_path),
        "GITHUB_LINK": github_link,
        "CONTENT": description,
        "PARENT_KEY": parent_key or "",
        "EPIC_NAME": title[:255] if issue_type == ISSUE_TYPE_EPIC else "",
        "EPIC_DESCRIPTION": description[:500] if issue_type == ISSUE_TYPE_EPIC else "",
        "ACCEPTANCE_CRITERIA": acceptance_criteria,
        "TIME_ESTIMATE": kwargs.get('time_estimate', ''),
        "CATEGORY": kwargs.get('category', 'general'),
        "SEVERITY": severity,
        "ENVIRONMENT": environment,
        "STEPS_TO_REPRODUCE": steps_to_reproduce,
        "EXPECTED_BEHAVIOR": expected_behavior,
        "ACTUAL_BEHAVIOR": actual_behavior
    }
    
    # Deep copy template data and replace placeholders
    import copy
    json_data = copy.deepcopy(template_data)
    
    def replace_placeholders(obj):
        if isinstance(obj, dict):
            return {k: replace_placeholders(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [replace_placeholders(item) for item in obj]
        elif isinstance(obj, str):
            result = obj
            for key, value in template_vars.items():
                result = result.replace(f"{{{key}}}", str(value))
            return result
        else:
            return obj
    
    json_data = replace_placeholders(json_data)
    
    # Create temp JSON file
    safe_title = title[:50].replace(' ', '_').replace('/', '_').replace(':', '_')
    json_filename = f"{issue_type.lower().replace('-', '_')}_{safe_title}.json"
    json_file_path = TEMP_JSON_DIR / json_filename
    
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    print(f"  📝 Created JSON: {json_file_path.name} (from templates.json:{issue_type.lower()})")
    return json_file_path, json_data


def json_to_adf_description(json_data):
    """Convert JSON data to ADF description with enhanced GitHub link formatting"""
    desc = json_data['description']
    
    # Create enhanced description with proper ADF structure
    return {
        "version": 1,
        "type": "doc", 
        "content": [
            {
                "type": "panel",
                "attrs": {
                    "panelType": "info"
                },
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": "📋 Specification Source",
                                "marks": [{"type": "strong"}]
                            }
                        ]
                    },
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": "🔗 GitHub: "
                            },
                            {
                                "type": "text",
                                "text": desc['source_file'],
                                "marks": [{
                                    "type": "link",
                                    "attrs": {"href": desc['github_link']}
                                }]
                            }
                        ]
                    }
                ]
            },
            {
                "type": "rule"
            },
            *markdown_to_adf(desc['content'])["content"]
        ]
    }


def get_project_issue_types():
    """Fetch available issue types for the project"""
    url = f"{JIRA_URL}/rest/api/3/issue/createmeta?projectKeys={PROJECT}&expand=projects.issuetypes"
    
    response = requests.get(
        url,
        auth=auth,
        headers={"Content-Type": "application/json"}
    )
    
    if not response.ok:
        print(f"\n⚠️  WARNING: Could not fetch issue types: HTTP {response.status_code}")
        return []
    
    data = response.json()
    
    if data.get("projects"):
        project_data = data["projects"][0]
        issue_types = [it["name"] for it in project_data.get("issuetypes", [])]
        return issue_types
    
    return []

def validate_json_structure(json_data, json_file_path):
    """Validate JSON structure for JIRA issue creation"""
    required_fields = ['summary', 'issue_type', 'description']
    missing_fields = []
    
    for field in required_fields:
        if field not in json_data or not json_data[field]:
            missing_fields.append(field)
    
    if missing_fields:
        print(f"⚠️  WARNING: Missing required fields in {json_file_path.name}: {', '.join(missing_fields)}")
        return False
    
    # Validate description structure
    if isinstance(json_data['description'], dict):
        desc_required = ['source_file', 'github_link', 'content']
        desc_missing = [f for f in desc_required if f not in json_data['description']]
        if desc_missing:
            print(f"⚠️  WARNING: Missing description fields in {json_file_path.name}: {', '.join(desc_missing)}")
            return False
    
    return True


def create_issue_from_json(json_file_path, json_data):
    """Create JIRA issue from template-based JSON data"""
    
    # Validate JSON structure first
    if not validate_json_structure(json_data, json_file_path):
        print(f"❌ ERROR: Invalid JSON structure in {json_file_path.name}")
        return {"key": "ERROR"}
    
    summary = json_data['summary']
    issue_type = json_data['issue_type']
    parent_key = json_data.get('parent')
    
    # Remove empty parent key
    if parent_key == "":
        parent_key = None
    
    if DRY_RUN:
        print("\n--- DRY RUN ---")
        print("JSON FILE:", json_file_path.name)
        print("TYPE     :", issue_type)
        print("TITLE    :", summary)
        print("GITHUB   :", json_data['description']['github_link'])
        print("SOURCE   :", json_data['description']['source_file'])
        print("LABELS   :", json_data.get('labels', []))
        print("PRIORITY :", json_data.get('priority', 'Medium'))
        if json_data.get('severity'):
            print("SEVERITY :", json_data['severity'])
        if parent_key:
            print("PARENT   :", parent_key)
        if json_data.get('story_points'):
            print("POINTS   :", json_data['story_points'])
        print("---------------")
        return {"key": "DRYRUN"}

    # Get available fields for this project and issue type to validate custom fields
    available_fields = get_available_fields(PROJECT, issue_type)
    print(f"     🔍 Available fields fetched: {len(available_fields)} fields")

    # Convert JSON description to ADF with GitHub link
    adf_description = json_to_adf_description(json_data)

    # Build JIRA payload from JSON data
    payload = {
        "fields": {
            "project": {"key": PROJECT},
            "summary": summary,
            "description": adf_description,
            "issuetype": {"name": issue_type}
        }
    }

    # Add parent if specified
    if parent_key:
        payload["fields"]["parent"] = {"key": parent_key}
    
    # Add labels if specified
    if json_data.get('labels'):
        payload["fields"]["labels"] = json_data['labels']
    
    # Add priority if specified
    if json_data.get('priority'):
        payload["fields"]["priority"] = {"name": json_data['priority']}
    
    # Add story points for stories (if field exists in JIRA)
    if issue_type == ISSUE_TYPE_STORY and json_data.get('story_points'):
        # Note: Field name may vary by JIRA setup (customfield_XXXXX)
        # This is a common field name, may need customization
        payload["fields"]["customfield_10016"] = json_data['story_points']
    
    # Add components if specified
    if json_data.get('components'):
        payload["fields"]["components"] = [{"name": comp} for comp in json_data['components']]

    # Add validated custom fields (only those available in JIRA)
    valid_custom_fields = validate_custom_fields(json_data, available_fields)
    for field_id, field_value in valid_custom_fields.items():
        payload["fields"][field_id] = field_value
        print(f"     🔧 Added custom field: {field_id} = {field_value}")

    # Handle epic-specific fields with validation
    if issue_type == ISSUE_TYPE_EPIC and json_data.get('epic_name'):
        field_mappings = get_field_mappings()
        epic_name_field = field_mappings.get('epic_name', 'customfield_10011')
        if epic_name_field in available_fields:
            payload["fields"][epic_name_field] = json_data['epic_name']
            print(f"     🏆 Added epic name: {epic_name_field} = {json_data['epic_name']}")
        else:
            print(f"     ⚠️  Epic name field not available: {epic_name_field}")

    url = f"{JIRA_URL}/rest/api/3/issue"

    response = requests.post(
        url,
        json=payload,
        auth=auth,
        headers={"Content-Type": "application/json"}
    )

    if not response.ok:
        if response.status_code == 401:
            print(f"\n❌ ERROR: HTTP 401 - Unauthorized")
            print(f"🔑 JIRA Authentication Issue:")
            print(f"   - Check that JIRA_EMAIL is correct: {EMAIL}")
            print(f"   - Check that JIRA_TOKEN is valid and not expired")
            print(f"   - Verify you have permission to create issues in project: {PROJECT}")
            print(f"   - Token should be an API token from: https://id.atlassian.com/manage-profile/security/api-tokens")
        elif response.status_code == 400:
            print(f"\n❌ ERROR: HTTP 400 - Bad Request")
            print(f"🔧 JIRA Configuration Issue:")
            try:
                error_response = response.json()
                if "errors" in error_response:
                    print(f"   Field Errors:")
                    for field, error in error_response["errors"].items():
                        print(f"   - {field}: {error}")
                        if field.startswith('customfield_'):
                            print(f"     💡 This custom field may not exist or be configured for this project")
                if "errorMessages" in error_response:
                    print(f"   General Errors: {', '.join(error_response['errorMessages'])}")
            except:
                print(f"   Raw response: {response.text[:500]}")
            print(f"\n💡 TROUBLESHOOTING:")
            print(f"   - Check JIRA project configuration")
            print(f"   - Verify custom fields exist and are on appropriate screens")
            print(f"   - Use JIRA admin to check field permissions")
        else:
            print(f"\n❌ ERROR: HTTP {response.status_code}")
            print(f"URL: {url}")
            print(f"JSON: {json_file_path}")
            try:
                error_response = response.json()
                print(f"Response: {error_response}")
            except:
                print(f"Response: {response.text[:500]}")
        
        # Don't raise exception, return error info instead
        return {"key": "ERROR", "status_code": response.status_code, "error": response.text[:500]}

    data = response.json()
    issue_key = data.get('key')
    issue_url = f"{JIRA_URL}/browse/{issue_key}"
    
    print(f"  ✅ Created {issue_type}: {issue_key} (JSON: {json_file_path.name})")
    print(f"     🔗 JIRA URL: {issue_url}")
    print(f"     📋 GitHub: {json_data['description']['github_link']}")

    return data


# ---------------------------------------
# Markdown Parsing
# ---------------------------------------

def parse_markdown(file_path):

    with open(file_path) as f:
        lines = f.readlines()

    title = None
    tasks = []
    current_section = None
    section_items = []

    for line in lines:

        if line.startswith("# "):
            title = line.replace("#", "").strip()

        # Level 2 heading (##) - start new section
        elif line.startswith("## "):
            # Save previous section if it has items
            if current_section and section_items:
                section_desc = "\n".join(section_items)
                tasks.append({"title": current_section, "description": section_desc})
            
            # Start new section
            current_section = line.replace("##", "").strip()
            section_items = []

        # Bullet point - add to current section
        elif line.strip().startswith("- ") and current_section:
            section_items.append(line.strip())

    # Save last section
    if current_section and section_items:
        section_desc = "\n".join(section_items)
        tasks.append({"title": current_section, "description": section_desc})

    description = "".join(lines)

    return title, description, tasks


# ---------------------------------------
# Processing Specs
# ---------------------------------------

def process_specs():
    
    print(f"\n📁 Creating temp JSON directory: {TEMP_JSON_DIR}")
    
    # First, identify and log all specs that will be processed
    print(f"\n🔍 IDENTIFYING SPECS FOR JIRA GENERATION")
    print(f"   📂 Spec Folder: {SPEC_FOLDER.absolute()}")
    print("="*60)
    
    # Collect epic specs (spec.md files)
    epic_specs = list(sorted(SPEC_FOLDER.glob("**/spec.md")))
    print(f"\n📋 EPIC SPECS IDENTIFIED: {len(epic_specs)}")
    for i, spec_file in enumerate(epic_specs, 1):
        print(f"   {i}. {spec_file.relative_to(SPEC_FOLDER)}")
        print(f"      Full path: {spec_file.absolute()}")
    
    if not epic_specs:
        print("   ⚠️  No epic specs (spec.md) found!")
    
    # Collect story specs (other .md files)
    all_md_files = list(sorted(SPEC_FOLDER.glob("**/*.md")))
    story_specs = [f for f in all_md_files if f.name != "spec.md"]
    print(f"\n📄 STORY SPECS IDENTIFIED: {len(story_specs)}")
    for i, spec_file in enumerate(story_specs, 1):
        print(f"   {i}. {spec_file.relative_to(SPEC_FOLDER)}")
        print(f"      Full path: {spec_file.absolute()}")
    
    if not story_specs:
        print("   ⚠️  No story specs (non-spec.md files) found!")
    
    total_specs = len(epic_specs) + len(story_specs)
    print(f"\n📊 TOTAL SPECS TO PROCESS: {total_specs}")
    print("="*60)
    
    if total_specs == 0:
        print("❌ ERROR: No spec files found to process!")
        return
    
    epic_key = None
    epic_count = 0
    story_count = 0
    task_count = 0
    json_files_created = []
    error_count = 0
    errors_details = []

    try:
        # First pass: create epic from main spec.md
        for file in sorted(SPEC_FOLDER.glob("**/spec.md")):

            print(f"\n📋 Processing EPIC: {file}")
            print(f"   📍 Spec Location: {file.absolute()}")
            print(f"   🔗 GitHub Source: {GITHUB_REPO_URL}/blob/{GITHUB_BRANCH}/{file}")

            title, description, tasks = parse_markdown(file)
            
            # Create JSON for epic
            json_file, json_data = create_json_for_item(
                title, description, file, ISSUE_TYPE_EPIC
            )
            json_files_created.append(json_file)

            result = create_issue_from_json(json_file, json_data)

            if result.get("key") == "ERROR":
                error_count += 1
                errors_details.append(f"Epic: {title} - {result.get('error', 'Unknown error')}")
                print(f"  ❌ Failed to create epic, continuing with stories...")
            else:
                epic_key = result.get("key")
                epic_count += 1

        # Second pass: create stories and tasks from other files
        for file in sorted(SPEC_FOLDER.glob("**/*.md")):

            # Skip spec.md (already processed as epic)
            if file.name == "spec.md":
                continue

            print(f"\n📄 Processing STORY: {file}")
            print(f"   📍 Spec Location: {file.absolute()}")
            print(f"   🔗 GitHub Source: {GITHUB_REPO_URL}/blob/{GITHUB_BRANCH}/{file}")

            title, description, tasks = parse_markdown(file)
            
            # Create JSON for story
            json_file, json_data = create_json_for_item(
                title, description, file, ISSUE_TYPE_STORY, epic_key
            )
            json_files_created.append(json_file)

            result = create_issue_from_json(json_file, json_data)

            if result.get("key") == "ERROR":
                error_count += 1
                errors_details.append(f"Story: {title} - {result.get('error', 'Unknown error')}")
                print(f"  ❌ Failed to create story, continuing with tasks...")
                story_key = None
            else:
                story_key = result.get("key")
                story_count += 1

            # create subtasks
            for task in tasks:
                
                # Determine task category and time estimate from content
                task_category = "general"
                time_estimate = ""
                
                if isinstance(task, dict):
                    task_title = task["title"]
                    task_desc = task["description"]
                    
                    # Categorize based on keywords
                    if any(keyword in task_title.lower() for keyword in ['test', 'testing', 'verify']):
                        task_category = "testing"
                        time_estimate = "2h"
                    elif any(keyword in task_title.lower() for keyword in ['api', 'endpoint', 'service']):
                        task_category = "backend"
                        time_estimate = "4h"
                    elif any(keyword in task_title.lower() for keyword in ['ui', 'frontend', 'component']):
                        task_category = "frontend"
                        time_estimate = "3h"
                    elif any(keyword in task_title.lower() for keyword in ['doc', 'documentation']):
                        task_category = "documentation"
                        time_estimate = "1h"
                    
                    # Structured task with title and description
                    task_json_file, task_json_data = create_json_for_item(
                        task_title, task_desc, file, "Task", None,  # No parent - flat structure
                        category=task_category, time_estimate=time_estimate
                    )
                else:
                    # Simple task (backward compatibility)
                    task_title = str(task)
                    
                    # Basic categorization for simple tasks
                    if any(keyword in task_title.lower() for keyword in ['test', 'testing']):
                        task_category = "testing"
                    
                    task_json_file, task_json_data = create_json_for_item(
                        task_title, task_title, file, "Task", None,  # No parent - flat structure
                        category=task_category, time_estimate="2h"
                    )
                
                json_files_created.append(task_json_file)
                result = create_issue_from_json(task_json_file, task_json_data)
                
                if result.get("key") == "ERROR":
                    error_count += 1
                    errors_details.append(f"Task: {task_title} - {result.get('error', 'Unknown error')}")
                else:
                    task_count += 1

        # Print summary
        print("\n" + "="*60)
        print("📊 JIRA SYNC SUMMARY")
        print("="*60)
        print(f"  Epics created:     {epic_count}")
        print(f"  Stories created:   {story_count}")
        print(f"  Subtasks created:  {task_count}")
        print(f"  JSON files:        {len(json_files_created)}")
        print(f"  Errors encountered: {error_count}")
        print(f"  SUCCESS RATE:      {((epic_count + story_count + task_count) / max(1, epic_count + story_count + task_count + error_count) * 100):.1f}%")
        print(f"  TOTAL ISSUES:      {epic_count + story_count + task_count}")
        print(f"  TEMP JSON DIR:     {TEMP_JSON_DIR}")
        print("="*60)
        
        if error_count > 0:
            print(f"\n⚠️  ERRORS SUMMARY ({error_count} failures):")
            for i, error in enumerate(errors_details[:5], 1):  # Show first 5 errors
                print(f"   {i}. {error[:100]}..." if len(error) > 100 else f"   {i}. {error}")
            if len(errors_details) > 5:
                print(f"   ... and {len(errors_details) - 5} more errors")
            print(f"\n💡 Most errors are likely due to custom field configuration.")
            print(f"   Consider updating the JSON templates to match your JIRA setup.")
        
        if not DRY_RUN:
            print(f"\n💡 JSON files preserved for debugging in: {TEMP_JSON_DIR}")
            print(f"   Remove with: rm -rf {TEMP_JSON_DIR}")
    
    except Exception as e:
        print(f"\n❌ ERROR during processing: {e}")
        raise
    finally:
        if DRY_RUN:
            # Clean up temp directory in dry run
            print(f"\n🧹 Cleaning up temp directory: {TEMP_JSON_DIR}")
            shutil.rmtree(TEMP_JSON_DIR, ignore_errors=True)


# ---------------------------------------
# Preview Hierarchy
# ---------------------------------------

def preview_structure():

    print("\n==============================")
    print("JIRA STRUCTURE PREVIEW")
    print("==============================")
    
    # First, identify and log all specs that will be processed
    print(f"\n🔍 IDENTIFYING SPECS FOR PREVIEW")
    print(f"   📂 Spec Folder: {SPEC_FOLDER.absolute()}")
    print("="*50)
    
    # Collect epic specs (spec.md files)
    epic_specs = list(sorted(SPEC_FOLDER.glob("**/spec.md")))
    print(f"\n📋 EPIC SPECS IDENTIFIED: {len(epic_specs)}")
    for i, spec_file in enumerate(epic_specs, 1):
        print(f"   {i}. {spec_file.relative_to(SPEC_FOLDER)}")
    
    # Collect story specs (other .md files)
    all_md_files = list(sorted(SPEC_FOLDER.glob("**/*.md")))
    story_specs = [f for f in all_md_files if f.name != "spec.md"]
    print(f"\n📄 STORY SPECS IDENTIFIED: {len(story_specs)}")
    for i, spec_file in enumerate(story_specs, 1):
        print(f"   {i}. {spec_file.relative_to(SPEC_FOLDER)}")
    
    total_specs = len(epic_specs) + len(story_specs)
    print(f"\n📊 TOTAL SPECS FOR PREVIEW: {total_specs}")
    print("="*50)
    
    if total_specs == 0:
        print("❌ ERROR: No spec files found to preview!")
        return

    epic_count = 0
    story_count = 0
    task_count = 0

    # First: show epic from spec.md
    for file in sorted(SPEC_FOLDER.glob("**/spec.md")):

        title, description, tasks = parse_markdown(file)
        print("\nEPIC:", title)
        epic_count += 1

    # Then: show stories and tasks from other files
    for file in sorted(SPEC_FOLDER.glob("**/*.md")):

        if file.name == "spec.md":
            continue

        title, description, tasks = parse_markdown(file)

        print("  STORY:", title)
        story_count += 1

        for task in tasks:
            if isinstance(task, dict):
                print("     TASK:", task["title"])
            else:
                print("     TASK:", task)
            task_count += 1

    # Print summary
    print("\n" + "="*50)
    print("📊 PREVIEW SUMMARY")
    print("="*50)
    print(f"  Epics:    {epic_count}")
    print(f"  Stories:  {story_count}")
    print(f"  Subtasks: {task_count}")
    print(f"  TOTAL:    {epic_count + story_count + task_count}")
    print("="*50)


# ---------------------------------------
# Main
# ---------------------------------------

def main():
    # Declare global variables at the start of function
    global ISSUE_TYPE_STORY, ISSUE_TYPE_TASK, ISSUE_TYPE_BUG

    print(f"\n🚀 STARTING JIRA SYNC (Enhanced JSON Mode)")
    print(f"   Mode: {'DRY RUN (Preview Only)' if DRY_RUN else 'LIVE MODE (Will Create Issues)'}")
    print(f"   Format: JSON templates and data processing")
    
    # Perform early spec discovery for logging
    if SPEC_FOLDER.exists():
        epic_specs = list(SPEC_FOLDER.glob("**/spec.md"))
        story_specs = [f for f in SPEC_FOLDER.glob("**/*.md") if f.name != "spec.md"]
        print(f"   📋 Epic specs found: {len(epic_specs)}")
        print(f"   📄 Story specs found: {len(story_specs)}")
        print(f"   📊 Total specs to process: {len(epic_specs) + len(story_specs)}")
    else:
        print(f"   ⚠️  Specs folder not found: {SPEC_FOLDER.absolute()}")

    if DRY_RUN:
        preview_structure()
    else:
        print(f"\n🔍 Fetching available issue types...")
        available_types = get_project_issue_types()
        if available_types:
            print(f"   Available: {', '.join(available_types)}")
            
            # Create flexible issue type mapping with fallbacks
            issue_type_mapping = {
                'epic': ISSUE_TYPE_EPIC,
                'story': ISSUE_TYPE_STORY,
                'task': ISSUE_TYPE_TASK,
                'bug': ISSUE_TYPE_BUG
            }
            
            # Check and apply fallbacks for missing types
            fallbacks_applied = []
            
            # Story fallback: Story -> Task -> Epic
            if ISSUE_TYPE_STORY not in available_types:
                if 'Task' in available_types:
                    issue_type_mapping['story'] = 'Task'
                    fallbacks_applied.append(f"Story ({ISSUE_TYPE_STORY}) → Task")
                elif ISSUE_TYPE_EPIC in available_types:
                    issue_type_mapping['story'] = ISSUE_TYPE_EPIC
                    fallbacks_applied.append(f"Story ({ISSUE_TYPE_STORY}) → {ISSUE_TYPE_EPIC}")
            
            # Task fallback: Sub-task -> Task -> Story
            if ISSUE_TYPE_TASK not in available_types:
                if 'Task' in available_types:
                    issue_type_mapping['task'] = 'Task'
                    fallbacks_applied.append(f"Sub-task ({ISSUE_TYPE_TASK}) → Task")
                elif ISSUE_TYPE_STORY in available_types:
                    issue_type_mapping['task'] = ISSUE_TYPE_STORY
                    fallbacks_applied.append(f"Sub-task ({ISSUE_TYPE_TASK}) → {ISSUE_TYPE_STORY}")
                elif ISSUE_TYPE_EPIC in available_types:
                    issue_type_mapping['task'] = ISSUE_TYPE_EPIC
                    fallbacks_applied.append(f"Sub-task ({ISSUE_TYPE_TASK}) → {ISSUE_TYPE_EPIC}")
            
            # Bug fallback: Bug -> Task -> Story
            if ISSUE_TYPE_BUG not in available_types:
                if 'Task' in available_types:
                    issue_type_mapping['bug'] = 'Task'
                    fallbacks_applied.append(f"Bug ({ISSUE_TYPE_BUG}) → Task")
                elif ISSUE_TYPE_STORY in available_types:
                    issue_type_mapping['bug'] = ISSUE_TYPE_STORY
                    fallbacks_applied.append(f"Bug ({ISSUE_TYPE_BUG}) → {ISSUE_TYPE_STORY}")
            
            # Update global variables with fallbacks
            ISSUE_TYPE_STORY = issue_type_mapping['story']
            ISSUE_TYPE_TASK = issue_type_mapping['task']
            ISSUE_TYPE_BUG = issue_type_mapping['bug']
            
            print(f"\n📋 Issue type mapping (with fallbacks):")
            print(f"   Epic → {ISSUE_TYPE_EPIC}")
            print(f"   Story → {ISSUE_TYPE_STORY}")
            print(f"   Task → {ISSUE_TYPE_TASK}")
            print(f"   Bug → {ISSUE_TYPE_BUG}")
            
            if fallbacks_applied:
                print(f"\n⚡ Applied fallbacks:")
                for fallback in fallbacks_applied:
                    print(f"   - {fallback}")
            
            print(f"\n📄 Templates file: {TEMPLATE_DIR / 'templates.json'}")
            
            # Final check for critical missing types
            still_missing = []
            if ISSUE_TYPE_EPIC not in available_types:
                still_missing.append(f"Epic ({ISSUE_TYPE_EPIC})")
            if ISSUE_TYPE_STORY not in available_types:
                still_missing.append(f"Story → {ISSUE_TYPE_STORY}")
            if ISSUE_TYPE_TASK not in available_types:
                still_missing.append(f"Task → {ISSUE_TYPE_TASK}")
            if ISSUE_TYPE_BUG not in available_types:
                still_missing.append(f"Bug → {ISSUE_TYPE_BUG}")
            
            if still_missing:
                print(f"\n❌ ERROR: These issue types are still not available after fallbacks:")
                for mt in still_missing:
                    print(f"   - {mt}")
                print(f"\n💡 Available types in your JIRA project: {', '.join(available_types)}")
                print(f"💡 Fix: Set environment variables to match your project's issue types:")
                print(f"   ISSUE_TYPE_EPIC='Epic'  # or 'Story', 'Task'")
                print(f"   ISSUE_TYPE_STORY='Story'  # or 'Task', 'Epic'")
                print(f"   ISSUE_TYPE_TASK='Task'  # or 'Sub-task', 'Story'")
                print(f"   ISSUE_TYPE_BUG='Bug'  # or 'Task', 'Story'")
                exit(1)
            else:
                print(f"\n✅ All issue types resolved successfully!")

    process_specs()


if __name__ == "__main__":
    main()
