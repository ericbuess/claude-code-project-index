#!/usr/bin/env python3
"""
Utility functions for project indexing - reconstructed from PROJECT_INDEX.json signatures
"""

import re
import fnmatch
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any
import subprocess

# Constants
CODE_EXTENSIONS = {
    '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c', '.h', '.hpp', 
    '.cs', '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.scala', '.clj', '.sh'
}

MARKDOWN_EXTENSIONS = {'.md', '.markdown', '.rst', '.txt'}

# Parseable languages mapping
PARSEABLE_LANGUAGES = {
    '.py': 'python',
    '.js': 'javascript', 
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.jsx': 'javascript',
    '.java': 'java',
    '.cpp': 'cpp',
    '.c': 'c',
    '.h': 'c',
    '.hpp': 'cpp',
    '.cs': 'csharp',
    '.go': 'go',
    '.rs': 'rust',
    '.php': 'php',
    '.rb': 'ruby',
    '.swift': 'swift',
    '.kt': 'kotlin',
    '.scala': 'scala',
    '.clj': 'clojure',
    '.sh': 'shell'
}

IGNORE_DIRS = {
    '.git', '.svn', '.hg', 'node_modules', '__pycache__', '.pytest_cache', 
    'venv', '.venv', 'env', '.env', 'build', 'dist', '.idea', '.vscode'
}

# Directory purpose mapping
DIRECTORY_PURPOSES = {
    'tests': 'Test directory',
    'test': 'Test directory', 
    'docs': 'Documentation',
    'documentation': 'Documentation',
    'src': 'Source code',
    'source': 'Source code',
    'scripts': 'Build and utility scripts',
    'bin': 'Binary/executable files',
    'lib': 'Library code',
    'libs': 'Library code',
    'utils': 'Utility functions',
    'config': 'Configuration files',
    'configs': 'Configuration files'
}

DEFAULT_GITIGNORE_PATTERNS = {
    '*.pyc', '*.pyo', '*.pyd', '__pycache__/', '.pytest_cache/', 'node_modules/', 
    '.DS_Store', '.git/', '.svn/', '.hg/', 'dist/', 'build/', '.idea/', '.vscode/'
}


def extract_function_calls_python(body: str, all_functions: Set[str]) -> List[str]:
    """Extract function calls from Python code body."""
    calls = []
    # Simple regex to find function calls
    for match in re.finditer(r'\b(\w+)\s*\(', body):
        func_name = match.group(1)
        if func_name in all_functions and func_name not in calls:
            calls.append(func_name)
    return calls


def extract_function_calls_javascript(body: str, all_functions: Set[str]) -> List[str]:
    """Extract function calls from JavaScript/TypeScript code body."""
    calls = []
    # Simple regex to find function calls
    for match in re.finditer(r'\b(\w+)\s*\(', body):
        func_name = match.group(1)
        if func_name in all_functions and func_name not in calls:
            calls.append(func_name)
    return calls


def build_call_graph(functions: Dict, classes: Dict) -> Tuple[Dict, Dict]:
    """Build bidirectional call graph from extracted functions and methods."""
    call_graph = {}
    reverse_call_graph = {}
    
    # Process functions
    for func_name, func_data in functions.items():
        if isinstance(func_data, dict) and 'calls' in func_data:
            calls = func_data['calls']
            call_graph[func_name] = calls
            for called in calls:
                if called not in reverse_call_graph:
                    reverse_call_graph[called] = []
                reverse_call_graph[called].append(func_name)
    
    return call_graph, reverse_call_graph


