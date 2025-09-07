#!/usr/bin/env python3
"""
Project Index for Claude Code
Provides spatial-architectural awareness to prevent code duplication and misplacement.

Features:
- Directory tree structure visualization
- Markdown documentation mapping with section headers
- Directory purpose inference
- Full function and class signatures with type annotations
- Multi-language support (parsed vs listed)

Usage: python project_index.py
Output: PROJECT_INDEX.json
"""

__version__ = "0.2.0-beta"

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import shared utilities
from index_utils import (
    IGNORE_DIRS, PARSEABLE_LANGUAGES, CODE_EXTENSIONS, MARKDOWN_EXTENSIONS,
    DIRECTORY_PURPOSES, extract_python_signatures, extract_javascript_signatures,
    extract_shell_signatures, extract_markdown_structure, infer_file_purpose, 
    infer_directory_purpose, get_language_name, should_index_file
)

# Limits to keep it fast and simple
MAX_FILES = 10000
MAX_INDEX_SIZE = 1024 * 1024  # 1MB
MAX_TREE_DEPTH = 5


def generate_tree_structure(root_path: Path, max_depth: int = MAX_TREE_DEPTH) -> List[str]:
    """Generate a compact ASCII tree representation of the directory structure."""
    tree_lines = []
    
    def should_include_dir(path: Path) -> bool:
        """Check if directory should be included in tree."""
        return (
            path.name not in IGNORE_DIRS and
            not path.name.startswith('.') and
            path.is_dir()
        )
    
    def add_tree_level(path: Path, prefix: str = "", depth: int = 0):
        """Recursively build tree structure."""
        if depth > max_depth:
            if any(should_include_dir(p) for p in path.iterdir() if p.is_dir()):
                tree_lines.append(prefix + "└── ...")
            return
        
        try:
            items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        except PermissionError:
            return
        
        # Filter items
        dirs = [item for item in items if should_include_dir(item)]
        
        # Important files to show in tree
        important_files = [
            item for item in items 
            if item.is_file() and (
                item.name in ['README.md', 'package.json', 'requirements.txt', 
                             'Cargo.toml', 'go.mod', 'pom.xml', 'build.gradle',
                             'setup.py', 'pyproject.toml', 'Makefile']
            )
        ]
        
        all_items = dirs + important_files
        
        for i, item in enumerate(all_items):
            is_last = i == len(all_items) - 1
            current_prefix = "└── " if is_last else "├── "
            
            name = item.name
            if item.is_dir():
                name += "/"
                # Add file count for directories
                try:
                    file_count = sum(1 for f in item.rglob('*') if f.is_file() and f.suffix in CODE_EXTENSIONS)
                    if file_count > 0:
                        name += f" ({file_count} files)"
                except:
                    pass
            
            tree_lines.append(prefix + current_prefix + name)
            
            if item.is_dir():
                next_prefix = prefix + ("    " if is_last else "│   ")
                add_tree_level(item, next_prefix, depth + 1)
    
    # Start with root
    tree_lines.append(".")
    add_tree_level(root_path, "")
    return tree_lines


