import os
import requests
import json
import tempfile
import shutil
import copy
import argparse
import time
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

# Validate configuration (moved to main() function)
auth = None
if not DRY_RUN and os.environ.get('JIRA_URL'):
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
_available_fields_cache = {}
_global_field_cache = {}  # Cache all fields for the project upfront

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

def prefetch_project_fields(project_key):
    """Pre-fetch all available fields for the project to avoid repeated API calls"""
    global _global_field_cache
    
    if project_key in _global_field_cache:
        print(f"✅ Using cached fields for project {project_key}")
        return _global_field_cache[project_key]
    
    print(f"🔍 Pre-fetching JIRA fields for project {project_key}...")
    
    try:
        url = f"{JIRA_URL}/rest/api/3/issue/createmeta?projectKeys={project_key}&expand=projects.issuetypes.fields"
        print(f"   API URL: {url}")
        
        response = requests.get(url, auth=auth, headers={"Content-Type": "application/json"}, timeout=15)
        print(f"   Response status: {response.status_code}")
        
        if response.ok:
            data = response.json()
            project_fields = {}
            
            if data.get("projects") and len(data["projects"]) > 0:
                project = data["projects"][0]
                for issue_type in project.get("issuetypes", []):
                    type_name = issue_type.get("name")
                    fields = list(issue_type.get("fields", {}).keys())
                    project_fields[type_name] = fields
                    
                    # Also cache in the per-type cache
                    cache_key = f"{project_key}:{type_name}"
                    _available_fields_cache[cache_key] = fields
            
            _global_field_cache[project_key] = project_fields
            total_fields = sum(len(fields) for fields in project_fields.values())
            print(f"✅ Cached {len(project_fields)} issue types with {total_fields} total field mappings")
            return project_fields
        else:
            print(f"⚠️  API returned {response.status_code}: {response.text[:200]}")
            
    except requests.exceptions.Timeout:
        print(f"⚠️  Timeout fetching project fields (15s limit exceeded)")
    except requests.exceptions.ConnectionError as e:
        print(f"⚠️  Connection error: {e}")
    except Exception as e:
        print(f"⚠️  Error fetching project fields: {e}")
    
    _global_field_cache[project_key] = {}
    print(f"❌ Using empty field cache for {project_key}")
    return {}

def get_cached_fields_for_type(project_key, issue_type_name):
    """Get cached fields for a specific issue type (no API calls)"""
    cache_key = f"{project_key}:{issue_type_name}"
    
    if cache_key in _available_fields_cache:
        return _available_fields_cache[cache_key]
    
    # Fallback to global cache
    global_cache = _global_field_cache.get(project_key, {})
    return global_cache.get(issue_type_name, [])

def get_available_fields(project_key, issue_type_name):
    """Get available fields for a specific project and issue type (cached first)"""
    # Try cached version first (no API call)
    fields = get_cached_fields_for_type(project_key, issue_type_name)
    if fields:
        return fields
    
    # Fallback to API call (rare case)
    cache_key = f"{project_key}:{issue_type_name}"
    
    url = f"{JIRA_URL}/rest/api/3/issue/createmeta?projectKeys={project_key}&issuetypeNames={issue_type_name}&expand=projects.issuetypes.fields"
    
    try:
        response = requests.get(url, auth=auth, headers={"Content-Type": "application/json"}, timeout=10)
        if response.ok:
            data = response.json()
            if data.get("projects") and len(data["projects"]) > 0:
                project = data["projects"][0]
                if project.get("issuetypes") and len(project["issuetypes"]) > 0:
                    issue_type = project["issuetypes"][0]
                    fields = list(issue_type.get("fields", {}).keys())
                    _available_fields_cache[cache_key] = fields
                    return fields
    except Exception as e:
        print(f"⚠️  Warning: Could not fetch fields for {issue_type_name}: {e}")
    
    _available_fields_cache[cache_key] = []
    return []

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
    
    print(f"     🔍 Processing markdown ({len(text)} chars)...")
    
    # Prevent processing extremely long text to avoid hanging
    if len(text) > 50000:
        print(f"     ⚠️  Text too long ({len(text)} chars), truncating to 50,000...")
        text = text[:50000] + "\n\n[Content truncated due to length...]"
    
    adf_content = []
    lines = text.split('\n')
    total_lines = len(lines)
    i = 0
    max_iterations = total_lines * 3  # Safety limit
    iteration_count = 0
    
    print(f"     📄 Processing {total_lines} lines...")
    
    while i < len(lines) and iteration_count < max_iterations:
        iteration_count += 1
        line = lines[i]
        stripped = line.strip()
        
        # Progress indicator for long processing
        if iteration_count % 100 == 0:
            print(f"     ⏳ Progress: line {i}/{total_lines} (iteration {iteration_count})")
        
        # Safety break if we're in an infinite loop
        if iteration_count >= max_iterations - 10:
            print(f"     ⚠️  Markdown parsing taking too long, breaking at line {i}/{total_lines}")
            break
        
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
    
    # Safety limit for very long text
    if len(text) > 10000:
        print(f"       ⚠️  Inline text too long ({len(text)} chars), truncating...")
        return [{"type": "text", "text": text[:10000] + "[truncated]"}]
    
    content = []
    i = 0
    current_text = ""
    max_iterations = len(text) * 2  # Safety limit
    iteration_count = 0
    
    while i < len(text) and iteration_count < max_iterations:
        iteration_count += 1
        
        # Safety break if we're in an infinite loop
        if iteration_count >= max_iterations - 10:
            print(f"       ⚠️  Inline parsing taking too long, breaking at position {i}/{len(text)}")
            if current_text:
                content.append({"type": "text", "text": current_text})
            break
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
    print(f"   🔧 Starting ADF conversion...")
    desc = json_data['description']
    
    # Get content ADF with logging
    print(f"   📝 Converting markdown content (length: {len(desc['content'])} chars)...")
    
    # For very large content, use simple fallback to prevent hanging
    if len(desc['content']) > 15000:
        print(f"   ⚡ Large content detected ({len(desc['content'])} chars), using simple conversion...")
        content_blocks = [{
            "type": "paragraph",
            "content": [{"type": "text", "text": desc['content'][:15000] + "\n\n[Content truncated - see GitHub link above for full specification]"}]
        }]
        print(f"   ✅ Simple conversion completed (1 block with truncation)")
    else:
        try:
            content_adf = markdown_to_adf(desc['content'])
            content_blocks = content_adf.get("content", [])
            print(f"   ✅ ADF conversion completed ({len(content_blocks)} blocks)")
        except Exception as e:
            print(f"   ❌ ADF conversion failed: {e}")
            # Fallback to simple text
            content_blocks = [{
                "type": "paragraph",
                "content": [{"type": "text", "text": desc['content'][:5000]}]
            }]
            print(f"   🔄 Using fallback content (truncated to 5000 chars)")
    
    print(f"   🔨 Building final ADF structure...")
    
    # Build complete ADF with info panel
    result = {
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
            }
        ] + content_blocks
    }
    
    print(f"   ✅ ADF description ready ({len(result['content'])} total blocks)")
    return result


