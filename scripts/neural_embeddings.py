#!/usr/bin/env python3
"""
Simple neural embeddings for code using Ollama + nomic-embed-text
No over-engineering - just practical semantic code search and analysis
"""

import json
import sys
import os
import requests
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

OLLAMA_URL = "http://127.0.0.1:11434"
EMBEDDING_MODEL = "nomic-embed-text"

def get_embedding(text: str) -> List[float]:
    """Get embedding from Ollama"""
    try:
        response = requests.post(f"{OLLAMA_URL}/api/embeddings", json={
            "model": EMBEDDING_MODEL,
            "prompt": text
        })
        if response.status_code == 200:
            return response.json()["embedding"]
        else:
            print(f"Error getting embedding: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error connecting to Ollama: {e}")
        return []

def extract_code_chunks(index_data: Dict) -> List[Dict]:
    """Extract meaningful code chunks from PROJECT_INDEX.json"""
    chunks = []
    
    for file_path, file_info in index_data.get("files", {}).items():
        if not file_info.get("parsed", False):
            continue
            
        # Add functions
        for func_name, func_info in file_info.get("functions", {}).items():
            chunks.append({
                "type": "function",
                "file": file_path,
                "name": func_name,
                "signature": func_info.get("signature", ""),
                "doc": func_info.get("doc", ""),
                "content": f"Function {func_name} in {file_path}: {func_info.get('doc', '')}"
            })
        
        # Add classes
        for class_name, class_info in file_info.get("classes", {}).items():
            chunks.append({
                "type": "class", 
                "file": file_path,
                "name": class_name,
                "doc": class_info.get("doc", ""),
                "content": f"Class {class_name} in {file_path}: {class_info.get('doc', '')}"
            })
            
            # Add methods
            for method_name, method_info in class_info.get("methods", {}).items():
                chunks.append({
                    "type": "method",
                    "file": file_path,
                    "class": class_name,
                    "name": method_name,
                    "signature": method_info.get("signature", ""),
                    "doc": method_info.get("doc", ""),
                    "content": f"Method {class_name}.{method_name} in {file_path}: {method_info.get('doc', '')}"
                })
    
    return chunks

def build_embeddings():
    """Build neural embeddings index"""
    print("🧠 Loading PROJECT_INDEX.json...")
    
    if not os.path.exists("PROJECT_INDEX.json"):
        print("❌ No PROJECT_INDEX.json found. Run /semantic-index first.")
        return
    
    with open("PROJECT_INDEX.json", "r") as f:
        index_data = json.load(f)
    
    print("📝 Extracting code chunks...")
    chunks = extract_code_chunks(index_data)
    print(f"Found {len(chunks)} code chunks")
    
    print("🚀 Generating embeddings...")
    embeddings_data = []
    
    for i, chunk in enumerate(chunks):
        if i % 10 == 0:
            print(f"Progress: {i}/{len(chunks)}")
            
        embedding = get_embedding(chunk["content"])
        if embedding:
            embeddings_data.append({
                "chunk": chunk,
                "embedding": embedding
            })
    
    # Save to NEURAL_INDEX.json
    neural_index = {
        "model": EMBEDDING_MODEL,
        "created_at": index_data.get("indexed_at"),
        "total_chunks": len(embeddings_data),
        "embeddings": embeddings_data
    }
    
    with open("NEURAL_INDEX.json", "w") as f:
        json.dump(neural_index, f, indent=2)
    
    print(f"✅ Neural index saved with {len(embeddings_data)} embeddings")

def semantic_search(query: str, top_k: int = 5):
    """Search for code using natural language"""
    if not os.path.exists("NEURAL_INDEX.json"):
        print("❌ No neural index found. Run /embedded-index build first.")
        return
    
    print(f"🔍 Searching for: {query}")
    
    # Get query embedding
    query_embedding = get_embedding(query)
    if not query_embedding:
        print("❌ Failed to get query embedding")
        return
    
    # Load neural index
    with open("NEURAL_INDEX.json", "r") as f:
        neural_index = json.load(f)
    
    # Calculate similarities
    similarities = []
    for item in neural_index["embeddings"]:
        chunk_embedding = item["embedding"]
        similarity = cosine_similarity([query_embedding], [chunk_embedding])[0][0]
        similarities.append({
            "similarity": similarity,
            "chunk": item["chunk"]
        })
    
    # Sort by similarity
    similarities.sort(key=lambda x: x["similarity"], reverse=True)
    
    print(f"\n🎯 Top {top_k} results:")
    for i, result in enumerate(similarities[:top_k]):
        chunk = result["chunk"]
        sim_score = result["similarity"]
        print(f"\n{i+1}. {chunk['type'].title()}: {chunk['name']} (similarity: {sim_score:.3f})")
        print(f"   📁 {chunk['file']}")
        if chunk.get("doc"):
            print(f"   📝 {chunk['doc'][:100]}...")