def build_index(root_dir: str) -> Tuple[Dict, int]:
    """Build the enhanced index with architectural awareness."""
    root = Path(root_dir)
    
    index = {
        'indexed_at': datetime.now().isoformat(),
        'root': str(root),
        'project_structure': {
            'type': 'tree',
            'root': '.',
            'tree': []
        },
        'documentation_map': {},
        'directory_purposes': {},
        'stats': {
            'total_files': 0,
            'total_directories': 0,
            'fully_parsed': {},
            'listed_only': {},
            'markdown_files': 0
        },
        'files': {},
        'dependency_graph': {}
    }
    
    # Generate directory tree
    quiet = os.getenv('QUIET_MODE')
    verbose = os.getenv('VERBOSE_MODE')
    
    if not quiet:
        print("📊 Building directory tree...")
    index['project_structure']['tree'] = generate_tree_structure(root)
    
    file_count = 0
    dir_count = 0
    skipped_count = 0
    directory_files = {}  # Track files per directory
    
    # Try to use git ls-files for better performance and accuracy
    if not quiet:
        print("🔍 Indexing files...")
    from index_utils import get_git_files
    git_files = get_git_files(root)
    
    if git_files is not None:
        # Use git-based file discovery
        if verbose:
            print(f"   Using git ls-files (found {len(git_files)} files)")
        files_to_process = git_files
        
        # Count directories from git files
        seen_dirs = set()
        for file_path in git_files:
            for parent in file_path.parents:
                if parent != root and parent not in seen_dirs:
                    seen_dirs.add(parent)
                    if parent not in directory_files:
                        directory_files[parent] = []
        dir_count = len(seen_dirs)
    else:
        # Fallback to manual file discovery
        if verbose:
            print("   Using manual file discovery (git not available)")
        files_to_process = []
        for file_path in root.rglob('*'):
            if file_path.is_dir():
                # Track directories
                if not any(part in IGNORE_DIRS for part in file_path.parts):
                    dir_count += 1
                    directory_files[file_path] = []
                continue
            
            if file_path.is_file():
                files_to_process.append(file_path)
    
    # Process files
    for file_path in files_to_process:
        if file_count >= MAX_FILES:
            print(f"⚠️  Stopping at {MAX_FILES} files (project too large)")
            print(f"   Consider adding more patterns to .gitignore to reduce scope")
            print(f"   Or ask Claude to modify MAX_FILES in scripts/project_index.py")
            break
        
        if not should_index_file(file_path, root):
            skipped_count += 1
            continue
        
        # Track files in their directories
        parent_dir = file_path.parent
        if parent_dir in directory_files:
            directory_files[parent_dir].append(file_path.name)
        
        # Get relative path and language
        rel_path = file_path.relative_to(root)
        
        # Handle markdown files specially
        if file_path.suffix in MARKDOWN_EXTENSIONS:
            doc_structure = extract_markdown_structure(file_path)
            if doc_structure['sections'] or doc_structure['architecture_hints']:
                index['documentation_map'][str(rel_path)] = doc_structure
                index['stats']['markdown_files'] += 1
            continue
        
        # Handle code files
        language = get_language_name(file_path.suffix)
        
        # Base info for all files
        file_info = {
            'language': language,
            'parsed': False
        }
        
        # Add file purpose if we can infer it
        file_purpose = infer_file_purpose(file_path)
        if file_purpose:
            file_info['purpose'] = file_purpose
        
        # Try to parse if we support this language
        if file_path.suffix in PARSEABLE_LANGUAGES:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                
                # Extract based on language
                if file_path.suffix == '.py':
                    extracted = extract_python_signatures(content)
                elif file_path.suffix in {'.js', '.ts', '.jsx', '.tsx'}:
                    extracted = extract_javascript_signatures(content)
                elif file_path.suffix in {'.sh', '.bash'}:
                    extracted = extract_shell_signatures(content)
                else:
                    extracted = {'functions': {}, 'classes': {}}
                
                # Only add if we found something
                if extracted['functions'] or extracted['classes']:
                    file_info.update(extracted)
                    file_info['parsed'] = True
                    
                # Update stats
                lang_key = PARSEABLE_LANGUAGES[file_path.suffix]
                index['stats']['fully_parsed'][lang_key] = \
                    index['stats']['fully_parsed'].get(lang_key, 0) + 1
                    
            except Exception as e:
                # Parse error - just list the file
                index['stats']['listed_only'][language] = \
                    index['stats']['listed_only'].get(language, 0) + 1
        else:
            # Language not supported for parsing
            index['stats']['listed_only'][language] = \
                index['stats']['listed_only'].get(language, 0) + 1
        
        # Add to index
        index['files'][str(rel_path)] = file_info
        file_count += 1
        
        # Progress indicator every 100 files
        if file_count % 100 == 0 and verbose:
            print(f"  Indexed {file_count} files...")
    
    # Infer directory purposes
    if not quiet:
        print("🏗️  Analyzing directory purposes...")
    for dir_path, files in directory_files.items():
        if files:  # Only process directories with files
            purpose = infer_directory_purpose(dir_path, files)
            if purpose:
                rel_dir = str(dir_path.relative_to(root))
                if rel_dir != '.':
                    index['directory_purposes'][rel_dir] = purpose
    
    index['stats']['total_files'] = file_count
    index['stats']['total_directories'] = dir_count
    
    # Build dependency graph
    if not quiet:
        print("🔗 Building dependency graph...")
    dependency_graph = {}
    
    for file_path, file_info in index['files'].items():
        if file_info.get('imports'):
            # Normalize imports to resolve relative paths
            file_dir = Path(file_path).parent
            dependencies = []
            
            for imp in file_info['imports']:
                # Handle relative imports
                if imp.startswith('.'):
                    # Resolve relative import
                    if imp.startswith('./'):
                        # Same directory
                        resolved = str(file_dir / imp[2:])
                    elif imp.startswith('../'):
                        # Parent directory
                        parts = imp.split('/')
                        up_levels = len([p for p in parts if p == '..'])
                        target_dir = file_dir
                        for _ in range(up_levels):
                            target_dir = target_dir.parent
                        remaining = '/'.join(p for p in parts if p != '..')
                        resolved = str(target_dir / remaining) if remaining else str(target_dir)
                    else:
                        # Module import like from . import X
                        resolved = str(file_dir)
                    
                    # Try to find actual file
                    for ext in ['.py', '.js', '.ts', '.jsx', '.tsx', '']:
                        potential_file = resolved + ext
                        if potential_file in index['files'] or potential_file.replace('\\', '/') in index['files']:
                            dependencies.append(potential_file.replace('\\', '/'))
                            break
                else:
                    # External dependency or absolute import
                    dependencies.append(imp)
            
            if dependencies:
                dependency_graph[file_path] = dependencies
    
    # Only add if not empty
    if dependency_graph:
        index['dependency_graph'] = dependency_graph
    
    # Build bidirectional call graph
    if not quiet:
        print("📞 Building call graph...")
    call_graph = {}
    called_by_graph = {}
    
    # Process all files to build call relationships
    for file_path, file_info in index['files'].items():
        if not isinstance(file_info, dict):
            continue
            
        # Process functions in this file
        if 'functions' in file_info:
            for func_name, func_data in file_info['functions'].items():
                if isinstance(func_data, dict) and 'calls' in func_data:
                    # Track what this function calls
                    full_func_name = f"{file_path}:{func_name}"
                    call_graph[full_func_name] = func_data['calls']
                    
                    # Build reverse index (called_by)
                    for called in func_data['calls']:
                        if called not in called_by_graph:
                            called_by_graph[called] = []
                        called_by_graph[called].append(func_name)
        
        # Process methods in classes
        if 'classes' in file_info:
            for class_name, class_data in file_info['classes'].items():
                if isinstance(class_data, dict) and 'methods' in class_data:
                    for method_name, method_data in class_data['methods'].items():
                        if isinstance(method_data, dict) and 'calls' in method_data:
                            # Track what this method calls
                            full_method_name = f"{file_path}:{class_name}.{method_name}"
                            call_graph[full_method_name] = method_data['calls']
                            
                            # Build reverse index
                            for called in method_data['calls']:
                                if called not in called_by_graph:
                                    called_by_graph[called] = []
                                called_by_graph[called].append(f"{class_name}.{method_name}")
    
    # Add called_by information back to functions
    for file_path, file_info in index['files'].items():
        if not isinstance(file_info, dict):
            continue
            
        if 'functions' in file_info:
            for func_name, func_data in file_info['functions'].items():
                if func_name in called_by_graph:
                    if isinstance(func_data, dict):
                        func_data['called_by'] = called_by_graph[func_name]
                    else:
                        # Convert string signature to dict
                        index['files'][file_path]['functions'][func_name] = {
                            'signature': func_data,
                            'called_by': called_by_graph[func_name]
                        }
        
        if 'classes' in file_info:
            for class_name, class_data in file_info['classes'].items():
                if isinstance(class_data, dict) and 'methods' in class_data:
                    for method_name, method_data in class_data['methods'].items():
                        full_name = f"{class_name}.{method_name}"
                        if method_name in called_by_graph or full_name in called_by_graph:
                            callers = called_by_graph.get(method_name, []) + called_by_graph.get(full_name, [])
                            if callers:
                                if isinstance(method_data, dict):
                                    method_data['called_by'] = list(set(callers))
                                else:
                                    # Convert string signature to dict
                                    class_data['methods'][method_name] = {
                                        'signature': method_data,
                                        'called_by': list(set(callers))
                                    }
    
    # Add staleness check
    week_old = datetime.now().timestamp() - 7 * 24 * 60 * 60
    index['staleness_check'] = week_old
    
    return index, skipped_count