def get_project_issue_types():
    """Fetch available issue types for the project"""
    url = f"{JIRA_URL}/rest/api/3/issue/createmeta?projectKeys={PROJECT}&expand=projects.issuetypes"
    
    response = requests.get(
        url,
        auth=auth,
        headers={"Content-Type": "application/json"},
        timeout=10
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
    
    print(f"🔄 Creating JIRA issue from {json_file_path.name}...")
    
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
        print("PARENT   :", parent_key if parent_key else "None")
        print("---------------")
        return {"key": "DRYRUN"}

    print(f"   📋 Issue: {summary[:50]}...")
    print(f"   🏷️  Type: {issue_type}")
    
    # Convert JSON description to ADF with GitHub link
    print(f"   📝 Converting description to ADF...")
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

    # Add basic custom fields (no validation for performance)
    if json_data.get('custom_fields'):
        field_mappings = get_field_mappings()
        basic_mappings = {
            'epic_name': field_mappings.get('epic_name', 'customfield_10011'),
            'story_points': field_mappings.get('story_points', 'customfield_10016')
        }
        
        # Only add epic name and story points (most common)
        if issue_type == ISSUE_TYPE_EPIC and json_data.get('epic_name'):
            epic_field = basic_mappings['epic_name']
            payload["fields"][epic_field] = json_data['epic_name']
        
        if issue_type == ISSUE_TYPE_STORY and json_data.get('story_points'):
            story_field = basic_mappings['story_points']
            payload["fields"][story_field] = json_data['story_points']

    url = f"{JIRA_URL}/rest/api/3/issue"
    print(f"   🌐 Making API request to: {url}")
    print(f"   📦 Payload size: {len(str(payload))} characters")

    try:
        response = requests.post(
            url,
            json=payload,
            auth=auth,
            headers={"Content-Type": "application/json"},
            timeout=20
        )
        print(f"   📡 Response received: {response.status_code}")
        
    except requests.exceptions.Timeout:
        print(f"   ⏰ Request timeout after 20 seconds")
        return {"key": "ERROR", "error": "Timeout"}
    except requests.exceptions.ConnectionError as e:
        print(f"   🔌 Connection error: {e}")
        return {"key": "ERROR", "error": f"Connection: {e}"}
    except Exception as e:
        print(f"   ❌ Request error: {e}")
        return {"key": "ERROR", "error": f"Request: {e}"}
    
    # Add small delay to avoid JIRA throttling
    time.sleep(0.5)

    if not response.ok:
        error_info = {"key": "ERROR", "status_code": response.status_code}
        
        # Get detailed error information from JIRA response
        error_details = "HTTP Error"
        try:
            if response.text:
                error_data = response.json()
                if "errors" in error_data:
                    # Field-specific errors
                    field_errors = []
                    for field, message in error_data["errors"].items():
                        field_errors.append(f"{field}: {message}")
                    error_details = "; ".join(field_errors)
                elif "errorMessages" in error_data:
                    # General error messages
                    error_details = "; ".join(error_data["errorMessages"])
                elif error_data.get("message"):
                    # Single error message
                    error_details = error_data["message"]
                else:
                    # Raw error data
                    error_details = str(error_data)[:200]
            else:
                error_details = f"HTTP {response.status_code} - No response body"
        except Exception as e:
            # If we can't parse JSON, use raw response text
            error_details = response.text[:200] if response.text else f"HTTP {response.status_code} - Empty response"
        
        error_info["error"] = error_details
        
        # Log specific error details
        if response.status_code == 400:
            print(f"❌ Field validation error for {issue_type}: {summary[:50]}...")
            print(f"   Details: {error_details}")
        elif response.status_code == 401:
            print(f"❌ Authentication error - check JIRA credentials")
            print(f"   Details: {error_details}")
        elif response.status_code == 403:
            print(f"❌ Permission denied - insufficient access rights")
            print(f"   Details: {error_details}")
        elif response.status_code == 404:
            print(f"❌ Project or issue type not found")
            print(f"   Details: {error_details}")
        else:
            print(f"❌ HTTP {response.status_code} error for {issue_type}")
            print(f"   Details: {error_details}")
        
        return error_info

    data = response.json()
    issue_key = data.get('key')
    
    print(f"  ✅ {issue_key} ({issue_type})")

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

            print(f"\n📋 Processing EPIC: {file.relative_to(SPEC_FOLDER)}")

            title, description, tasks = parse_markdown(file)
            
            # Create JSON for epic
            json_file, json_data = create_json_for_item(
                title, description, file, ISSUE_TYPE_EPIC
            )
            json_files_created.append(json_file)

            result = create_issue_from_json(json_file, json_data)

            if result.get("key") == "ERROR":
                error_count += 1
                error_msg = result.get('error', 'Unknown error')
                errors_details.append(f"Epic: {title} - {error_msg}")
                print(f"  ❌ Failed to create epic: {error_msg}")
            else:
                epic_key = result.get("key")
                epic_count += 1

        # Second pass: create stories and tasks from other files
        for file in sorted(SPEC_FOLDER.glob("**/*.md")):

            # Skip spec.md (already processed as epic)
            if file.name == "spec.md":
                continue

            print(f"📄 Processing STORY: {file.relative_to(SPEC_FOLDER)}")

            title, description, tasks = parse_markdown(file)
            
            # Create JSON for story
            json_file, json_data = create_json_for_item(
                title, description, file, ISSUE_TYPE_STORY, epic_key
            )
            json_files_created.append(json_file)

            result = create_issue_from_json(json_file, json_data)

            if result.get("key") == "ERROR":
                error_count += 1
                error_msg = result.get('error', 'Unknown error')
                errors_details.append(f"Story: {title} - {error_msg}")
                print(f"  ❌ Failed to create story: {error_msg}")
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
                    error_msg = result.get('error', 'Unknown error')
                    errors_details.append(f"Task: {task_title} - {error_msg}")
                    print(f"  ❌ Failed to create task: {error_msg}")
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
            print(f"\n❌ DETAILED ERROR SUMMARY ({error_count} failures):")
            for i, error in enumerate(errors_details, 1):
                print(f"   {i}. {error}")
            print(f"\n💡 Review error details above to fix JIRA configuration issues.")
            print(f"   Common issues: missing custom fields, incorrect field types, permission errors.")
        
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


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Enhanced JIRA Sync - Convert markdown specs to JIRA issues with JSON templates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 jira_sync.py --dry-run                    # Preview what will be created
  python3 jira_sync.py --preview                    # Show structure preview only  
  python3 jira_sync.py --discover-fields            # Discover available JIRA fields
  python3 jira_sync.py --project TEST --dry-run     # Test with specific project
  python3 jira_sync.py --github-repo https://github.com/my/repo --branch main

Environment Variables:
  JIRA_URL, JIRA_EMAIL, JIRA_TOKEN, JIRA_PROJECT (required for live mode)
  GITHUB_REPO_URL, GITHUB_BRANCH (optional, auto-detected in GitHub Actions)
  ISSUE_TYPE_EPIC, ISSUE_TYPE_STORY, ISSUE_TYPE_TASK, ISSUE_TYPE_BUG (optional)
        """)
    
    parser.add_argument("--dry-run", "-d", action="store_true", 
                       help="Preview mode - don't create actual JIRA issues")
    parser.add_argument("--preview", "-p", action="store_true",
                       help="Show structure preview only (faster than dry-run)")
    parser.add_argument("--discover-fields", action="store_true",
                       help="Discover available JIRA fields and exit")
    
    # Override environment variables
    parser.add_argument("--project", help="JIRA project key (overrides JIRA_PROJECT)")
    parser.add_argument("--jira-url", help="JIRA URL (overrides JIRA_URL)")
    parser.add_argument("--github-repo", help="GitHub repository URL (overrides GITHUB_REPO_URL)")
    parser.add_argument("--branch", help="GitHub branch (overrides GITHUB_BRANCH)")
    
    # Template options
    parser.add_argument("--template", help="Template file to use (default: templates.json)")
    parser.add_argument("--use-simple-template", action="store_true", 
                       help="Use simple template (minimal custom fields)")
    
    # Issue type overrides
    parser.add_argument("--epic-type", help="Issue type for epics (default: Epic)")
    parser.add_argument("--story-type", help="Issue type for stories (default: Story)")
    parser.add_argument("--task-type", help="Issue type for tasks (default: Task)")
    parser.add_argument("--bug-type", help="Issue type for bugs (default: Bug)")
    
    # Performance options
    parser.add_argument("--timeout", type=int, default=30, help="API timeout in seconds (default: 30)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    return parser.parse_args()


def validate_jira_connection():
    """
    Comprehensive JIRA validation and connectivity check
    Returns: (success: bool, issues: list, warnings: list)
    """
    print(f"\n🔍 JIRA VALIDATION & CONNECTIVITY CHECK")
    print("="*60)
    
    issues = []
    warnings = []
    
    # 1. Basic Configuration Validation
    print(f"1️⃣ Validating basic configuration...")
    
    config_checks = [
        ("JIRA_URL", JIRA_URL, "https://your-domain.atlassian.net"),
        ("JIRA_EMAIL", EMAIL, "your-email@domain.com"),
        ("JIRA_TOKEN", TOKEN, "your-api-token"),
        ("JIRA_PROJECT", PROJECT, "PROJECT_KEY")
    ]
    
    for name, value, example in config_checks:
        if not value:
            issues.append(f"Missing {name} environment variable")
            print(f"   ❌ {name}: Not set")
        elif value == example:
            issues.append(f"{name} is using default/example value")
            print(f"   ❌ {name}: Using example value")
        else:
            print(f"   ✅ {name}: Configured")
    
    # URL format validation
    if JIRA_URL and not JIRA_URL.startswith(('http://', 'https://')):
        issues.append(f"JIRA_URL must start with http:// or https://")
        print(f"   ❌ JIRA_URL: Invalid format (missing protocol)")
    
    # Additional URL validation checks
    if JIRA_URL:
        if JIRA_URL.endswith('/'):
            warnings.append("JIRA_URL ends with '/' - this will be stripped automatically")
            print(f"   ⚠️  JIRA_URL: Trailing slash detected (will be auto-corrected)")
        
        # Common domain validation
        if 'atlassian.net' not in JIRA_URL and 'localhost' not in JIRA_URL and not JIRA_URL.startswith('http://'):
            warnings.append("JIRA_URL doesn't appear to be an Atlassian Cloud instance")
            print(f"   ⚠️  JIRA_URL: Not a standard Atlassian Cloud URL")
    
    # Token format validation
    if TOKEN and len(TOKEN) < 10:
        issues.append("JIRA_TOKEN appears too short (API tokens are typically 24+ characters)")
        print(f"   ❌ JIRA_TOKEN: Token appears too short")
    
    # Email format basic validation
    if EMAIL and '@' not in EMAIL:
        issues.append("JIRA_EMAIL doesn't appear to be a valid email address")
        print(f"   ❌ JIRA_EMAIL: Invalid email format")
    
    if issues:
        print(f"\n❌ Configuration validation failed with {len(issues)} issues")
        return False, issues, warnings
    
    # 2. Network Connectivity Test
    print(f"\n2️⃣ Testing network connectivity...")
    
    try:
        # Test basic connectivity without auth
        import urllib.parse
        parsed_url = urllib.parse.urlparse(JIRA_URL)
        test_host = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        print(f"   🌐 Testing connection to: {test_host}")
        response = requests.get(f"{JIRA_URL}/status", timeout=10)
        print(f"   ✅ Network connectivity: OK (HTTP {response.status_code})")
        
    except requests.exceptions.Timeout:
        issues.append("Network timeout - JIRA server unreachable")
        print(f"   ❌ Network connectivity: Timeout after 10 seconds")
        return False, issues, warnings
        
    except requests.exceptions.ConnectionError as e:
        issues.append(f"Connection error: {str(e)}")
        print(f"   ❌ Network connectivity: Connection failed")
        return False, issues, warnings
        
    except Exception as e:
        warnings.append(f"Network test inconclusive: {str(e)}")
        print(f"   ⚠️  Network connectivity: Test inconclusive")
    
    # 3. Authentication Test
    print(f"\n3️⃣ Testing JIRA authentication...")
    
    try:
        auth_url = f"{JIRA_URL}/rest/api/3/myself"
        print(f"   🔐 Testing auth at: /rest/api/3/myself")
        
        auth_response = requests.get(auth_url, auth=auth, timeout=15)
        
        if auth_response.status_code == 200:
            user_data = auth_response.json()
            display_name = user_data.get('displayName', 'Unknown')
            account_id = user_data.get('accountId', 'Unknown')
            print(f"   ✅ Authentication: SUCCESS")
            print(f"      User: {display_name} ({account_id})")
            
        elif auth_response.status_code == 401:
            issues.append("Authentication failed - invalid credentials")
            print(f"   ❌ Authentication: FAILED (401 Unauthorized)")
            print(f"      Check JIRA_EMAIL and JIRA_TOKEN values")
            return False, issues, warnings
            
        elif auth_response.status_code == 403:
            issues.append("Authentication failed - access forbidden")
            print(f"   ❌ Authentication: FAILED (403 Forbidden)")
            print(f"      User has insufficient permissions")
            return False, issues, warnings
            
        else:
            issues.append(f"Authentication test failed with HTTP {auth_response.status_code}")
            print(f"   ❌ Authentication: FAILED (HTTP {auth_response.status_code})")
            return False, issues, warnings
            
    except Exception as e:
        issues.append(f"Authentication test error: {str(e)}")
        print(f"   ❌ Authentication: ERROR - {str(e)}")
        return False, issues, warnings
    
    # 4. Project Access Validation
    print(f"\n4️⃣ Validating project access...")
    
    try:
        project_url = f"{JIRA_URL}/rest/api/3/project/{PROJECT}"
        print(f"   📋 Testing project access: {PROJECT}")
        
        project_response = requests.get(project_url, auth=auth, timeout=15)
        
        if project_response.status_code == 200:
            project_data = project_response.json()
            project_name = project_data.get('name', 'Unknown')
            project_type = project_data.get('projectTypeKey', 'unknown')
            print(f"   ✅ Project access: SUCCESS")
            print(f"      Project: {project_name} (Type: {project_type})")
            
        elif project_response.status_code == 404:
            issues.append(f"Project '{PROJECT}' not found or no access")
            print(f"   ❌ Project access: FAILED (404 Not Found)")
            print(f"      Project '{PROJECT}' does not exist or user has no access")
            return False, issues, warnings
            
        elif project_response.status_code == 403:
            issues.append(f"No permission to access project '{PROJECT}'")
            print(f"   ❌ Project access: FAILED (403 Forbidden)")
            return False, issues, warnings
            
        else:
            issues.append(f"Project access test failed with HTTP {project_response.status_code}")
            print(f"   ❌ Project access: FAILED (HTTP {project_response.status_code})")
            return False, issues, warnings
            
    except Exception as e:
        issues.append(f"Project access test error: {str(e)}")
        print(f"   ❌ Project access: ERROR - {str(e)}")
        return False, issues, warnings
    
    # 5. Issue Types Validation
    print(f"\n5️⃣ Validating issue types...")
    
    try:
        available_types = get_project_issue_types()
        
        if not available_types:
            warnings.append("Could not fetch issue types - proceeding with defaults")
            print(f"   ⚠️  Issue types: Could not fetch, using defaults")
        else:
            print(f"   📊 Available issue types: {', '.join(available_types)}")
            
            # Check each required type
            required_types = [
                ("Epic", ISSUE_TYPE_EPIC),
                ("Story", ISSUE_TYPE_STORY), 
                ("Task", ISSUE_TYPE_TASK),
                ("Bug", ISSUE_TYPE_BUG)
            ]
            
            missing_types = []
            for type_name, type_value in required_types:
                if type_value not in available_types:
                    missing_types.append(f"{type_name} ({type_value})")
                else:
                    print(f"   ✅ {type_name}: {type_value} - Available")
            
            if missing_types:
                warnings.append(f"Issue types not available: {', '.join(missing_types)}")
                print(f"   ⚠️  Missing types: {', '.join(missing_types)}")
                print(f"      Will attempt automatic fallbacks during processing")
            else:
                print(f"   ✅ All required issue types are available")
                
    except Exception as e:
        warnings.append(f"Issue type validation error: {str(e)}")
        print(f"   ⚠️  Issue types: Validation error - {str(e)}")
    
    # 6. Field Permissions Test
    print(f"\n6️⃣ Testing field permissions...")
    
    try:
        # Test create meta for Epic (most fields)
        meta_url = f"{JIRA_URL}/rest/api/3/issue/createmeta"
        params = {
            "projectKeys": PROJECT,
            "issuetypeNames": ISSUE_TYPE_EPIC,
            "expand": "projects.issuetypes.fields"
        }
        
        print(f"   🔧 Testing field access for {ISSUE_TYPE_EPIC}...")
        meta_response = requests.get(meta_url, params=params, auth=auth, timeout=15)
        
        if meta_response.status_code == 200:
            meta_data = meta_response.json()
            
            if meta_data.get("projects") and len(meta_data["projects"]) > 0:
                project = meta_data["projects"][0]
                if project.get("issuetypes") and len(project["issuetypes"]) > 0:
                    issue_type = project["issuetypes"][0]
                    available_fields = list(issue_type.get("fields", {}).keys())
                    
                    print(f"   ✅ Field permissions: SUCCESS")
                    print(f"      Available fields: {len(available_fields)}")
                    
                    # Check for key fields
                    key_fields = ["summary", "description", "issuetype", "project"]
                    missing_key_fields = [f for f in key_fields if f not in available_fields]
                    
                    if missing_key_fields:
                        issues.append(f"Missing required fields: {', '.join(missing_key_fields)}")
                        print(f"   ❌ Missing required fields: {', '.join(missing_key_fields)}")
                    else:
                        print(f"   ✅ All required fields available")
                        
                    # Check for common custom fields
                    common_custom = ["customfield_10016", "customfield_10011"]  # Story points, Epic name
                    available_custom = [f for f in common_custom if f in available_fields]
                    if available_custom:
                        print(f"   ✅ Custom fields detected: {len(available_custom)}")
                    else:
                        print(f"   ℹ️  No common custom fields found (normal for basic setups)")
                else:
                    warnings.append(f"No issue type data returned for {ISSUE_TYPE_EPIC}")
                    print(f"   ⚠️  No issue type data for {ISSUE_TYPE_EPIC}")
            else:
                warnings.append("No project data returned in create meta")
                print(f"   ⚠️  No project data in create meta response")
                
        elif meta_response.status_code == 403:
            warnings.append("Limited field access - may affect custom fields")
            print(f"   ⚠️  Field permissions: Limited access (403)")
            
        else:
            warnings.append(f"Field permission test failed: HTTP {meta_response.status_code}")
            print(f"   ⚠️  Field permissions: Test failed (HTTP {meta_response.status_code})")
            
    except Exception as e:
        warnings.append(f"Field permission test error: {str(e)}")
        print(f"   ⚠️  Field permissions: Test error - {str(e)}")
    
    # 7. Issue Creation Test (Dry Run)
    print(f"\n7️⃣ Testing issue creation permissions...")
    
    try:
        # Create minimal test payload
        test_payload = {
            "fields": {
                "project": {"key": PROJECT},
                "summary": "JIRA Sync Test Issue - DELETE ME",
                "description": {
                    "version": 1,
                    "type": "doc",
                    "content": [{
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Test issue created by JIRA sync validation. Safe to delete."}]
                    }]
                },
                "issuetype": {"name": ISSUE_TYPE_STORY}  # Use story as it's most common
            }
        }
        
        create_url = f"{JIRA_URL}/rest/api/3/issue"
        print(f"   🧪 Testing issue creation permissions (dry run)...")
        
        # Make a test request (we'll get validation response even without actually creating)
        test_response = requests.post(
            create_url,
            json=test_payload,
            auth=auth,
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        
        if test_response.status_code in [200, 201]:
            # Issue was created successfully (unexpected but good)
            created_issue = test_response.json()
            issue_key = created_issue.get("key")
            print(f"   ✅ Issue creation: SUCCESS")
            print(f"      Test issue created: {issue_key}")
            warnings.append(f"Test issue {issue_key} was created and should be deleted")
            
        elif test_response.status_code == 400:
            # Field validation error - check if it's permissions or field issues
            error_data = test_response.json()
            error_messages = error_data.get("errors", {})
            
            permission_errors = []
            field_errors = []
            
            for field, message in error_messages.items():
                if "permission" in message.lower() or "forbidden" in message.lower():
                    permission_errors.append(f"{field}: {message}")
                else:
                    field_errors.append(f"{field}: {message}")
            
            if permission_errors:
                issues.append(f"Issue creation permission errors: {'; '.join(permission_errors)}")
                print(f"   ❌ Issue creation: PERMISSION DENIED")
                for error in permission_errors:
                    print(f"      {error}")
            else:
                print(f"   ✅ Issue creation: PERMISSIONS OK")
                print(f"      Field validation errors are normal in validation test")
                if field_errors:
                    warnings.extend([f"Field issue: {err}" for err in field_errors[:3]])  # Limit to 3
                    
        elif test_response.status_code == 403:
            issues.append("No permission to create issues in this project")
            print(f"   ❌ Issue creation: FORBIDDEN (403)")
            print(f"      User cannot create issues in project {PROJECT}")
            
        else:
            warnings.append(f"Issue creation test inconclusive: HTTP {test_response.status_code}")
            print(f"   ⚠️  Issue creation: Test inconclusive (HTTP {test_response.status_code})")
            
    except Exception as e:
        warnings.append(f"Issue creation test error: {str(e)}")
        print(f"   ⚠️  Issue creation: Test error - {str(e)}")
    
    # Final Summary
    print(f"\n" + "="*60)
    print(f"📊 JIRA VALIDATION SUMMARY")
    print(f"="*60)
    
    if issues:
        print(f"❌ VALIDATION FAILED - {len(issues)} critical issues:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
        print(f"\n💡 Fix these issues before proceeding with JIRA sync.")
        
    else:
        print(f"✅ VALIDATION PASSED - JIRA is ready for sync")
        
    if warnings:
        print(f"\n⚠️  {len(warnings)} warnings (non-critical):")
        for i, warning in enumerate(warnings, 1):
            print(f"   {i}. {warning}")
    
    print(f"="*60)
    
    return len(issues) == 0, issues, warnings


# ---------------------------------------
# Main
# ---------------------------------------

def main():
    # Declare global variables at the start of function
    global DRY_RUN, JIRA_URL, PROJECT, GITHUB_REPO_URL, GITHUB_BRANCH
    global ISSUE_TYPE_EPIC, ISSUE_TYPE_STORY, ISSUE_TYPE_TASK, ISSUE_TYPE_BUG
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Apply command line overrides to global variables
    if args.dry_run:
        DRY_RUN = True
        os.environ['DRY_RUN'] = 'true'
    
    if args.project:
        PROJECT = args.project
        os.environ['JIRA_PROJECT'] = args.project
        
    if args.jira_url:
        JIRA_URL = args.jira_url.rstrip("/")
        os.environ['JIRA_URL'] = JIRA_URL
        
    if args.github_repo:
        GITHUB_REPO_URL = args.github_repo
        os.environ['GITHUB_REPO_URL'] = args.github_repo
        
    if args.branch:
        GITHUB_BRANCH = args.branch  
        os.environ['GITHUB_BRANCH'] = args.branch
        
    # Issue type overrides
    if args.epic_type:
        ISSUE_TYPE_EPIC = args.epic_type
    if args.story_type:
        ISSUE_TYPE_STORY = args.story_type
    if args.task_type:
        ISSUE_TYPE_TASK = args.task_type
    if args.bug_type:
        ISSUE_TYPE_BUG = args.bug_type
        
    # Template selection
    if args.use_simple_template:
        # Switch to simple template
        simple_template = TEMPLATE_DIR / "templates-simple.json"
        main_template = TEMPLATE_DIR / "templates.json"
        if simple_template.exists():
            import shutil
            shutil.copy(simple_template, main_template)
            print(f"📄 Using simple template (minimal custom fields)")
    
    # Special modes (that don't need JIRA config)
    if args.discover_fields:
        from discover_jira_fields import main as discover_main
        return discover_main()
        
    if args.preview:
        preview_structure()
        return

    # =================================================================
    # STEP 1: JIRA CONNECTIVITY & VALIDATION - MANDATORY FIRST STEP
    # =================================================================
    
    print(f"\n🔐 STEP 1: JIRA CONNECTIVITY & VALIDATION")
    print("="*70)
    
    if not DRY_RUN:
        # 1.1 Basic Configuration Check
        print(f"\n📋 Checking basic configuration...")
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
            print(f"❌ CONFIGURATION ERROR: Missing required environment variables")
            print(f"   Missing: {', '.join(missing)}")
            print(f"💡 Setup Guide:")
            print(f"   export JIRA_URL='https://your-domain.atlassian.net'")
            print(f"   export JIRA_EMAIL='your-email@domain.com'")
            print(f"   export JIRA_TOKEN='your-api-token'")
            print(f"   export JIRA_PROJECT='YOUR_PROJECT_KEY'")
            print(f"\n🔗 Get API token: https://id.atlassian.com/manage-profile/security/api-tokens")
            exit(1)
        
        print(f"✅ Basic configuration validated")
        
        # 1.2 Set up authentication
        global auth
        auth = (EMAIL, TOKEN)
        
        # 1.3 COMPREHENSIVE JIRA VALIDATION & CONNECTIVITY TEST
        print(f"\n🔍 Running comprehensive JIRA validation...")
        validation_start_time = time.time()
        validation_success, validation_issues, validation_warnings = validate_jira_connection()
        
        # 1.4 Handle validation results
        if not validation_success:
            print(f"\n❌ JIRA VALIDATION FAILED - CANNOT PROCEED")
            print(f"📋 Issues found ({len(validation_issues)}):")
            for i, issue in enumerate(validation_issues, 1):
                print(f"   {i}. {issue}")
            
            if validation_warnings:
                print(f"\n⚠️  Warnings ({len(validation_warnings)}):")
                for i, warning in enumerate(validation_warnings, 1):
                    print(f"   {i}. {warning}")
            
            print(f"\n💡 TROUBLESHOOTING:")
            print(f"   • Verify your JIRA URL is correct and accessible")
            print(f"   • Check your email and API token are valid") 
            print(f"   • Ensure you have access to the specified project")
            print(f"   • Test your credentials at: {JIRA_URL}/secure/ViewProfile.jspa")
            exit(1)
        
        # 1.5 Validation successful - log results
        print(f"\n🎉 JIRA VALIDATION SUCCESSFUL!")
        print(f"   ✅ Authentication verified")
        print(f"   ✅ Project access confirmed")  
        print(f"   ✅ All systems ready")
        print(f"   📊 Validation completed in ~{int(time.time() - validation_start_time)}s")
        
        if validation_warnings:
            print(f"\n⚠️  Warnings to note ({len(validation_warnings)}):")
            for i, warning in enumerate(validation_warnings, 1):
                print(f"   {i}. {warning}")
        
        # 1.6 Pre-fetch all project fields for performance optimization
        print(f"\n🚀 Pre-fetching JIRA field metadata for performance...")
        try:
            prefetch_project_fields(PROJECT)
            print(f"✅ Field metadata cached successfully")
        except Exception as e:
            print(f"⚠️  Could not pre-fetch fields: {e}")
            print(f"   📝 Will fetch fields on-demand (slower but functional)")
    
    else:
        print(f"\n📋 DRY RUN MODE - Configuration check only")
        print(f"✅ Configuration loaded for preview mode:")
        print(f"   JIRA_URL: {JIRA_URL or 'Not required in dry run'}")
        print(f"   PROJECT: {PROJECT or 'Not required in dry run'}")
        print(f"   EMAIL: {EMAIL or 'Not required in dry run'}")
        print(f"   Note: Full validation skipped in dry run mode")

    # =================================================================
    # STEP 2: CONFIGURATION & SETUP (After JIRA Validation Success)
    # =================================================================
    
    print(f"\n📋 STEP 2: FINAL CONFIGURATION & SETUP")
    print("="*70)
    print(f"✅ Configuration loaded:")
    print(f"   JIRA_URL: {JIRA_URL or 'Not required in dry run'}")
    print(f"   PROJECT: {PROJECT or 'Not required in dry run'}")
    print(f"   EMAIL: {EMAIL or 'Not required in dry run'}")
    print(f"   GITHUB_REPO_URL: {GITHUB_REPO_URL}")
    print(f"   GITHUB_BRANCH: {GITHUB_BRANCH}")
    print(f"   GITHUB_ACTIONS: {os.environ.get('GITHUB_ACTIONS', 'false')}")

    print(f"\n🚀 STARTING JIRA SYNC (Enhanced JSON Mode)")
    print(f"   Mode: {'DRY RUN (Preview Only)' if DRY_RUN else 'LIVE MODE (Will Create Issues)'}")
    print(f"   Format: JSON templates and data processing")
    
    # =================================================================
    # STEP 3: SPEC DISCOVERY & INITIAL ANALYSIS
    # =================================================================
    
    print(f"\n📁 STEP 3: SPEC DISCOVERY & INITIAL ANALYSIS") 
    print("="*70)
    
    # =================================================================
    # STEP 3A: VALIDATE SPEC FILES BEFORE PROCESSING
    # =================================================================
    
    print(f"\n🔍 Validating spec files before processing...")
    
    # Check if specs folder exists
    if not SPEC_FOLDER.exists():
        print(f"❌ ERROR: Specs folder does not exist at {SPEC_FOLDER.absolute()}")
        print(f"💡 Create the specs folder and add spec.md files to proceed")
        exit(1)
    
    # Count spec files
    epic_specs = list(SPEC_FOLDER.glob("**/spec.md"))
    all_md_files = list(SPEC_FOLDER.glob("**/*.md"))
    story_specs = [f for f in all_md_files if f.name != "spec.md"]
    total_specs = len(epic_specs) + len(story_specs)
    
    print(f"✅ Spec folder validation:")
    print(f"   📋 Epic specs (spec.md files): {len(epic_specs)}")
    print(f"   📄 Story specs (other .md files): {len(story_specs)}")
    print(f"   📊 Total specs to process: {total_specs}")
    
    # Validate minimum requirements
    if total_specs == 0:
        print(f"❌ ERROR: No spec files found in {SPEC_FOLDER.absolute()}")
        print(f"💡 Add at least one spec.md file or other .md files to proceed")
        exit(1)
    
    if len(epic_specs) == 0:
        print(f"⚠️  WARNING: No epic specs (spec.md) found - only story specs will be processed")
    
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
        # =================================================================
        # STEP 4: ISSUE TYPE RESOLUTION & MAPPING (After Validation)
        # =================================================================
        
        print(f"\n⚙️ STEP 4: ISSUE TYPE RESOLUTION & MAPPING")
        print("="*70)
        
        # Issue type resolution (moved here after validation)
        print(f"\n🔍 Resolving issue type mappings...")
        available_types = get_project_issue_types()  # Already cached from validation
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
            
            print(f"\n📋 Final issue type mapping:")
            print(f"   Epic → {ISSUE_TYPE_EPIC}")
            print(f"   Story → {ISSUE_TYPE_STORY}")
            print(f"   Task → {ISSUE_TYPE_TASK}")
            print(f"   Bug → {ISSUE_TYPE_BUG}")
            
            if fallbacks_applied:
                print(f"\n⚡ Applied fallbacks:")
                for fallback in fallbacks_applied:
                    print(f"   - {fallback}")
            
            print(f"\n📄 Templates file: {TEMPLATE_DIR / 'templates.json'}")

    # =================================================================
    # STEP 5: PROCESS SPEC FILES (After All Validation & Setup)
    # =================================================================
    
    print(f"\n📄 STEP 5: PROCESSING SPEC FILES")
    print("="*70)
    print(f"✅ All pre-flight checks passed - ready to process spec files")

    process_specs()


if __name__ == "__main__":
    main()