def extract_python_signatures(content: str) -> Dict[str, Dict]:
    """Extract Python function and class signatures with full details for all files."""
    functions = {}
    classes = {}
    lines = content.split('\n')
    
    # Extract functions with more comprehensive pattern
    func_pattern = r'^(\s*)def\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*[^:]+)?\s*:'
    for i, line in enumerate(lines):
        match = re.match(func_pattern, line)
        if match:
            indent, func_name, params = match.groups()
            
            # Extract docstring if present
            doc = ""
            doc_start = i + 1
            if doc_start < len(lines) and '"""' in lines[doc_start]:
                doc_lines = []
                in_docstring = False
                for j in range(doc_start, min(doc_start + 10, len(lines))):
                    if '"""' in lines[j]:
                        if in_docstring:
                            break
                        else:
                            in_docstring = True
                            doc_lines.append(lines[j].strip().replace('"""', '').strip())
                    elif in_docstring:
                        doc_lines.append(lines[j].strip())
                doc = ' '.join(doc_lines).strip()
            
            functions[func_name] = {
                'name': func_name,
                'type': 'function',
                'line': i + 1,
                'signature': f"({params})",
                'doc': doc,
                'indent_level': len(indent) // 4  # Assuming 4-space indentation
            }
    
    # Extract classes with methods
    class_pattern = r'^(\s*)class\s+(\w+)(\([^)]*\))?\s*:'
    current_class = None
    current_class_indent = -1
    
    for i, line in enumerate(lines):
        class_match = re.match(class_pattern, line)
        if class_match:
            indent, class_name, inheritance = class_match.groups()
            indent_level = len(indent) // 4
            
            # Extract docstring if present
            doc = ""
            doc_start = i + 1
            if doc_start < len(lines) and '"""' in lines[doc_start]:
                doc_lines = []
                in_docstring = False
                for j in range(doc_start, min(doc_start + 10, len(lines))):
                    if '"""' in lines[j]:
                        if in_docstring:
                            break
                        else:
                            in_docstring = True
                            doc_lines.append(lines[j].strip().replace('"""', '').strip())
                    elif in_docstring:
                        doc_lines.append(lines[j].strip())
                doc = ' '.join(doc_lines).strip()
            
            classes[class_name] = {
                'name': class_name,
                'type': 'class',
                'line': i + 1,
                'doc': doc,
                'methods': {},
                'indent_level': indent_level
            }
            
            if inheritance:
                classes[class_name]['inherits'] = inheritance.strip('()')
            
            current_class = class_name
            current_class_indent = indent_level
        
        # Check for methods within classes
        elif current_class is not None:
            method_match = re.match(r'^(\s+)def\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*[^:]+)?\s*:', line)
            if method_match:
                method_indent, method_name, method_params = method_match.groups()
                method_indent_level = len(method_indent) // 4
                
                # If method is at class level (one level deeper than class)
                if method_indent_level == current_class_indent + 1:
                    # Extract method docstring
                    method_doc = ""
                    doc_start = i + 1
                    if doc_start < len(lines) and '"""' in lines[doc_start]:
                        doc_lines = []
                        in_docstring = False
                        for j in range(doc_start, min(doc_start + 10, len(lines))):
                            if '"""' in lines[j]:
                                if in_docstring:
                                    break
                                else:
                                    in_docstring = True
                                    doc_lines.append(lines[j].strip().replace('"""', '').strip())
                            elif in_docstring:
                                doc_lines.append(lines[j].strip())
                        method_doc = ' '.join(doc_lines).strip()
                    
                    classes[current_class]['methods'][method_name] = {
                        'name': method_name,
                        'type': 'method',
                        'line': i + 1,
                        'signature': f"({method_params})",
                        'doc': method_doc
                    }
            
            # Reset current class if we've moved to a different indentation level
            elif line.strip() and not line.startswith(' ' * ((current_class_indent + 1) * 4)):
                if not line.startswith(' ' * (current_class_indent * 4)):
                    current_class = None
                    current_class_indent = -1
    
    return {'functions': functions, 'classes': classes}


def pos_to_line(content: str, pos: int) -> int:
    """Convert character position to line number."""
    return content[:pos].count('\n') + 1


def extract_javascript_signatures(content: str) -> Dict[str, Any]:
    """Extract JavaScript/TypeScript function and class signatures with full details."""
    functions = {}
    classes = {}
    
    # Basic function extraction for JS/TS
    func_patterns = [
        r'function\s+(\w+)\s*\([^)]*\)',
        r'const\s+(\w+)\s*=\s*\([^)]*\)\s*=>',
        r'(\w+)\s*:\s*\([^)]*\)\s*=>'
    ]
    
    for pattern in func_patterns:
        for match in re.finditer(pattern, content, re.MULTILINE):
            func_name = match.group(1)
            functions[func_name] = {
                'name': func_name,
                'type': 'function',
                'line': pos_to_line(content, match.start())
            }
    
    return {'functions': functions, 'classes': classes}


def extract_function_calls_shell(body: str, all_functions: Set[str]) -> List[str]:
    """Extract function calls from shell script body."""
    calls = []
    # Simple pattern for shell function calls
    for match in re.finditer(r'\b(\w+)\b', body):
        func_name = match.group(1)
        if func_name in all_functions and func_name not in calls:
            calls.append(func_name)
    return calls