def convert_to_enhanced_dense_format(index: Dict) -> Dict:
    """Convert to enhanced dense format that preserves all AI-relevant information."""
    dense = {
        'at': index.get('indexed_at', ''),
        'root': index.get('root', '.'),
        'tree': index.get('project_structure', {}).get('tree', [])[:20],  # Compact tree
        'stats': index.get('stats', {}),
        'f': {},     # Files
        'g': [],     # Call graph edges
        'd': {},     # Documentation map
        'deps': index.get('dependency_graph', {}),  # Keep dependencies
    }
    
    def truncate_doc(doc: str, max_len: int = 80) -> str:
        """Truncate docstring to max length."""
        if not doc:
            return ''
        doc = doc.strip().replace('\n', ' ')
        if len(doc) > max_len:
            return doc[:max_len-3] + '...'
        return doc
    
    # Build compressed files section
    for path, info in index.get('files', {}).items():
        if not info.get('parsed', False):
            continue
            
        # Use abbreviated path
        abbrev_path = path.replace('scripts/', 's/').replace('src/', 'sr/').replace('tests/', 't/')
        
        file_entry = []
        
        # Add language as single letter
        lang = info.get('language', 'unknown')
        lang_map = {'python': 'p', 'javascript': 'j', 'typescript': 't', 'shell': 's', 'json': 'j'}
        file_entry.append(lang_map.get(lang, 'u'))
        
        # Compress functions with docstrings: name:line:signature:calls:docstring
        funcs = []
        for fname, fdata in info.get('functions', {}).items():
            if isinstance(fdata, dict):
                line = fdata.get('line', 0)
                sig = fdata.get('signature', '()')
                # Compress signature
                sig = sig.replace(' -> ', '>').replace(': ', ':')
                calls = ','.join(fdata.get('calls', []))
                doc = truncate_doc(fdata.get('doc', ''))
                funcs.append(f"{fname}:{line}:{sig}:{calls}:{doc}")
            else:
                funcs.append(f"{fname}:0:{fdata}::")
        
        if funcs:
            file_entry.append(funcs)
        
        # Compress classes with methods and docstrings
        classes = {}
        for cname, cdata in info.get('classes', {}).items():
            if isinstance(cdata, dict):
                class_line = str(cdata.get('line', 0))
                methods = []
                for mname, mdata in cdata.get('methods', {}).items():
                    if isinstance(mdata, dict):
                        mline = mdata.get('line', 0)
                        msig = mdata.get('signature', '()')
                        msig = msig.replace(' -> ', '>').replace(': ', ':')
                        mcalls = ','.join(mdata.get('calls', []))
                        mdoc = truncate_doc(mdata.get('doc', ''))
                        methods.append(f"{mname}:{mline}:{msig}:{mcalls}:{mdoc}")
                    else:
                        methods.append(f"{mname}:0:{mdata}::")
                
                if methods or class_line != '0':
                    classes[cname] = [class_line, methods]
        
        if classes:
            file_entry.append(classes)
        
        # Only add file if it has content
        if len(file_entry) > 1:
            dense['f'][abbrev_path] = file_entry
    
    # Build call graph edges (keep bidirectional info)
    edges = set()
    for path, info in index.get('files', {}).items():
        if info.get('parsed', False):
            # Extract function calls
            for fname, fdata in info.get('functions', {}).items():
                if isinstance(fdata, dict):
                    for called in fdata.get('calls', []):
                        edges.add((fname, called))
                    for caller in fdata.get('called_by', []):
                        edges.add((caller, fname))
            
            # Extract method calls
            for cname, cdata in info.get('classes', {}).items():
                if isinstance(cdata, dict):
                    for mname, mdata in cdata.get('methods', {}).items():
                        if isinstance(mdata, dict):
                            full_name = f"{cname}.{mname}"
                            for called in mdata.get('calls', []):
                                edges.add((full_name, called))
                            for caller in mdata.get('called_by', []):
                                edges.add((caller, full_name))
    
    # Convert edges to list format
    dense['g'] = [[e[0], e[1]] for e in edges]
    
    # Add compressed documentation map
    for doc_path, doc_info in index.get('documentation_map', {}).items():
        sections = doc_info.get('sections', [])
        if sections:
            # Keep first 10 sections for better context
            dense['d'][doc_path] = sections[:10]
    
    # Add directory purposes if present
    if 'directory_purposes' in index:
        dense['dir_purposes'] = index['directory_purposes']
    
    # Add staleness check timestamp
    if 'staleness_check' in index:
        dense['staleness'] = index['staleness_check']
    
    return dense