def find_similar_functions(target_function: str, top_k: int = 5):
    """Find functions similar to a specific function"""
    if not os.path.exists("NEURAL_INDEX.json"):
        print("❌ No neural index found. Run /embedded-index build first.")
        return
    
    with open("NEURAL_INDEX.json", "r") as f:
        neural_index = json.load(f)
    
    # Find target function
    target_chunk = None
    for item in neural_index["embeddings"]:
        if item["chunk"]["name"] == target_function:
            target_chunk = item
            break
    
    if not target_chunk:
        print(f"❌ Function '{target_function}' not found")
        return
    
    target_embedding = target_chunk["embedding"]
    print(f"🎯 Finding functions similar to: {target_function}")
    
    # Calculate similarities
    similarities = []
    for item in neural_index["embeddings"]:
        if item["chunk"]["name"] == target_function:
            continue  # Skip self
            
        chunk_embedding = item["embedding"] 
        similarity = cosine_similarity([target_embedding], [chunk_embedding])[0][0]
        similarities.append({
            "similarity": similarity,
            "chunk": item["chunk"]
        })
    
    # Sort and show results
    similarities.sort(key=lambda x: x["similarity"], reverse=True)
    
    print(f"\n🔗 Most similar functions:")
    for i, result in enumerate(similarities[:top_k]):
        chunk = result["chunk"]
        sim_score = result["similarity"]
        print(f"\n{i+1}. {chunk['name']} (similarity: {sim_score:.3f})")
        print(f"   📁 {chunk['file']}")
        if chunk.get("doc"):
            print(f"   📝 {chunk['doc'][:80]}...")

def analyze_semantic_clusters():
    """Find semantic clusters in the codebase"""
    if not os.path.exists("NEURAL_INDEX.json"):
        print("❌ No neural index found. Run /embedded-index build first.")
        return
    
    with open("NEURAL_INDEX.json", "r") as f:
        neural_index = json.load(f)
    
    print("🔬 Analyzing semantic clusters...")
    
    # Simple clustering: find high-similarity pairs
    clusters = []
    processed = set()
    
    for i, item1 in enumerate(neural_index["embeddings"]):
        if i in processed:
            continue
            
        cluster = [item1]
        processed.add(i)
        
        for j, item2 in enumerate(neural_index["embeddings"][i+1:], i+1):
            if j in processed:
                continue
                
            similarity = cosine_similarity([item1["embedding"]], [item2["embedding"]])[0][0]
            
            if similarity > 0.8:  # High similarity threshold
                cluster.append(item2)
                processed.add(j)
        
        if len(cluster) > 1:
            clusters.append(cluster)
    
    print(f"\n📊 Found {len(clusters)} semantic clusters:")
    
    for i, cluster in enumerate(clusters):
        print(f"\n🔗 Cluster {i+1} ({len(cluster)} items):")
        for item in cluster:
            chunk = item["chunk"]
            print(f"   • {chunk['type']}: {chunk['name']} ({chunk['file']})")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Neural embeddings for code")
    parser.add_argument("--build", action="store_true", help="Build embeddings index")
    parser.add_argument("--search", type=str, help="Semantic search query")
    parser.add_argument("--similar", type=str, help="Find similar functions")
    parser.add_argument("--analyze", action="store_true", help="Analyze semantic patterns")
    parser.add_argument("--clusters", action="store_true", help="Show semantic clusters")
    
    args = parser.parse_args()
    
    if args.build:
        build_embeddings()
    elif args.search:
        semantic_search(args.search)
    elif args.similar:
        find_similar_functions(args.similar)
    elif args.analyze:
        print("🧠 Neural Semantic Analysis")
        analyze_semantic_clusters()
    elif args.clusters:
        analyze_semantic_clusters()
    else:
        print("Neural Embeddings Tools")
        print("--build: Generate embeddings")
        print("--search 'query': Semantic search") 
        print("--similar func_name: Find similar functions")
        print("--analyze: Show semantic clusters")

if __name__ == "__main__":
    main()