def extract_shell_signatures(content: str) -> Dict[str, Any]:
    """Extract shell script function signatures and structure."""
    functions = {}
    
    # Shell function pattern
    func_pattern = r'(\w+)\s*\(\)\s*\{'
    for match in re.finditer(func_pattern, content, re.MULTILINE):
        func_name = match.group(1)
        functions[func_name] = {
            'name': func_name,
            'type': 'function',
            'line': pos_to_line(content, match.start())
        }
    
    return {'functions': functions, 'classes': {}}


def extract_markdown_structure(file_path: Path) -> Dict[str, List[str]]:
    """Extract headers and architectural hints from markdown files."""
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        headers = []
        
        for match in re.finditer(r'^#+\s+(.+)$', content, re.MULTILINE):
            headers.append(match.group(1).strip())
        
        return {'headers': headers}
    except Exception:
        return {'headers': []}


def infer_file_purpose(file_path: Path) -> Optional[str]:
    """Infer the purpose of a file from its name and location."""
    name = file_path.name.lower()
    parent = file_path.parent.name.lower()
    
    if 'test' in name or parent == 'tests':
        return 'Test file'
    elif 'config' in name or name.endswith('.config.js'):
        return 'Configuration'
    elif name in ('readme.md', 'readme.txt'):
        return 'Documentation'
    elif name.startswith('.'):
        return 'Hidden/config file'
    else:
        return None


def infer_directory_purpose(path: Path, files_within: List[str]) -> Optional[str]:
    """Infer directory purpose from naming patterns and contents."""
    dir_name = path.name.lower()
    
    if dir_name in ('tests', 'test'):
        return 'Test directory'
    elif dir_name in ('docs', 'documentation'):
        return 'Documentation'
    elif dir_name in ('src', 'source'):
        return 'Source code'
    elif dir_name in ('scripts', 'bin'):
        return 'Build and utility scripts'
    else:
        return None


def get_language_name(extension: str) -> str:
    """Get readable language name from extension."""
    lang_map = {
        '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript', 
        '.java': 'Java', '.cpp': 'C++', '.c': 'C', '.go': 'Go',
        '.rs': 'Rust', '.php': 'PHP', '.rb': 'Ruby', '.sh': 'Shell',
        '.md': 'Markdown', '.json': 'JSON', '.yaml': 'YAML', '.yml': 'YAML'
    }
    return lang_map.get(extension, extension[1:].upper() if extension else 'Unknown')


def parse_gitignore(gitignore_path: Path) -> List[str]:
    """Parse a .gitignore file and return list of patterns."""
    try:
        patterns = []
        with open(gitignore_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    patterns.append(line)
        return patterns
    except Exception:
        return []


def load_gitignore_patterns(root_path: Path) -> Set[str]:
    """Load all gitignore patterns from project root and merge with defaults."""
    patterns = set(DEFAULT_GITIGNORE_PATTERNS)
    
    gitignore_path = root_path / '.gitignore'
    if gitignore_path.exists():
        patterns.update(parse_gitignore(gitignore_path))
    
    return patterns


def matches_gitignore_pattern(path: Path, patterns: Set[str], root_path: Path) -> bool:
    """Check if a path matches any gitignore pattern."""
    try:
        rel_path = path.relative_to(root_path)
        path_str = str(rel_path)
        
        for pattern in patterns:
            if fnmatch.fnmatch(path_str, pattern) or fnmatch.fnmatch(path.name, pattern):
                return True
        
        return False
    except ValueError:
        return False


def should_index_file(path: Path, root_path: Path = None) -> bool:
    """Check if we should index this file."""
    # Must be a code or markdown file
    if not (path.suffix in CODE_EXTENSIONS or path.suffix in MARKDOWN_EXTENSIONS):
        return False
    
    # Skip if in hardcoded ignored directory (for safety)
    for part in path.parts:
        if part in IGNORE_DIRS:
            return False
    
    # If root_path provided, check gitignore patterns
    if root_path:
        patterns = load_gitignore_patterns(root_path)
        if matches_gitignore_pattern(path, patterns, root_path):
            return False
    
    return True


def get_git_files(root_path: Path) -> Optional[List[Path]]:
    """Get list of files tracked by git."""
    try:
        result = subprocess.run(
            ['git', 'ls-files'], 
            cwd=root_path, 
            capture_output=True, 
            text=True
        )
        if result.returncode == 0:
            return [root_path / f for f in result.stdout.strip().split('\n') if f]
        return None
    except Exception:
        return None