def compress_if_needed(dense_index: Dict, target_size: int = MAX_INDEX_SIZE) -> Dict:
    """Compress dense index further if it exceeds size limit."""
    index_json = json.dumps(dense_index, separators=(',', ':'))
    current_size = len(index_json)
    
    if current_size <= target_size:
        return dense_index
    
    print(f"⚠️  Index too large ({current_size} bytes), compressing to {target_size}...")
    
    # Add safeguards
    iteration = 0
    MAX_ITERATIONS = 10
    
    # Progressive compression strategies
    
    # Step 1: Reduce tree to 10 items
    iteration += 1
    if iteration > MAX_ITERATIONS:
        print(f"  ⚠️ Max compression iterations reached. Returning partially compressed index.")
        return dense_index
    
    print(f"  Step {iteration}: Reducing tree structure...")
    if len(dense_index.get('tree', [])) > 10:
        dense_index['tree'] = dense_index['tree'][:10]
        dense_index['tree'].append("... (truncated)")
        current_size = len(json.dumps(dense_index, separators=(',', ':')))
        if current_size <= target_size:
            print(f"  ✅ Compressed to {current_size} bytes")
            return dense_index
        
    # Step 2: Truncate docstrings to 40 chars
    iteration += 1
    if iteration > MAX_ITERATIONS:
        print(f"  ⚠️ Max compression iterations reached. Returning partially compressed index.")
        return dense_index
    
    print(f"  Step {iteration}: Truncating docstrings...")
    for path, file_data in dense_index.get('f', {}).items():
        if len(file_data) > 1 and isinstance(file_data[1], list):
            # Truncate function docstrings
            new_funcs = []
            for func in file_data[1]:
                parts = func.split(':')
                if len(parts) >= 5 and len(parts[4]) > 40:
                    parts[4] = parts[4][:37] + '...'
                new_funcs.append(':'.join(parts))
            file_data[1] = new_funcs
    
    current_size = len(json.dumps(dense_index, separators=(',', ':')))
    if current_size <= target_size:
        print(f"  ✅ Compressed to {current_size} bytes")
        return dense_index
        
    # Step 3: Remove docstrings entirely
    iteration += 1
    if iteration > MAX_ITERATIONS:
        print(f"  ⚠️ Max compression iterations reached. Returning partially compressed index.")
        return dense_index
    
    print(f"  Step {iteration}: Removing docstrings entirely...")
    for path, file_data in dense_index.get('f', {}).items():
        if len(file_data) > 1 and isinstance(file_data[1], list):
            # Remove docstrings from functions
            new_funcs = []
            for func in file_data[1]:
                parts = func.split(':')
                if len(parts) >= 5:
                    parts[4] = ''  # Remove docstring
                new_funcs.append(':'.join(parts))
            file_data[1] = new_funcs
    
    current_size = len(json.dumps(dense_index, separators=(',', ':')))
    if current_size <= target_size:
        print(f"  ✅ Compressed to {current_size} bytes")
        return dense_index
    
    # Step 4: Remove documentation map
    iteration += 1
    if iteration > MAX_ITERATIONS:
        print(f"  ⚠️ Max compression iterations reached. Returning partially compressed index.")
        return dense_index
    
    print(f"  Step {iteration}: Removing documentation map...")
    if 'd' in dense_index:
        del dense_index['d']
    
    current_size = len(json.dumps(dense_index, separators=(',', ':')))
    if current_size <= target_size:
        print(f"  ✅ Compressed to {current_size} bytes")
        return dense_index
    
    # Step 5: Emergency truncation - keep most important files
    iteration += 1
    if iteration > MAX_ITERATIONS:
        print(f"  ⚠️ Max compression iterations reached. Returning partially compressed index.")
        return dense_index
    
    print(f"  Step {iteration}: Emergency truncation - keeping most important files...")
    if dense_index.get('f'):
        files_to_keep = int(len(dense_index['f']) * (target_size / current_size) * 0.9)
        if files_to_keep < 10:
            files_to_keep = 10
        
        # Calculate importance based on function count
        file_importance = {}
        for path, file_data in dense_index['f'].items():
            importance = 0
            if len(file_data) > 1 and isinstance(file_data[1], list):
                importance = len(file_data[1])  # Number of functions
            if len(file_data) > 2:  # Has classes
                importance += 5
            file_importance[path] = importance
        
        # Keep most important files
        sorted_files = sorted(file_importance.items(), key=lambda x: x[1], reverse=True)
        files_to_keep_set = set(path for path, _ in sorted_files[:files_to_keep])
        
        # Remove less important files
        for path in list(dense_index['f'].keys()):
            if path not in files_to_keep_set:
                del dense_index['f'][path]
        
        print(f"  Emergency truncation: kept {len(dense_index['f'])} most important files")
    
    final_size = len(json.dumps(dense_index, separators=(',', ':')))
    print(f"  Compressed from {len(index_json)} to {final_size} bytes")
    
    return dense_index


