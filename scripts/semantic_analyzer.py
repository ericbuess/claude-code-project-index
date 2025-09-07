#!/usr/bin/env python3
"""
Semantic analyzer for code fingerprinting and similarity detection.
Used to enhance the project index with semantic analysis capabilities.
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Import utilities from index_utils
from index_utils import (
    create_ast_fingerprint,
    create_tfidf_embeddings,
    extract_architectural_patterns,
    normalize_code_for_comparison,
    extract_python_signatures,
    extract_javascript_signatures,
    extract_shell_signatures,
    PARSEABLE_LANGUAGES
)


class SemanticAnalyzer:
    """Main class for semantic code analysis and fingerprinting."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.vectorizer = None
        self.function_bodies = []
        self.function_metadata = []
    
    def analyze_project(self, index_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive semantic analysis on the project index."""
        print("Starting semantic analysis...")
        
        # Extract all function bodies and metadata
        all_functions = self._extract_all_functions(index_data)
        
        if not all_functions:
            print("No functions found for analysis")
            return self._create_empty_semantic_index()
        
        print(f"Analyzing {len(all_functions)} functions...")
        
        # Create embeddings for all functions
        function_bodies = [func['body'] for func in all_functions]
        vectorizer, embeddings = create_tfidf_embeddings(function_bodies)
        
        # Build semantic index
        semantic_index = {
            'functions': {},
            'similarity_clusters': [],
            'architectural_patterns': {},
            'complexity_analysis': {},
            'vocabulary': self._extract_vocabulary(vectorizer) if vectorizer else {}
        }
        
        # Process each function
        for i, func_data in enumerate(all_functions):
            func_id = f"{func_data['file_path']}:{func_data['name']}"
            
            # Create AST fingerprint
            ast_fingerprint = create_ast_fingerprint(
                func_data['body'], 
                func_data.get('language', 'python')
            )
            
            # Store function analysis
            semantic_index['functions'][func_id] = {
                'file_path': func_data['file_path'],
                'function_name': func_data['name'],
                'signature': func_data.get('signature', ''),
                'ast_fingerprint': ast_fingerprint,
                'tfidf_vector': embeddings[i] if embeddings else [],
                'complexity': self._calculate_complexity(func_data['body']),
                'patterns': self._identify_function_patterns(func_data['name'], func_data['body']),
                'language': func_data.get('language', 'python')
            }
        
        # Find similarity clusters
        if embeddings:
            semantic_index['similarity_clusters'] = self._find_similarity_clusters(
                all_functions, embeddings
            )
        
        # Extract architectural patterns
        semantic_index['architectural_patterns'] = self._analyze_architecture(index_data)
        
        # Complexity analysis
        semantic_index['complexity_analysis'] = self._analyze_complexity(all_functions)
        
        print(f"Semantic analysis complete. Found {len(semantic_index['similarity_clusters'])} similarity clusters.")
        
        return semantic_index
    
    def _extract_all_functions(self, index_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract all functions from the index with their bodies."""
        functions = []
        files = index_data.get('files', {})
        
        for file_path, file_data in files.items():
            if not file_data.get('parsed', False):
                continue
            
            language = file_data.get('language', 'unknown')
            
            # Read the actual file to get function bodies
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue
            
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    file_content = f.read()
            except:
                continue
            
            # Extract function bodies based on language
            if language == 'python':
                functions.extend(self._extract_python_function_bodies(
                    file_path, file_content, file_data.get('functions', {})
                ))
            elif language in ['javascript', 'typescript']:
                functions.extend(self._extract_javascript_function_bodies(
                    file_path, file_content, file_data.get('functions', {})
                ))
            elif language == 'shell':
                functions.extend(self._extract_shell_function_bodies(
                    file_path, file_content, file_data.get('functions', {})
                ))
        
        return functions
    
    def _extract_python_function_bodies(self, file_path: str, content: str, functions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract Python function bodies from file content."""
        result = []
        lines = content.split('\n')
        
        for func_name, func_info in functions.items():
            # Find function definition in file
            for i, line in enumerate(lines):
                if f"def {func_name}(" in line:
                    # Extract function body
                    body_lines = []
                    indent_level = len(line) - len(line.lstrip())
                    
                    # Collect function body
                    for j in range(i + 1, len(lines)):
                        current_line = lines[j]
                        if not current_line.strip():  # Empty line
                            body_lines.append(current_line)
                            continue
                        
                        current_indent = len(current_line) - len(current_line.lstrip())
                        if current_indent <= indent_level and current_line.strip():
                            break
                        
                        body_lines.append(current_line)
                    
                    if body_lines:
                        result.append({
                            'file_path': file_path,
                            'name': func_name,
                            'signature': func_info.get('signature', '') if isinstance(func_info, dict) else func_info,
                            'body': '\n'.join(body_lines),
                            'language': 'python'
                        })
                    break
        
        return result
    
    def _extract_javascript_function_bodies(self, file_path: str, content: str, functions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract JavaScript/TypeScript function bodies from file content."""
        result = []
        
        for func_name, func_info in functions.items():
            # Simple extraction - look for function patterns
            patterns = [
                rf'function\s+{func_name}\s*\([^)]*\)\s*{{',
                rf'const\s+{func_name}\s*=\s*\([^)]*\)\s*=>\s*{{',
                rf'{func_name}\s*\([^)]*\)\s*{{'
            ]
            
            for pattern in patterns:
                import re
                match = re.search(pattern, content)
                if match:
                    # Extract function body (simplified)
                    start = match.end()
                    brace_count = 1
                    end = start
                    
                    for i in range(start, len(content)):
                        if content[i] == '{':
                            brace_count += 1
                        elif content[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end = i
                                break
                    
                    if end > start:
                        body = content[start:end]
                        result.append({
                            'file_path': file_path,
                            'name': func_name,
                            'signature': func_info.get('signature', '') if isinstance(func_info, dict) else func_info,
                            'body': body,
                            'language': 'javascript'
                        })
                    break
        
        return result
    
    def _extract_shell_function_bodies(self, file_path: str, content: str, functions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract shell function bodies from file content."""
        result = []
        lines = content.split('\n')
        
        for func_name, func_info in functions.items():
            # Find function definition
            for i, line in enumerate(lines):
                if f"{func_name}()" in line or f"function {func_name}" in line:
                    # Extract function body
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
                        result.append({
                            'file_path': file_path,
                            'name': func_name,
                            'signature': func_info.get('signature', '') if isinstance(func_info, dict) else func_info,
                            'body': '\n'.join(body_lines),
                            'language': 'shell'
                        })
                    break
        
        return result
    
    def _calculate_complexity(self, function_body: str) -> Dict[str, int]:
        """Calculate cyclomatic complexity and other metrics."""
        # Simple complexity metrics
        complexity = {
            'lines': len([line for line in function_body.split('\n') if line.strip()]),
            'cyclomatic': 1,  # Base complexity
            'nesting_depth': 0
        }
        
        # Count decision points for cyclomatic complexity
        decision_patterns = [
            r'\bif\b', r'\belif\b', r'\belse\b',
            r'\bfor\b', r'\bwhile\b',
            r'\btry\b', r'\bexcept\b', r'\bcatch\b',
            r'\bswitch\b', r'\bcase\b',
            r'\?\s*.*\s*:'  # Ternary operator
        ]
        
        for pattern in decision_patterns:
            import re
            matches = re.findall(pattern, function_body, re.IGNORECASE)
            complexity['cyclomatic'] += len(matches)
        
        # Calculate nesting depth (simplified)
        max_depth = 0
        current_depth = 0
        for line in function_body.split('\n'):
            stripped = line.strip()
            if any(keyword in stripped for keyword in ['if', 'for', 'while', 'try', 'with']):
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif stripped.startswith(('end', '}')) or stripped == '':
                current_depth = max(0, current_depth - 1)
        
        complexity['nesting_depth'] = max_depth
        return complexity
    
    def _identify_function_patterns(self, func_name: str, func_body: str) -> List[str]:
        """Identify common patterns in function implementation."""
        patterns = []
        
        name_lower = func_name.lower()
        body_lower = func_body.lower()
        
        # Naming patterns
        if name_lower.startswith(('get', 'fetch', 'retrieve')):
            patterns.append('getter')
        elif name_lower.startswith(('set', 'update', 'modify')):
            patterns.append('setter')
        elif name_lower.startswith(('is', 'has', 'can', 'should')):
            patterns.append('predicate')
        elif 'valid' in name_lower or 'check' in name_lower:
            patterns.append('validation')
        elif name_lower.startswith(('create', 'make', 'build')):
            patterns.append('factory')
        elif name_lower.startswith(('parse', 'format', 'convert')):
            patterns.append('transformer')
        
        # Implementation patterns
        if 'raise ' in body_lower or 'throw ' in body_lower:
            patterns.append('error_handling')
        if 'log' in body_lower or 'print' in body_lower:
            patterns.append('logging')
        if 'async' in body_lower or 'await' in body_lower:
            patterns.append('async')
        if 'cache' in body_lower:
            patterns.append('caching')
        if 'db' in body_lower or 'database' in body_lower or 'query' in body_lower:
            patterns.append('database')
        if 'http' in body_lower or 'request' in body_lower or 'api' in body_lower:
            patterns.append('api')
        
        return patterns
    
    def _find_similarity_clusters(self, functions: List[Dict[str, Any]], embeddings: List[List[float]]) -> List[Dict[str, Any]]:
        """Find clusters of similar functions."""
        from index_utils import compute_code_similarity
        
        clusters = []
        processed = set()
        
        for i, func1 in enumerate(functions):
            if i in processed:
                continue
            
            cluster = {
                'representative': f"{func1['file_path']}:{func1['name']}",
                'functions': [f"{func1['file_path']}:{func1['name']}"],
                'similarity_scores': [1.0],
                'pattern': 'similar_implementation'
            }
            
            # Find similar functions
            for j, func2 in enumerate(functions[i+1:], i+1):
                if j in processed:
                    continue
                
                similarity = compute_code_similarity(embeddings[i], embeddings[j])
                if similarity >= 0.75:  # 75% similarity threshold for clustering
                    cluster['functions'].append(f"{func2['file_path']}:{func2['name']}")
                    cluster['similarity_scores'].append(similarity)
                    processed.add(j)
            
            if len(cluster['functions']) > 1:
                clusters.append(cluster)
            
            processed.add(i)
        
        return clusters
    
    def _analyze_architecture(self, index_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze architectural patterns across the project."""
        patterns = {
            'naming_conventions': {},
            'directory_patterns': {},
            'design_patterns': [],
            'dependency_patterns': {}
        }
        
        # Analyze file organization
        files = index_data.get('files', {})
        
        # Directory patterns
        directories = set()
        for file_path in files.keys():
            if '/' in file_path:
                directory = '/'.join(file_path.split('/')[:-1])
                directories.add(directory)
        
        # Common directory patterns
        if 'src' in directories:
            patterns['directory_patterns']['src_pattern'] = True
        if any('test' in d for d in directories):
            patterns['directory_patterns']['test_separation'] = True
        if any('util' in d for d in directories):
            patterns['directory_patterns']['utility_separation'] = True
        
        # Naming conventions analysis
        all_functions = []
        for file_data in files.values():
            if file_data.get('functions'):
                all_functions.extend(file_data['functions'].keys())
        
        if all_functions:
            snake_case = sum(1 for name in all_functions if '_' in name and name.islower())
            camel_case = sum(1 for name in all_functions if '_' not in name and any(c.isupper() for c in name[1:]))
            
            if snake_case > camel_case:
                patterns['naming_conventions']['functions'] = 'snake_case'
            elif camel_case > 0:
                patterns['naming_conventions']['functions'] = 'camelCase'
        
        return patterns
    
    def _analyze_complexity(self, functions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze project complexity metrics."""
        if not functions:
            return {}
        
        complexities = [self._calculate_complexity(func['body']) for func in functions]
        
        lines = [c['lines'] for c in complexities]
        cyclomatic = [c['cyclomatic'] for c in complexities]
        nesting = [c['nesting_depth'] for c in complexities]
        
        return {
            'total_functions': len(functions),
            'average_lines_per_function': sum(lines) / len(lines),
            'average_cyclomatic_complexity': sum(cyclomatic) / len(cyclomatic),
            'max_cyclomatic_complexity': max(cyclomatic),
            'average_nesting_depth': sum(nesting) / len(nesting),
            'max_nesting_depth': max(nesting),
            'high_complexity_functions': [
                f"{func['file_path']}:{func['name']}" 
                for func, complexity in zip(functions, complexities)
                if complexity['cyclomatic'] > 10 or complexity['nesting_depth'] > 4
            ]
        }
    
    def _extract_vocabulary(self, vectorizer) -> Dict[str, Any]:
        """Extract vocabulary information from TF-IDF vectorizer."""
        if not vectorizer:
            return {}
        
        try:
            vocabulary = vectorizer.get_feature_names_out()
            return {
                'size': len(vocabulary),
                'top_terms': list(vocabulary[:20])  # First 20 terms
            }
        except:
            return {}
    
    def _create_empty_semantic_index(self) -> Dict[str, Any]:
        """Create an empty semantic index structure."""
        return {
            'functions': {},
            'similarity_clusters': [],
            'architectural_patterns': {},
            'complexity_analysis': {},
            'vocabulary': {}
        }


def main():
    """Main entry point for semantic analysis."""
    if len(sys.argv) < 2:
        print("Usage: python semantic_analyzer.py <project_root> [index_file]")
        sys.exit(1)
    
    project_root = sys.argv[1]
    index_file = sys.argv[2] if len(sys.argv) > 2 else 'PROJECT_INDEX.json'
    
    # Load existing index
    index_path = Path(project_root) / index_file
    if not index_path.exists():
        print(f"Index file not found: {index_path}")
        sys.exit(1)
    
    try:
        with open(index_path, 'r') as f:
            index_data = json.load(f)
    except Exception as e:
        print(f"Error loading index: {e}")
        sys.exit(1)
    
    # Perform semantic analysis
    analyzer = SemanticAnalyzer(project_root)
    semantic_index = analyzer.analyze_project(index_data)
    
    # Add semantic index to existing data
    index_data['semantic_index'] = semantic_index
    
    # Save updated index
    try:
        with open(index_path, 'w') as f:
            json.dump(index_data, f, indent=2)
        print(f"Enhanced index saved to {index_path}")
    except Exception as e:
        print(f"Error saving index: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()