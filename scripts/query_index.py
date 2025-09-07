#!/usr/bin/env python3
"""
Query Index - Search and query functionality for PROJECT_INDEX.json
Find similar code patterns using cached neural embeddings

Features:
- Query similar functions using natural language
- Show cached duplicate groups
- Multiple similarity algorithms
- Real-time and cached query modes
"""

__version__ = "0.1.0"

import json
import math
import argparse
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Callable

# Import shared algorithms and utilities from append_cluster script
# (These will be the same functions but used for querying)

class SimilarityAlgorithms:
    """Collection of similarity algorithms for vector comparison."""
    
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors (default algorithm)."""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    @staticmethod
    def euclidean_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate similarity based on Euclidean distance."""
        if len(vec1) != len(vec2):
            return 0.0
        
        distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(vec1, vec2)))
        return 1.0 / (1.0 + distance)
    
    @staticmethod
    def manhattan_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate similarity based on Manhattan distance."""
        if len(vec1) != len(vec2):
            return 0.0
        
        distance = sum(abs(a - b) for a, b in zip(vec1, vec2))
        return 1.0 / (1.0 + distance)
    
    @staticmethod
    def dot_product_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate raw dot product similarity."""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        return (math.tanh(dot_product) + 1) / 2


def get_similarity_algorithm(algorithm_name: str) -> Callable[[List[float], List[float]], float]:
    """Get similarity algorithm function by name."""
    algorithms = {
        'cosine': SimilarityAlgorithms.cosine_similarity,
        'euclidean': SimilarityAlgorithms.euclidean_similarity,
        'manhattan': SimilarityAlgorithms.manhattan_similarity,
        'dot-product': SimilarityAlgorithms.dot_product_similarity,
    }
    
    if algorithm_name not in algorithms:
        raise ValueError(f"Unknown algorithm: {algorithm_name}. Available: {list(algorithms.keys())}")
    
    return algorithms[algorithm_name]


def load_project_index(index_path: str = "PROJECT_INDEX.json") -> Dict:
    """Load PROJECT_INDEX.json with embeddings."""
    try:
        with open(index_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: {index_path} not found!")
        print("   Run the 3-step workflow first:")
        print("   1. python3 scripts/project_index.py")
        print("   2. python3 scripts/append_embeddings_to_index.py")
        print("   3. python3 scripts/append_cluster_to_embeddings_in_index.py --build-cache")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in {index_path}: {e}")
        sys.exit(1)


def extract_embeddings_from_index(index: Dict) -> List[Dict]:
    """Extract all embeddings with metadata from the project index."""
    embeddings = []
    
    # Extract from files section with full embedding data
    files_data = index.get('files', {})
    
    for file_path, file_data in files_data.items():
        if not isinstance(file_data, dict):
            continue
        
        # Extract functions
        for func_name, func_data in file_data.get('functions', {}).items():
            if isinstance(func_data, dict) and 'embedding' in func_data:
                embeddings.append({
                    'type': 'function',
                    'name': func_name,
                    'file': file_path,
                    'line': func_data.get('line', 0),
                    'signature': func_data.get('signature', '()'),
                    'doc': func_data.get('doc', ''),
                    'embedding': func_data['embedding'],
                    'full_name': f"{file_path}:{func_name}",
                    'calls': func_data.get('calls', []),
                    'called_by': func_data.get('called_by', [])
                })
        
        # Extract methods from classes
        for class_name, class_data in file_data.get('classes', {}).items():
            if isinstance(class_data, dict):
                for method_name, method_data in class_data.get('methods', {}).items():
                    if isinstance(method_data, dict) and 'embedding' in method_data:
                        embeddings.append({
                            'type': 'method',
                            'name': method_name,
                            'class': class_name,
                            'file': file_path,
                            'line': method_data.get('line', 0),
                            'signature': method_data.get('signature', '()'),
                            'doc': method_data.get('doc', ''),
                            'embedding': method_data['embedding'],
                            'full_name': f"{file_path}:{class_name}.{method_name}",
                            'calls': method_data.get('calls', []),
                            'called_by': method_data.get('called_by', [])
                        })
    
    return embeddings


def generate_embedding_for_query(query: str, model_name: str = "nomic-embed-text", 
                                endpoint: str = "http://localhost:11434") -> Optional[List[float]]:
    """Generate embedding for a query string."""
    try:
        url = f"{endpoint}/api/embeddings"
        data = json.dumps({
            "model": model_name,
            "prompt": query
        }).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('embedding')
    except Exception as e:
        print(f"❌ Error generating embedding for query: {e}")
        return None


def query_similar_functions(query: str, index: Dict, algorithm: str = 'cosine',
                          top_k: int = 10, threshold: float = 0.5,
                          endpoint: str = "http://localhost:11434",
                          model_name: str = "nomic-embed-text") -> List[Tuple[Dict, float]]:
    """Query for similar functions using natural language."""
    # Generate query embedding
    query_embedding = generate_embedding_for_query(query, model_name, endpoint)
    if not query_embedding:
        return []
    
    # Get algorithm function
    try:
        similarity_func = get_similarity_algorithm(algorithm)
    except ValueError as e:
        print(f"❌ {e}")
        return []
    
    # Get all embeddings
    embeddings = extract_embeddings_from_index(index)
    if not embeddings:
        print("❌ No embeddings found in index!")
        return []
    
    # Calculate similarities
    results = []
    for item in embeddings:
        try:
            similarity = similarity_func(query_embedding, item['embedding'])
            if similarity >= threshold:
                results.append((item, similarity))
        except Exception:
            continue
    
    # Sort and return top results
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]