def print_summary(index: Dict, skipped_count: int):
    """Print a helpful summary of what was indexed."""
    stats = index['stats']
    
    # Add warning if no files were found
    if stats['total_files'] == 0:
        print("\n⚠️  WARNING: No files were indexed!")
        print("   This might mean:")
        print("   • You're in the wrong directory")
        print("   • All files are being ignored (check .gitignore)")
        print("   • The project has no supported file types")
        print(f"\n   Current directory: {os.getcwd()}")
        print("   Try running from your project root directory.")
        return
    
    print(f"\n📊 Project Analysis Complete:")
    print(f"   📁 {stats['total_directories']} directories indexed")
    print(f"   📄 {stats['total_files']} code files found")
    print(f"   📝 {stats['markdown_files']} documentation files analyzed")
    
    # Show fully parsed languages
    if stats['fully_parsed']:
        print("\n✅ Languages with full parsing:")
        for lang, count in sorted(stats['fully_parsed'].items()):
            print(f"   • {count} {lang.capitalize()} files (with signatures)")
    
    # Show listed-only languages
    if stats['listed_only']:
        print("\n📋 Languages listed only:")
        for lang, count in sorted(stats['listed_only'].items()):
            print(f"   • {count} {lang.capitalize()} files")
    
    # Show documentation insights
    if index.get('d'):
        print(f"\n📚 Documentation insights:")
        for doc_file, sections in list(index['d'].items())[:3]:
            print(f"   • {doc_file}: {len(sections)} sections")
    
    # Show directory purposes
    if index.get('dir_purposes'):
        print(f"\n🏗️  Directory structure:")
        for dir_path, purpose in list(index['dir_purposes'].items())[:5]:
            print(f"   • {dir_path}/: {purpose}")
    
    if skipped_count > 0:
        print(f"\n   (Skipped {skipped_count} files in ignored directories)")


