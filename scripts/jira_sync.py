import os
import requests
import yaml
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
TEMP_YAML_DIR = Path(tempfile.mkdtemp(prefix="jira_sync_"))
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

# ---------------------------------------
# JIRA API
# ---------------------------------------

def markdown_to_adf(text):
    """Simplified markdown to ADF conversion for better performance"""
    if not text or not text.strip():
        return {
            "version": 1,
            "type": "doc",
            "content": [{
                "type": "paragraph",
                "content": [{"type": "text", "text": ""}]
            }]
        }
    
    # Simplified approach - preserve text with basic paragraph structure
    # Split into paragraphs and handle basic formatting
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    adf_content = []
    for paragraph in paragraphs:
        if paragraph.startswith('# '):
            # Header
            adf_content.append({
                "type": "heading",
                "attrs": {"level": 1},
                "content": [{"type": "text", "text": paragraph[2:].strip()}]
            })
        elif paragraph.startswith('## '):
            # Header level 2
            adf_content.append({
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": paragraph[3:].strip()}]
            })
        elif paragraph.startswith('```'):
            # Code block
            adf_content.append({
                "type": "codeBlock",
                "attrs": {"language": "text"},
                "content": [{"type": "text", "text": paragraph.replace('```', '').strip()}]
            })
        else:
            # Regular paragraph
            adf_content.append({
                "type": "paragraph",
                "content": [{"type": "text", "text": paragraph[:32000]}]
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
    """Simplified inline markdown parsing for better performance"""
    if not text:
        return [{"type": "text", "text": ""}]
    
    # Simplified approach - just return text with minimal processing
    # This avoids complex character-by-character parsing
    return [{"type": "text", "text": text}]


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
    """Load YAML template for specific issue type from single templates file"""
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
    
    templates_file = TEMPLATE_DIR / "templates.yaml"
    
    if not templates_file.exists():
        raise FileNotFoundError(f"Templates file not found: {templates_file}")
    
    with open(templates_file, 'r', encoding='utf-8') as f:
        all_templates = yaml.safe_load(f)
    
    if 'templates' not in all_templates or template_key not in all_templates['templates']:
        # Fallback to task template if specific template not found
        if template_key != "task" and "task" in all_templates.get('templates', {}):
            print(f"⚠️  Template '{template_key}' not found, using 'task' template for {issue_type}")
            template_key = "task"
        else:
            raise ValueError(f"Template '{template_key}' not found in {templates_file}")
    
    return all_templates['templates'][template_key]


def create_yaml_for_item(title, description, file_path, issue_type, parent_key=None, **kwargs):
    """Create a JIRA item YAML file from unified template"""
    
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
    environment = kwargs.get('environment', 'Not specified')
    
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
    yaml_data = copy.deepcopy(template_data)
    
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
    
    yaml_data = replace_placeholders(yaml_data)
    
    # Create temp YAML file
    safe_title = title[:50].replace(' ', '_').replace('/', '_').replace(':', '_')
    yaml_filename = f"{issue_type.lower().replace('-', '_')}_{safe_title}.yaml"
    yaml_file_path = TEMP_YAML_DIR / yaml_filename
    
    with open(yaml_file_path, 'w', encoding='utf-8') as f:
        yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True)
    
    print(f"  📝 Created YAML: {yaml_file_path.name} (from templates.yaml:{issue_type.lower()})")
    return yaml_file_path, yaml_data


def yaml_to_adf_description(yaml_data):
    """Convert YAML data to ADF description with GitHub link"""
    desc = yaml_data['description']
    
    # Create enhanced description with prominent GitHub link
    enhanced_description = f"""**📋 Specification Source**

🔗 **GitHub:** [{desc['source_file']}]({desc['github_link']})

---

{desc['content']}"""
    
    return markdown_to_adf(enhanced_description)


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

def create_issue_from_yaml(yaml_file_path, yaml_data):
    """Create JIRA issue from template-based YAML data"""
    
    summary = yaml_data['summary']
    issue_type = yaml_data['issue_type']
    parent_key = yaml_data.get('parent')
    
    # Remove empty parent key
    if parent_key == "":
        parent_key = None
    
    if DRY_RUN:
        print("\n--- DRY RUN ---")
        print("YAML FILE:", yaml_file_path.name)
        print("TYPE     :", issue_type)
        print("TITLE    :", summary)
        print("GITHUB   :", yaml_data['description']['github_link'])
        print("SOURCE   :", yaml_data['description']['source_file'])
        print("LABELS   :", yaml_data.get('labels', []))
        print("PRIORITY :", yaml_data.get('priority', 'Medium'))
        if yaml_data.get('severity'):
            print("SEVERITY :", yaml_data['severity'])
        if parent_key:
            print("PARENT   :", parent_key)
        if yaml_data.get('story_points'):
            print("POINTS   :", yaml_data['story_points'])
        print("---------------")
        return {"key": "DRYRUN"}

    # Convert YAML description to ADF with GitHub link
    adf_description = yaml_to_adf_description(yaml_data)

    # Build JIRA payload from YAML data
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
    if yaml_data.get('labels'):
        payload["fields"]["labels"] = yaml_data['labels']
    
    # Add priority if specified
    if yaml_data.get('priority'):
        payload["fields"]["priority"] = {"name": yaml_data['priority']}
    
    # Add story points for stories (if field exists in JIRA)
    if issue_type == ISSUE_TYPE_STORY and yaml_data.get('story_points'):
        # Note: Field name may vary by JIRA setup (customfield_XXXXX)
        # This is a common field name, may need customization
        payload["fields"]["customfield_10016"] = yaml_data['story_points']
    
    # Add components if specified
    if yaml_data.get('components'):
        payload["fields"]["components"] = [{"name": comp} for comp in yaml_data['components']]

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
            try:
                error_response = response.json()
                if "errorMessages" in error_response:
                    print(f"   - JIRA Error: {', '.join(error_response['errorMessages'])}")
            except:
                pass
            print(f"\n💡 TROUBLESHOOTING STEPS:")
            print(f"   1. Go to your JIRA project settings")
            print(f"   2. Check 'Project permissions' under 'Project settings'")
            print(f"   3. Ensure your user has 'Create Issues' permission")
            print(f"   4. If using API token, regenerate it and update JIRA_TOKEN")
        else:
            print(f"\n❌ ERROR: HTTP {response.status_code}")
            print(f"URL: {url}")
            print(f"YAML: {yaml_file_path}")
            print(f"Payload: {payload}")
            print(f"Response: {response.text[:500]}")
        response.raise_for_status()

    data = response.json()
    issue_key = data.get('key')
    issue_url = f"{JIRA_URL}/browse/{issue_key}"
    
    print(f"  ✅ Created {issue_type}: {issue_key} (YAML: {yaml_file_path.name})")
    print(f"     🔗 JIRA URL: {issue_url}")
    print(f"     📋 GitHub: {yaml_data['description']['github_link']}")

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
    
    print(f"\n📁 Creating temp YAML directory: {TEMP_YAML_DIR}")
    
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
    yaml_files_created = []

    try:
        # First pass: create epic from main spec.md
        for file in sorted(SPEC_FOLDER.glob("**/spec.md")):

            print(f"\n📋 Processing EPIC: {file}")
            print(f"   📍 Spec Location: {file.absolute()}")
            print(f"   🔗 GitHub Source: {GITHUB_REPO_URL}/blob/{GITHUB_BRANCH}/{file}")

            title, description, tasks = parse_markdown(file)
            
            # Create YAML for epic
            yaml_file, yaml_data = create_yaml_for_item(
                title, description, file, ISSUE_TYPE_EPIC
            )
            yaml_files_created.append(yaml_file)

            result = create_issue_from_yaml(yaml_file, yaml_data)

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
            
            # Create YAML for story
            yaml_file, yaml_data = create_yaml_for_item(
                title, description, file, ISSUE_TYPE_STORY, epic_key
            )
            yaml_files_created.append(yaml_file)

            result = create_issue_from_yaml(yaml_file, yaml_data)

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
                    task_yaml_file, task_yaml_data = create_yaml_for_item(
                        task_title, task_desc, file, "Task", None,  # No parent - flat structure
                        category=task_category, time_estimate=time_estimate
                    )
                else:
                    # Simple task (backward compatibility)
                    task_title = str(task)
                    
                    # Basic categorization for simple tasks
                    if any(keyword in task_title.lower() for keyword in ['test', 'testing']):
                        task_category = "testing"
                    
                    task_yaml_file, task_yaml_data = create_yaml_for_item(
                        task_title, task_title, file, "Task", None,  # No parent - flat structure
                        category=task_category, time_estimate="2h"
                    )
                
                yaml_files_created.append(task_yaml_file)
                create_issue_from_yaml(task_yaml_file, task_yaml_data)
                task_count += 1

        # Print summary
        print("\n" + "="*60)
        print("📊 JIRA SYNC SUMMARY")
        print("="*60)
        print(f"  Epics created:     {epic_count}")
        print(f"  Stories created:   {story_count}")
        print(f"  Subtasks created:  {task_count}")
        print(f"  YAML files:        {len(yaml_files_created)}")
        print(f"  TOTAL ISSUES:      {epic_count + story_count + task_count}")
        print(f"  TEMP YAML DIR:     {TEMP_YAML_DIR}")
        print("="*60)
        
        if not DRY_RUN:
            print(f"\n💡 YAML files preserved for debugging in: {TEMP_YAML_DIR}")
            print(f"   Remove with: rm -rf {TEMP_YAML_DIR}")
    
    except Exception as e:
        print(f"\n❌ ERROR during processing: {e}")
        raise
    finally:
        if DRY_RUN:
            # Clean up temp directory in dry run
            print(f"\n🧹 Cleaning up temp directory: {TEMP_YAML_DIR}")
            shutil.rmtree(TEMP_YAML_DIR, ignore_errors=True)


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

    print(f"\n🚀 STARTING JIRA SYNC")
    print(f"   Mode: {'DRY RUN (Preview Only)' if DRY_RUN else 'LIVE MODE (Will Create Issues)'}")
    
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
            
            print(f"\n📄 Templates file: {TEMPLATE_DIR / 'templates.yaml'}")
            
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
