#!/usr/bin/env python3
"""
Append Embeddings to Index
Extends PROJECT_INDEX.json by adding neural embeddings to functions and classes.

This script reads the standard PROJECT_INDEX.json and adds embedding vectors
to each function and class method using Ollama's embedding models.

Usage: python append_embeddings_to_index.py [OPTIONS]
Output: Extends existing PROJECT_INDEX.json with 'embedding' fields
"""

__version__ = "0.1.0"

import json
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import centralized Ollama management
try:
    from find_ollama import OllamaManager
except ImportError:
    # Fallback if find_ollama.py is not in the same directory
    sys.path.insert(0, str(Path(__file__).parent))
    from find_ollama import OllamaManager


def generate_embedding(text: str, model_name: str = None, endpoint: str = None) -> Optional[List[float]]:
    """Generate embedding for text using centralized Ollama management.
    Returns None on error.
    """
    model_name = model_name or os.getenv('EMBED_MODEL_NAME', 'nomic-embed-text')
    endpoint = endpoint or os.getenv('EMBED_ENDPOINT', 'http://localhost:11434')
    
    try:
        manager = OllamaManager(endpoint)
        manager.default_model = model_name
        success, embedding, error = manager.generate_embedding(text, model_name)
        if success:
            return embedding
        else:
            print(f"  Warning: Could not generate embedding: {error}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"  Warning: Could not generate embedding: {e}", file=sys.stderr)
        return None


def load_project_index(index_path: str) -> Dict:
    """Load existing PROJECT_INDEX.json."""
    try:
        with open(index_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: {index_path} not found!")
        print("   Run project_index.py first to generate the base index:")
        print(f"   python3 scripts/project_index.py")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in {index_path}: {e}")
        sys.exit(1)


def detect_format(index: Dict) -> str:
    """Detect whether index is in original or compressed format."""
    if 'files' in index and isinstance(index['files'], dict):
        return 'original'
    elif 'f' in index:
        return 'compressed'
    else:
        print("❌ Error: Unknown index format")
        sys.exit(1)


def add_embeddings_to_original_format(index: Dict, model_name: str, endpoint: str) -> int:
    """Add embeddings to original format index."""
    embeddings_added = 0
    
    for file_path, file_info in index.get('files', {}).items():
        if not isinstance(file_info, dict) or not file_info.get('parsed', False):
            continue
        
        # Process functions
        for func_name, func_data in file_info.get('functions', {}).items():
            if isinstance(func_data, dict) and 'embedding' not in func_data:
                # Create text representation for embedding
                func_text = f"Function: {func_name}\\n"
                if 'signature' in func_data:
                    func_text += f"Signature: {func_data['signature']}\\n"
                if 'doc' in func_data:
                    func_text += f"Documentation: {func_data['doc']}\\n"
                if 'calls' in func_data:
                    func_text += f"Calls: {', '.join(func_data['calls'])}\\n"
                
                embedding = generate_embedding(func_text, model_name, endpoint)
                if embedding:
                    func_data['embedding'] = embedding
                    embeddings_added += 1
        
        # Process classes and methods
        for class_name, class_data in file_info.get('classes', {}).items():
            if isinstance(class_data, dict):
                # Class-level embedding
                if 'embedding' not in class_data:
                    class_text = f"Class: {class_name}\\n"
                    if 'inherits' in class_data:
                        class_text += f"Inherits: {', '.join(class_data['inherits'])}\\n"
                    if 'doc' in class_data:
                        class_text += f"Documentation: {class_data['doc']}\\n"
                    
                    class_embedding = generate_embedding(class_text, model_name, endpoint)
                    if class_embedding:
                        class_data['embedding'] = class_embedding
                        embeddings_added += 1
                
                # Method embeddings
                for method_name, method_data in class_data.get('methods', {}).items():
                    if isinstance(method_data, dict) and 'embedding' not in method_data:
                        method_text = f"Method: {class_name}.{method_name}\\n"
                        if 'signature' in method_data:
                            method_text += f"Signature: {method_data['signature']}\\n"
                        if 'doc' in method_data:
                            method_text += f"Documentation: {method_data['doc']}\\n"
                        if 'calls' in method_data:
                            method_text += f"Calls: {', '.join(method_data['calls'])}\\n"
                        
                        method_embedding = generate_embedding(method_text, model_name, endpoint)
                        if method_embedding:
                            method_data['embedding'] = method_embedding
                            embeddings_added += 1
    
    return embeddings_added


def expand_compressed_to_original_with_embeddings(index: Dict, model_name: str, endpoint: str) -> Tuple[Dict, int]:
    """Expand compressed format to original format with embeddings."""
    expanded = {
        'indexed_at': index.get('at', ''),
        'root': index.get('root', '.'),
        'project_structure': {
            'type': 'tree',
            'root': '.',
            'tree': index.get('tree', [])
        },
        'documentation_map': index.get('d', {}),
        'directory_purposes': index.get('dir_purposes', {}),
        'stats': index.get('stats', {}),
        'files': {},
        'dependency_graph': index.get('deps', {}),
        'staleness_check': index.get('staleness', datetime.now().timestamp() - 7 * 24 * 60 * 60)
    }
    
    embeddings_added = 0
    
    # Process compressed files
    for abbrev_path, file_data in index.get('f', {}).items():
        if not isinstance(file_data, list) or len(file_data) < 2:
            continue
        
        # Expand abbreviated path
        full_path = abbrev_path.replace('s/', 'scripts/').replace('sr/', 'src/').replace('t/', 'tests/')
        
        # Decode language
        lang_code = file_data[0]
        lang_map = {'p': 'python', 'j': 'javascript', 't': 'typescript', 's': 'shell'}
        language = lang_map.get(lang_code, 'unknown')
        
        file_info = {
            'language': language,
            'parsed': True,
            'functions': {},
            'classes': {}
        }
        
        # Process functions (second element)
        if len(file_data) > 1 and isinstance(file_data[1], list):
            for func_str in file_data[1]:
                parts = func_str.split(':')
                if len(parts) >= 5:
                    func_name = parts[0]
                    line = int(parts[1]) if parts[1].isdigit() else 0
                    signature = parts[2].replace('>', ' -> ').replace(':', ': ')
                    calls = parts[3].split(',') if parts[3] else []
                    doc = parts[4]
                    
                    func_data = {
                        'line': line,
                        'signature': signature,
                        'doc': doc,
                        'calls': calls
                    }
                    
                    # Generate embedding
                    func_text = f"Function: {func_name}\\n"
                    func_text += f"Signature: {signature}\\n"
                    if doc:
                        func_text += f"Documentation: {doc}\\n"
                    if calls:
                        func_text += f"Calls: {', '.join(calls)}\\n"
                    
                    embedding = generate_embedding(func_text, model_name, endpoint)
                    if embedding:
                        func_data['embedding'] = embedding
                        embeddings_added += 1
                    
                    file_info['functions'][func_name] = func_data
        
        # Process classes (third element)
        if len(file_data) > 2 and isinstance(file_data[2], dict):
            for class_name, class_info in file_data[2].items():
                if isinstance(class_info, list) and len(class_info) >= 2:
                    class_line = int(class_info[0]) if class_info[0].isdigit() else 0
                    methods = class_info[1] if isinstance(class_info[1], list) else []
                    
                    class_data = {
                        'line': class_line,
                        'methods': {}
                    }
                    
                    # Generate class embedding
                    class_text = f"Class: {class_name}\\n"
                    class_embedding = generate_embedding(class_text, model_name, endpoint)
                    if class_embedding:
                        class_data['embedding'] = class_embedding
                        embeddings_added += 1
                    
                    # Process methods
                    for method_str in methods:
                        parts = method_str.split(':')
                        if len(parts) >= 5:
                            method_name = parts[0]
                            method_line = int(parts[1]) if parts[1].isdigit() else 0
                            method_sig = parts[2].replace('>', ' -> ').replace(':', ': ')
                            method_calls = parts[3].split(',') if parts[3] else []
                            method_doc = parts[4]
                            
                            method_data = {
                                'line': method_line,
                                'signature': method_sig,
                                'doc': method_doc,
                                'calls': method_calls
                            }
                            
                            # Generate method embedding
                            method_text = f"Method: {class_name}.{method_name}\\n"
                            method_text += f"Signature: {method_sig}\\n"
                            if method_doc:
                                method_text += f"Documentation: {method_doc}\\n"
                            if method_calls:
                                method_text += f"Calls: {', '.join(method_calls)}\\n"
                            
                            method_embedding = generate_embedding(method_text, model_name, endpoint)
                            if method_embedding:
                                method_data['embedding'] = method_embedding
                                embeddings_added += 1
                            
                            class_data['methods'][method_name] = method_data
                    
                    file_info['classes'][class_name] = class_data
        
        expanded['files'][full_path] = file_info
    
    # Update stats
    if 'embeddings_generated' not in expanded['stats']:
        expanded['stats']['embeddings_generated'] = embeddings_added
    
    return expanded, embeddings_added


def main():
    """Main embedding generation interface."""
    parser = argparse.ArgumentParser(
        description='Add neural embeddings to PROJECT_INDEX.json',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s                                 # Add embeddings to PROJECT_INDEX.json
  %(prog)s --model mxbai-embed-large       # Use different embedding model
  %(prog)s --input CUSTOM_INDEX.json      # Process custom index file
  %(prog)s --output EMBEDDED_INDEX.json   # Save to different file
        '''
    )
    
    parser.add_argument('--version', action='version', version=f'Embedding Generator v{__version__}')
    
    # File I/O
    parser.add_argument('-i', '--input', default='PROJECT_INDEX.json',
                       help='Input index file (default: PROJECT_INDEX.json)')
    parser.add_argument('-o', '--output', type=str,
                       help='Output file (default: same as input)')
    
    # Embedding options
    parser.add_argument('--model', default='nomic-embed-text',
                       help='Ollama model for embeddings (default: nomic-embed-text)')
    parser.add_argument('--endpoint', default='http://localhost:11434',
                       help='Ollama API endpoint (default: http://localhost:11434)')
    
    # Options
    parser.add_argument('--force', action='store_true',
                       help='Regenerate embeddings even if they already exist')
    parser.add_argument('--expand-compressed', action='store_true',
                       help='Expand compressed format to original format with embeddings')
    
    args = parser.parse_args()
    
    print(f"🧠 Adding embeddings to index: {args.input}")
    
    # Load project index
    index = load_project_index(args.input)
    format_type = detect_format(index)
    
    print(f"📊 Detected format: {format_type}")
    
    embeddings_added = 0
    
    if format_type == 'original':
        if not args.force:
            # Check if embeddings already exist
            has_embeddings = False
            for file_info in index.get('files', {}).values():
                if isinstance(file_info, dict):
                    for func_data in file_info.get('functions', {}).values():
                        if isinstance(func_data, dict) and 'embedding' in func_data:
                            has_embeddings = True
                            break
                    if has_embeddings:
                        break
            
            if has_embeddings:
                print("⚠️  Embeddings already exist. Use --force to regenerate.")
                return
        
        print("🔧 Adding embeddings to original format...")
        embeddings_added = add_embeddings_to_original_format(index, args.model, args.endpoint)
    
    elif format_type == 'compressed':
        if args.expand_compressed:
            print("🔧 Expanding compressed format and adding embeddings...")
            index, embeddings_added = expand_compressed_to_original_with_embeddings(index, args.model, args.endpoint)
        else:
            print("❌ Cannot add embeddings to compressed format.")
            print("   Use --expand-compressed to expand to original format with embeddings")
            print("   or run project_index.py without compression first.")
            sys.exit(1)
    
    if embeddings_added == 0:
        print("⚠️  No embeddings were generated.")
        return
    
    # Update stats
    if 'stats' not in index:
        index['stats'] = {}
    index['stats']['embeddings_generated'] = embeddings_added
    index['embeddings_updated_at'] = datetime.now().isoformat()
    
    # Save enhanced index
    output_path = args.output or args.input
    try:
        with open(output_path, 'w') as f:
            json.dump(index, f, separators=(',', ':'))
        print(f"💾 Enhanced index saved to: {output_path}")
        print(f"✅ Generated {embeddings_added} embeddings")
    except Exception as e:
        print(f"❌ Error saving to {output_path}: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()