def main():
    """Run the enhanced indexer."""
    quiet = os.getenv('QUIET_MODE')
    if not quiet:
        print("🚀 Building Project Index...")
    
    # Check for target size from environment
    target_size_k = int(os.getenv('INDEX_TARGET_SIZE_K', '0'))
    if target_size_k > 0:
        # Convert k tokens to approximate bytes (1 token ≈ 4 chars)
        target_size_bytes = target_size_k * 1000 * 4
        print(f"   Target size: {target_size_k}k tokens (~{target_size_bytes:,} bytes)")
    else:
        target_size_bytes = MAX_INDEX_SIZE
    
    print("   Analyzing project structure and documentation...")
    
    # Build index for current directory
    index, skipped_count = build_index('.')
    
    # Convert to enhanced dense format (always)
    index = convert_to_enhanced_dense_format(index)
    
    # Compress further if needed
    index = compress_if_needed(index, target_size_bytes)
    
    # Add metadata if requested via environment
    if target_size_k > 0:
        if '_meta' not in index:
            index['_meta'] = {}
        # Note: Full metadata is added by the hook after generation
        index['_meta']['target_size_k'] = target_size_k
    
    # Save to PROJECT_INDEX.json (minified)
    output_path = Path('PROJECT_INDEX.json')
    output_path.write_text(json.dumps(index, separators=(',', ':')))
    
    # Print summary
    print_summary(index, skipped_count)
    
    print(f"\n💾 Saved to: {output_path}")
    
    # More concise output when called by hook
    if target_size_k > 0:
        actual_size = len(json.dumps(index, separators=(',', ':')))
        actual_tokens = actual_size // 4 // 1000
        print(f"📊 Size: {actual_tokens}k tokens (target was {target_size_k}k)")
    else:
        print("\n✨ Claude now has architectural awareness of your project!")
        print("   • Knows WHERE to place new code")
        print("   • Understands project structure")
        print("   • Can navigate documentation")
        print("\n📌 Benefits:")
        print("   • Prevents code duplication")
        print("   • Ensures proper file placement")
        print("   • Maintains architectural consistency")


if __name__ == '__main__':
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate PROJECT_INDEX.json for code analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s                     # Generate standard index
  %(prog)s -s 75               # Target 75k tokens
  %(prog)s --quiet             # Minimal output
        '''
    )
    
    parser.add_argument(
        '--version', 
        action='version', 
        version=f'PROJECT_INDEX v{__version__}'
    )
    
    parser.add_argument(
        '-s', '--size',
        type=int,
        metavar='K',
        help='Target size in thousands of tokens (e.g., 75 for 75k)'
    )
    
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Minimal output'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    parser.add_argument(
        '-d', '--directory',
        default='.',
        help='Directory to index (default: current directory)'
    )
    
    args = parser.parse_args()
    
    # Set environment variables based on arguments
    if args.size:
        os.environ['INDEX_TARGET_SIZE_K'] = str(args.size)
    
    if args.quiet:
        os.environ['QUIET_MODE'] = '1'
    
    if args.verbose:
        os.environ['VERBOSE_MODE'] = '1'
    
    # Change to target directory if specified
    if args.directory != '.':
        original_dir = os.getcwd()
        os.chdir(args.directory)
        try:
            main()
        finally:
            os.chdir(original_dir)
    else:
        main()