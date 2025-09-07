#!/usr/bin/env python3
"""
Append Cluster to Embeddings in Index
Step 3 of the embedding workflow: Build similarity cache and append to PROJECT_INDEX.json

This script builds similarity matrices and clustering data from existing embeddings
and appends the results to PROJECT_INDEX.json for fast future queries.

Workflow position: project_index.py → append_embeddings_to_index.py → THIS SCRIPT
"""

__version__ = "0.1.0"

import json
import math
import argparse
import sys
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Callable


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
    
    @staticmethod
    def jaccard_similarity(vec1: List[float], vec2: List[float], threshold: float = 0.1) -> float:
        """Calculate Jaccard similarity by treating vectors as binary."""
        if len(vec1) != len(vec2):
            return 0.0
        
        bin1 = [1 if abs(x) > threshold else 0 for x in vec1]
        bin2 = [1 if abs(x) > threshold else 0 for x in vec2]
        
        intersection = sum(1 for a, b in zip(bin1, bin2) if a == 1 and b == 1)
        union = sum(1 for a, b in zip(bin1, bin2) if a == 1 or b == 1)
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    @staticmethod
    def weighted_cosine_similarity(vec1: List[float], vec2: List[float], weights: List[float] = None) -> float:
        """Calculate weighted cosine similarity."""
        if len(vec1) != len(vec2):
            return 0.0
        
        if weights is None:
            weights = [1.0] * len(vec1)
        elif len(weights) != len(vec1):
            if len(weights) < len(vec1):
                weights = weights + [1.0] * (len(vec1) - len(weights))
            else:
                weights = weights[:len(vec1)]
        
        weighted_vec1 = [a * w for a, w in zip(vec1, weights)]
        weighted_vec2 = [b * w for b, w in zip(vec2, weights)]
        
        return SimilarityAlgorithms.cosine_similarity(weighted_vec1, weighted_vec2)


def get_similarity_algorithm(algorithm_name: str, weights: List[float] = None) -> Callable[[List[float], List[float]], float]:
    """Get similarity algorithm function by name."""
    algorithms = {
        'cosine': SimilarityAlgorithms.cosine_similarity,
        'euclidean': SimilarityAlgorithms.euclidean_similarity,
        'manhattan': SimilarityAlgorithms.manhattan_similarity,
        'dot-product': SimilarityAlgorithms.dot_product_similarity,
        'jaccard': SimilarityAlgorithms.jaccard_similarity,
        'weighted-cosine': lambda v1, v2: SimilarityAlgorithms.weighted_cosine_similarity(v1, v2, weights)
    }
    
    if algorithm_name not in algorithms:
        raise ValueError(f"Unknown algorithm: {algorithm_name}. Available: {list(algorithms.keys())}")
    
    return algorithms[algorithm_name]


def load_weights(weights_path: str) -> List[float]:
    """Load weights from JSON file."""
    try:
        with open(weights_path, 'r') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'weights' in data:
            return data['weights']
        else:
            raise ValueError("Weights file should contain a list or dict with 'weights' key")
    
    except Exception as e:
        print(f"❌ Error loading weights from {weights_path}: {e}")
        sys.exit(1)