def print_query_results(results: List[Tuple[Dict, float]], query: str = None, algorithm: str = 'cosine'):
    """Print similarity search results."""
    if not results:
        print("🤷 No similar code found.")
        return
    
    if query:
        print(f"🔍 Similar to: '{query}' (using {algorithm} algorithm)")
    print(f"📊 Found {len(results)} similar items:\n")
    
    for i, (item, similarity) in enumerate(results, 1):
        print(f"#{i} 🎯 Similarity: {similarity:.3f}")
        print(f"   📁 {item['file']}:{item['line']}")
        
        if item['type'] == 'function':
            print(f"   🔧 Function: {item['name']}{item['signature']}")
        else:
            print(f"   🏷️  Method: {item['class']}.{item['name']}{item['signature']}")
        
        if item['doc']:
            print(f"   📝 {item['doc']}")
        
        # Show call relationships if available
        if item.get('calls'):
            calls = ', '.join(item['calls'][:3])
            if len(item['calls']) > 3:
                calls += f" (+{len(item['calls'])-3} more)"
            print(f"   📞 Calls: {calls}")
        
        print()


def print_cached_duplicates(cache: Dict, algorithm: str = 'cosine'):
    """Print duplicate groups from cache."""
    if 'similarity_analysis' not in cache:
        print("❌ No similarity cache found. Build cache first:")
        print("   python3 scripts/append_cluster_to_embeddings_in_index.py --build-cache")
        return
    
    similarity_cache = cache['similarity_analysis']
    if algorithm not in similarity_cache.get('algorithms', {}):
        print(f"❌ No cache data found for algorithm: {algorithm}")
        return
    
    duplicates = similarity_cache['algorithms'][algorithm].get('duplicate_groups', [])
    
    if not duplicates:
        print("✅ No potential duplicates found.")
        return
    
    print(f"⚠️  Found {len(duplicates)} groups of potentially duplicate code (using {algorithm} algorithm):\n")
    
    for i, group in enumerate(duplicates, 1):
        items = group['items']
        sim_range = group['similarity_range']
        print(f"Group #{i} ({len(items)} similar items, similarity: {sim_range[0]:.3f}-{sim_range[1]:.3f}):")
        
        for item in items:
            print(f"  🎯 {item['score']:.3f} - {item['item']}")
        print()


def main():
    """Main query interface."""
    parser = argparse.ArgumentParser(
        description='Query and search PROJECT_INDEX.json for similar code',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Query similar functions
  %(prog)s -q "authentication function"
  %(prog)s -q "validate email" --algorithm euclidean
  
  # Show cached duplicates
  %(prog)s --duplicates --algorithm cosine
  
  # Custom settings
  %(prog)s -q "error handling" --top-k 5 --threshold 0.7
        '''
    )
    
    parser.add_argument('--version', action='version', version=f'Query Index v{__version__}')
    
    # Mode selection
    parser.add_argument('-q', '--query', type=str,
                       help='Search query for similar functions')
    parser.add_argument('--duplicates', action='store_true',
                       help='Show cached duplicate groups')
    
    # Algorithm selection
    parser.add_argument('--algorithm', default='cosine',
                       choices=['cosine', 'euclidean', 'manhattan', 'dot-product'],
                       help='Similarity algorithm (default: cosine)')
    
    # File I/O
    parser.add_argument('-i', '--input', default='PROJECT_INDEX.json',
                       help='Input index file (default: PROJECT_INDEX.json)')
    
    # Search parameters
    parser.add_argument('-k', '--top-k', type=int, default=10,
                       help='Number of top results (default: 10)')
    parser.add_argument('-t', '--threshold', type=float, default=0.5,
                       help='Similarity threshold (default: 0.5)')
    
    # Ollama settings
    parser.add_argument('--embed-model', default='nomic-embed-text',
                       help='Ollama model for embeddings (default: nomic-embed-text)')
    parser.add_argument('--embed-endpoint', default='http://localhost:11434',
                       help='Ollama API endpoint (default: http://localhost:11434)')
    
    args = parser.parse_args()
    
    if not any([args.query, args.duplicates]):
        print("❌ Error: Must specify --query or --duplicates")
        parser.print_help()
        sys.exit(1)
    
    # Load project index
    print(f"📊 Loading project index: {args.input}")
    index = load_project_index(args.input)
    
    # Handle duplicate display
    if args.duplicates:
        print_cached_duplicates(index, args.algorithm)
        return
    
    # Handle query
    if args.query:
        print(f"🔍 Searching for: '{args.query}' (using {args.algorithm})")
        
        results = query_similar_functions(
            args.query, index, args.algorithm,
            args.top_k, args.threshold,
            args.embed_endpoint, args.embed_model
        )
        
        print_query_results(results, args.query, args.algorithm)


if __name__ == '__main__':
    main()