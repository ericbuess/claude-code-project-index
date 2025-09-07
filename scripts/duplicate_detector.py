#!/usr/bin/env python3
"""
PostToolUse hook for real-time duplicate code detection.
Analyzes new/modified code and warns about potential duplicates.
"""

import json
import sys
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

# Import utilities from index_utils
try:
    from index_utils import (
        find_similar_functions,
        create_ast_fingerprint,
        create_tfidf_embeddings,
        compute_code_similarity,
        normalize_code_for_comparison,
        extract_python_signatures,
        extract_javascript_signatures,
        extract_shell_signatures,
        PARSEABLE_LANGUAGES
    )
except ImportError:
    # Add current directory to path for imports
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from index_utils import (
        find_similar_functions,
        create_ast_fingerprint,
        create_tfidf_embeddings,
        compute_code_similarity,
        normalize_code_for_comparison,
        extract_python_signatures,
        extract_javascript_signatures,
        extract_shell_signatures,
        PARSEABLE_LANGUAGES
    )


class DuplicateDetector:
    """Real-time duplicate detection for code modifications."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.index_path = self.project_root / 'PROJECT_INDEX.json'
        self.index_data = None
        self.load_index()
    
    def load_index(self):
        """Load the project index with semantic data."""
        if not self.index_path.exists():
            self.index_data = {}
            return
        
        try:
            with open(self.index_path, 'r') as f:
                self.index_data = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load index: {e}", file=sys.stderr)
            self.index_data = {}
    
    def analyze_code_change(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a code change for potential duplicates."""
        file_path = tool_input.get('file_path', '')
        content = tool_input.get('content', '')
        
        if not file_path or not content:
            return {'no_duplicates': True}
        
        # Determine file language
        file_ext = Path(file_path).suffix
        language = PARSEABLE_LANGUAGES.get(file_ext, 'unknown')
        
        if language == 'unknown':
            return {'no_duplicates': True}
        
        # Extract functions from the new/modified content
        new_functions = self._extract_functions_from_content(content, language)
        
        if not new_functions:
            return {'no_duplicates': True}
        
        # Check each function for duplicates
        duplicates = []
        for func_data in new_functions:
            similar_funcs = self._find_duplicates(func_data, language)
            if similar_funcs:
                duplicates.extend(similar_funcs)
        
        if duplicates:
            return {
                'duplicates_found': True,
                'duplicates': duplicates,
                'file_path': file_path
            }
        
        return {'no_duplicates': True}
    
    def _extract_functions_from_content(self, content: str, language: str) -> List[Dict[str, Any]]:
        """Extract function definitions from code content."""
        functions = []
        
        try:
            if language == 'python':
                signatures = extract_python_signatures(content)
                functions.extend(self._parse_python_functions(content, signatures.get('functions', {})))
            elif language in ['javascript', 'typescript']:
                signatures = extract_javascript_signatures(content)
                functions.extend(self._parse_javascript_functions(content, signatures.get('functions', {})))
            elif language == 'shell':
                signatures = extract_shell_signatures(content)
                functions.extend(self._parse_shell_functions(content, signatures.get('functions', {})))
        except Exception as e:
            print(f"Warning: Could not parse {language} code: {e}", file=sys.stderr)
        
        return functions
    
    def _parse_python_functions(self, content: str, functions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Python functions and extract their bodies."""
        result = []
        lines = content.split('\n')
        
        for func_name, func_info in functions.items():
            # Skip private/dunder methods for duplicate detection
            if func_name.startswith('_'):
                continue
            
            # Find function definition and extract body
            for i, line in enumerate(lines):
                if f"def {func_name}(" in line:
                    body_lines = []
                    indent_level = len(line) - len(line.lstrip())
                    
                    # Collect function body
                    for j in range(i + 1, len(lines)):
                        current_line = lines[j]
                        if not current_line.strip():
                            body_lines.append(current_line)
                            continue
                        
                        current_indent = len(current_line) - len(current_line.lstrip())
                        if current_indent <= indent_level and current_line.strip():
                            break
                        
                        body_lines.append(current_line)
                    
                    if body_lines:
                        # Clean up the body (remove docstrings and comments for analysis)
                        clean_body = self._clean_function_body('\n'.join(body_lines))
                        if len(clean_body.strip()) > 10:  # Ignore trivial functions
                            result.append({
                                'name': func_name,
                                'signature': func_info.get('signature', '') if isinstance(func_info, dict) else func_info,
                                'body': '\n'.join(body_lines),
                                'clean_body': clean_body,
                                'language': 'python'
                            })
                    break
        
        return result
    
    def _parse_javascript_functions(self, content: str, functions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse JavaScript/TypeScript functions and extract their bodies."""
        # Simplified extraction - for full implementation, would need better JS parsing
        result = []
        
        for func_name, func_info in functions.items():
            # Find function in content and extract body
            patterns = [
                rf'function\s+{func_name}\s*\([^)]*\)\s*{{([^}}]+)}}',
                rf'const\s+{func_name}\s*=\s*\([^)]*\)\s*=>\s*{{([^}}]+)}}',
                rf'{func_name}\s*\([^)]*\)\s*{{([^}}]+)}}'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    body = match.group(1) if match.lastindex else ''
                    clean_body = self._clean_function_body(body)
                    if len(clean_body.strip()) > 10:
                        result.append({
                            'name': func_name,
                            'signature': func_info.get('signature', '') if isinstance(func_info, dict) else func_info,
                            'body': body,
                            'clean_body': clean_body,
                            'language': 'javascript'
                        })
                    break
        
        return result
    
    def _parse_shell_functions(self, content: str, functions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse shell functions and extract their bodies."""
        result = []
        lines = content.split('\n')
        
        for func_name, func_info in functions.items():
            # Find function definition
            for i, line in enumerate(lines):
                if f"{func_name}()" in line or f"function {func_name}" in line:
                    body_lines = []
                    brace_count = 0
                    in_function = False
                    
                    for j in range(i + 1, len(lines)):
                        current_line = lines[j]
                        
                        if '{' in current_line:
                            brace_count += current_line.count('{')
                            in_function = True
                        
                        if in_function:
                            body_lines.append(current_line)
                        
                        if '}' in current_line:
                            brace_count -= current_line.count('}')
                            if brace_count <= 0:
                                break
                    
                    if body_lines:
                        body = '\n'.join(body_lines)
                        clean_body = self._clean_function_body(body)
                        if len(clean_body.strip()) > 10:
                            result.append({
                                'name': func_name,
                                'signature': func_info.get('signature', '') if isinstance(func_info, dict) else func_info,
                                'body': body,
                                'clean_body': clean_body,
                                'language': 'shell'
                            })
                    break
        
        return result
    
    def _clean_function_body(self, body: str) -> str:
        """Clean function body for duplicate detection analysis."""
        # Remove comments
        cleaned = re.sub(r'#.*$', '', body, flags=re.MULTILINE)
        cleaned = re.sub(r'//.*$', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
        
        # Remove docstrings
        cleaned = re.sub(r'""".*?"""', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"'''.*?'''", '', cleaned, flags=re.DOTALL)
        
        # Remove string literals (but keep structure)
        cleaned = re.sub(r'"[^"]*"', '"STRING"', cleaned)
        cleaned = re.sub(r"'[^']*'", "'STRING'", cleaned)
        
        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Remove empty lines
        lines = [line.strip() for line in cleaned.split('\n') if line.strip()]
        return '\n'.join(lines)
    
    def _find_duplicates(self, func_data: Dict[str, Any], language: str) -> List[Dict[str, Any]]:
        """Find duplicates for a specific function."""
        duplicates = []
        
        if not self.index_data or 'semantic_index' not in self.index_data:
            return duplicates
        
        semantic_index = self.index_data['semantic_index']
        existing_functions = semantic_index.get('functions', {})
        
        # Check for exact structural matches first (AST fingerprint)
        ast_fingerprint = create_ast_fingerprint(func_data['clean_body'], language)
        if ast_fingerprint:
            for func_id, func_info in existing_functions.items():
                if func_info.get('ast_fingerprint') == ast_fingerprint:
                    duplicates.append({
                        'type': 'exact_structural_duplicate',
                        'similarity': 1.0,
                        'existing_function': func_id,
                        'existing_signature': func_info.get('signature', ''),
                        'new_function': func_data['name'],
                        'message': f"Function '{func_data['name']}' has identical structure to existing function"
                    })
        
        # Check for semantic similarity using TF-IDF
        if func_data['clean_body'].strip():
            similar_functions = find_similar_functions(
                func_data['clean_body'], 
                self.index_data, 
                similarity_threshold=0.8
            )
            
            for similar in similar_functions:
                # Avoid duplicating exact matches
                if similar['similarity'] < 1.0:
                    duplicates.append({
                        'type': 'semantic_similarity',
                        'similarity': similar['similarity'],
                        'existing_function': similar['function_id'],
                        'existing_signature': similar.get('signature', ''),
                        'new_function': func_data['name'],
                        'message': f"Function '{func_data['name']}' is {similar['similarity']*100:.0f}% similar to existing function"
                    })
        
        # Check for naming pattern violations
        existing_names = [func_id.split(':')[-1] for func_id in existing_functions.keys()]
        naming_duplicates = self._check_naming_patterns(func_data['name'], existing_names)
        duplicates.extend(naming_duplicates)
        
        return duplicates
    
    def _check_naming_patterns(self, new_func_name: str, existing_names: List[str]) -> List[Dict[str, Any]]:
        """Check for naming pattern violations and similar names."""
        violations = []
        
        # Check for very similar names (potential typos or slight variations)
        for existing_name in existing_names:
            similarity = self._string_similarity(new_func_name.lower(), existing_name.lower())
            if 0.8 <= similarity < 1.0:  # Very similar but not identical
                violations.append({
                    'type': 'similar_naming',
                    'similarity': similarity,
                    'existing_function': existing_name,
                    'new_function': new_func_name,
                    'message': f"Function name '{new_func_name}' is very similar to existing '{existing_name}'"
                })
        
        return violations
    
    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity using simple character-based approach."""
        if not s1 or not s2:
            return 0.0
        
        # Simple Jaccard similarity on character bigrams
        bigrams1 = set(s1[i:i+2] for i in range(len(s1)-1))
        bigrams2 = set(s2[i:i+2] for i in range(len(s2)-1))
        
        if not bigrams1 and not bigrams2:
            return 1.0
        if not bigrams1 or not bigrams2:
            return 0.0
        
        intersection = len(bigrams1.intersection(bigrams2))
        union = len(bigrams1.union(bigrams2))
        
        return intersection / union if union > 0 else 0.0
    
    def generate_warning_message(self, duplicates: List[Dict[str, Any]], file_path: str) -> str:
        """Generate a human-readable warning message about duplicates."""
        if not duplicates:
            return ""
        
        messages = ["⚠️ Duplicate code detected:"]
        
        # Group by type
        exact_duplicates = [d for d in duplicates if d['type'] == 'exact_structural_duplicate']
        semantic_duplicates = [d for d in duplicates if d['type'] == 'semantic_similarity']
        naming_duplicates = [d for d in duplicates if d['type'] == 'similar_naming']
        
        if exact_duplicates:
            messages.append("\\n🚨 Exact duplicates:")
            for dup in exact_duplicates[:3]:  # Limit to top 3
                messages.append(f"  • {dup['message']}")
                messages.append(f"    Existing: {dup['existing_function']}")
        
        if semantic_duplicates:
            messages.append("\\n📊 Similar implementations:")
            for dup in semantic_duplicates[:3]:  # Limit to top 3
                messages.append(f"  • {dup['message']}")
                messages.append(f"    Existing: {dup['existing_function']}")
        
        if naming_duplicates:
            messages.append("\\n📝 Similar names:")
            for dup in naming_duplicates[:2]:  # Limit to top 2
                messages.append(f"  • {dup['message']}")
        
        messages.append("\\n💡 Suggestions:")
        if exact_duplicates:
            messages.append("  • Consider using the existing function or extracting shared logic")
        if semantic_duplicates:
            messages.append("  • Review if existing implementation can be reused or extended")
        if naming_duplicates:
            messages.append("  • Consider renaming to avoid confusion")
        
        return "\\n".join(messages)


def main():
    """Main hook entry point."""
    try:
        # Read hook input from stdin
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Extract relevant information
    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})
    
    # Only process code editing tools
    if tool_name not in ['Edit', 'Write', 'MultiEdit']:
        sys.exit(0)
    
    # Get project directory
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR')
    if not project_dir:
        project_dir = os.getcwd()
    
    # Initialize detector
    detector = DuplicateDetector(project_dir)
    
    # Analyze the code change
    analysis = detector.analyze_code_change(tool_input)
    
    # If duplicates found, block the operation
    if analysis.get('duplicates_found', False):
        duplicates = analysis.get('duplicates', [])
        file_path = analysis.get('file_path', '')
        
        warning_message = detector.generate_warning_message(duplicates, file_path)
        
        # Return blocking response
        output = {
            "decision": "block",
            "reason": warning_message
        }
        print(json.dumps(output))
        sys.exit(0)
    
    # No duplicates found, allow operation to proceed
    sys.exit(0)


if __name__ == '__main__':
    main()