def load_project_index(index_path: str = "PROJECT_INDEX.json") -> Dict:
    """Load PROJECT_INDEX.json with embeddings."""
    try:
        with open(index_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: {index_path} not found!")
        print("   Run the embedding workflow first:")
        print("   1. python3 scripts/project_index.py")
        print("   2. python3 scripts/append_embeddings_to_index.py")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in {index_path}: {e}")
        sys.exit(1)


def calculate_embedding_hash(embeddings: List[Dict]) -> str:
    """Calculate hash of all embeddings to detect changes."""
    embedding_data = []
    for item in embeddings:
        embedding_data.append(f"{item['full_name']}:{len(item['embedding'])}")
    
    combined = "|".join(sorted(embedding_data))
    return hashlib.md5(combined.encode()).hexdigest()[:16]


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


def build_similarity_cache(embeddings: List[Dict], algorithms: List[str], 
                          similarity_threshold: float = 0.5, duplicate_threshold: float = 0.9,
                          top_k: int = 10, weights: List[float] = None) -> Dict:
    """Build similarity cache for all specified algorithms."""
    print(f"🔧 Building similarity cache for {len(embeddings)} items...")
    
    cache = {
        "generated_at": datetime.now().isoformat(),
        "embedding_hash": calculate_embedding_hash(embeddings),
        "config": {
            "similarity_threshold": similarity_threshold,
            "duplicate_threshold": duplicate_threshold,
            "top_k": top_k
        },
        "algorithms": {}
    }
    
    for algorithm in algorithms:
        print(f"   Processing {algorithm} algorithm...")
        
        try:
            similarity_func = get_similarity_algorithm(algorithm, weights)
        except ValueError as e:
            print(f"   ❌ Skipping {algorithm}: {e}")
            continue
        
        # Find duplicates
        duplicates = find_duplicates_internal(embeddings, similarity_func, duplicate_threshold)
        
        # Build top similarities for each item
        top_similar = {}
        processed = 0
        
        for i, item1 in enumerate(embeddings):
            similarities = []
            
            for j, item2 in enumerate(embeddings):
                if i == j:
                    continue
                
                try:
                    similarity = similarity_func(item1['embedding'], item2['embedding'])
                    if similarity >= similarity_threshold:
                        similarities.append({
                            "target": item2['full_name'],
                            "score": round(similarity, 4)
                        })
                except Exception as e:
                    continue
            
            # Sort by similarity and keep top_k
            similarities.sort(key=lambda x: x['score'], reverse=True)
            if similarities:
                top_similar[item1['full_name']] = similarities[:top_k]
            
            processed += 1
            if processed % 10 == 0:
                print(f"     Processed {processed}/{len(embeddings)} items...")
        
        # Store algorithm results
        cache["algorithms"][algorithm] = {
            "duplicate_groups": duplicates,
            "top_similar": top_similar,
            "stats": {
                "total_items": len(embeddings),
                "items_with_similar": len(top_similar),
                "duplicate_groups": len(duplicates)
            }
        }
        
        print(f"   ✅ {algorithm}: {len(duplicates)} duplicate groups, {len(top_similar)} items with similarities")
    
    return cache


def find_duplicates_internal(embeddings: List[Dict], similarity_func: Callable, threshold: float) -> List[Dict]:
    """Find duplicate groups using the specified similarity function."""
    duplicates = []
    used_indices = set()
    
    for i, item1 in enumerate(embeddings):
        if i in used_indices:
            continue
        
        similar_group = [{
            "item": item1['full_name'],
            "score": 1.0
        }]
        
        for j, item2 in enumerate(embeddings):
            if i == j or j in used_indices:
                continue
            
            try:
                similarity = similarity_func(item1['embedding'], item2['embedding'])
                if similarity >= threshold:
                    similar_group.append({
                        "item": item2['full_name'],
                        "score": round(similarity, 4)
                    })
                    used_indices.add(j)
            except Exception:
                continue
        
        if len(similar_group) > 1:
            duplicates.append({
                "similarity_range": [min(item['score'] for item in similar_group),
                                   max(item['score'] for item in similar_group)],
                "items": similar_group
            })
            used_indices.add(i)
    
    return duplicates


def save_enhanced_index(index: Dict, output_path: str):
    """Save enhanced index with similarity cache to file."""
    try:
        with open(output_path, 'w') as f:
            json.dump(index, f, separators=(',', ':'))
        print(f"💾 Enhanced index saved to: {output_path}")
    except Exception as e:
        print(f"❌ Error saving to {output_path}: {e}")
        sys.exit(1)


def print_cache_stats(cache: Dict):
    """Print statistics about the similarity cache."""
    print(f"\n📊 Similarity Cache Statistics:")
    print(f"   Generated: {cache['generated_at']}")
    print(f"   Algorithms: {len(cache['algorithms'])}")
    
    for algo_name, algo_data in cache['algorithms'].items():
        stats = algo_data['stats']
        print(f"   • {algo_name}:")
        print(f"     - {stats['total_items']} total items processed")
        print(f"     - {stats['items_with_similar']} items have similar functions")
        print(f"     - {stats['duplicate_groups']} potential duplicate groups")


def main():
    """Main clustering interface - builds and saves similarity cache."""
    parser = argparse.ArgumentParser(
        description='Append similarity clustering data to PROJECT_INDEX.json',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Build similarity cache with default cosine algorithm
  %(prog)s --build-cache
  
  # Build cache with multiple algorithms
  %(prog)s --build-cache --algorithms cosine,euclidean,manhattan
  
  # Custom output file and thresholds
  %(prog)s --build-cache -o ENHANCED_INDEX.json --threshold 0.7
  
  # Build cache with weighted cosine
  %(prog)s --build-cache --algorithm weighted-cosine --weights weights.json

This is Step 3 of the embedding workflow:
  1. python3 scripts/project_index.py
  2. python3 scripts/append_embeddings_to_index.py  
  3. python3 scripts/append_cluster_to_embeddings_in_index.py --build-cache
        '''
    )
    
    parser.add_argument('--version', action='version', version=f'Cluster Append v{__version__}')
    
    # Mode selection (only build-cache for this script)
    parser.add_argument('--build-cache', action='store_true', required=True,
                       help='Build similarity cache and append to index file')
    
    # Algorithm selection
    parser.add_argument('--algorithm', default='cosine',
                       choices=['cosine', 'euclidean', 'manhattan', 'dot-product', 'jaccard', 'weighted-cosine'],
                       help='Single similarity algorithm (default: cosine)')
    parser.add_argument('--algorithms', type=str,
                       help='Comma-separated algorithms for cache building (e.g., "cosine,euclidean")')
    parser.add_argument('--weights', type=str,
                       help='Weights file for weighted-cosine algorithm')
    
    # File I/O
    parser.add_argument('-i', '--input', default='PROJECT_INDEX.json',
                       help='Input index file (default: PROJECT_INDEX.json)')
    parser.add_argument('-o', '--output', type=str,
                       help='Output file for enhanced index (default: same as input)')
    
    # Cache building parameters
    parser.add_argument('-k', '--top-k', type=int, default=10,
                       help='Number of top similar items to cache per function (default: 10)')
    parser.add_argument('-t', '--threshold', type=float, default=0.5,
                       help='Similarity threshold for caching (default: 0.5)')
    parser.add_argument('--duplicate-threshold', type=float, default=0.9,
                       help='Duplicate detection threshold (default: 0.9)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.algorithm == 'weighted-cosine' and not args.weights:
        print("❌ Error: weighted-cosine algorithm requires --weights parameter")
        sys.exit(1)
    
    # Load weights if specified
    weights = None
    if args.weights:
        weights = load_weights(args.weights)
    
    # Load project index
    print(f"📊 Loading project index: {args.input}")
    index = load_project_index(args.input)
    
    # Extract embeddings
    embeddings = extract_embeddings_from_index(index)
    if not embeddings:
        print("❌ No embeddings found! Generate embeddings first:")
        print("   python3 scripts/append_embeddings_to_index.py")
        sys.exit(1)
    
    print(f"✅ Loaded {len(embeddings)} functions/methods with embeddings\n")
    
    # Determine algorithms to use
    algorithms = args.algorithms.split(',') if args.algorithms else [args.algorithm]
    algorithms = [alg.strip() for alg in algorithms]
    
    print(f"🔧 Building similarity cache with algorithms: {', '.join(algorithms)}")
    
    # Build similarity cache
    similarity_cache = build_similarity_cache(
        embeddings, algorithms, args.threshold, 
        args.duplicate_threshold, args.top_k, weights
    )
    
    # Add cache to index
    index['similarity_analysis'] = similarity_cache
    
    # Save enhanced index
    output_path = args.output or args.input
    save_enhanced_index(index, output_path)
    
    # Print statistics
    print_cache_stats(similarity_cache)
    print(f"\n✅ Similarity clustering completed!")
    print(f"💡 Query similar functions with: python3 scripts/query_index.py -q 'your search'")


if __name__ == '__main__':
    main()