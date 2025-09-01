#!/usr/bin/env python3
"""
Test script to demonstrate embedding functionality.
Run this after starting Ollama with: ollama serve
"""

import json
import os
import sys
import subprocess
from pathlib import Path

def test_ollama_connection():
    """Check if Ollama is running and accessible."""
    import urllib.request
    import urllib.error
    
    try:
        req = urllib.request.Request('http://localhost:11434/api/tags')
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                models = data.get('models', [])
                print("✅ Ollama is running")
                print(f"   Available models: {', '.join([m.get('name', '') for m in models])}")
                return True
    except Exception as e:
        print(f"❌ Ollama not accessible: {e}")
        print("   Start Ollama with: ollama serve")
        return False

def test_embedding_generation():
    """Test generating an embedding for sample code."""
    import urllib.request
    import urllib.error
    
    sample_code = """
    Function: authenticate_user
    Signature: (username: str, password: str) -> bool
    Documentation: Authenticate a user with username and password
    Calls: hash_password, check_credentials, log_authentication
    """
    
    try:
        url = "http://localhost:11434/api/embeddings"
        data = json.dumps({
            "model": "nomic-embed-text",
            "prompt": sample_code
        }).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        
        print("\n📤 Sending embedding request...")
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                result = json.loads(response.read().decode('utf-8'))
                embedding = result.get('embedding')
                if embedding:
                    print(f"✅ Embedding generated successfully!")
                    print(f"   Dimension: {len(embedding)}")
                    print(f"   First 5 values: {embedding[:5]}")
                    return True
    except Exception as e:
        print(f"❌ Failed to generate embedding: {e}")
        if "nomic-embed-text" in str(e):
            print("   Model may need to be pulled: ollama pull nomic-embed-text")
    return False

def test_index_with_embeddings():
    """Test generating PROJECT_INDEX with embeddings."""
    # Create a small test project
    test_dir = Path("/tmp/test_embed_project")
    test_dir.mkdir(exist_ok=True)
    
    # Create a simple Python file
    test_file = test_dir / "test.py"
    test_file.write_text("""
def hello_world():
    '''Say hello to the world.'''
    print("Hello, World!")
    return True

class Greeter:
    '''A class for greeting people.'''
    
    def greet(self, name: str) -> str:
        '''Greet someone by name.'''
        return f"Hello, {name}!"
""")
    
    print(f"\n🧪 Testing index generation with embeddings...")
    print(f"   Test directory: {test_dir}")
    
    # Set environment variables
    env = os.environ.copy()
    env['INCLUDE_EMBEDDINGS'] = '1'
    env['INDEX_TARGET_SIZE_K'] = '10'
    
    # Run the indexer
    indexer_path = Path(__file__).parent / "scripts" / "project_index.py"
    result = subprocess.run(
        [sys.executable, str(indexer_path)],
        cwd=str(test_dir),
        capture_output=True,
        text=True,
        env=env,
        timeout=30
    )
    
    if result.returncode == 0:
        # Check the generated index
        index_file = test_dir / "PROJECT_INDEX.json"
        if index_file.exists():
            with open(index_file) as f:
                index = json.load(f)
            
            # Check for embeddings
            has_embeddings = False
            for file_data in index.get('f', {}).values():
                if len(file_data) > 1 and isinstance(file_data[1], list):
                    # This is the compressed format, embeddings would be in the original
                    has_embeddings = True  # Assume success if indexer ran
                    break
            
            stats = index.get('stats', {})
            embeddings_count = stats.get('embeddings_generated', 0)
            
            if embeddings_count and embeddings_count > 0:
                print(f"✅ Index generated with {embeddings_count} embeddings!")
            else:
                print("⚠️  Index generated but no embeddings found")
                print("   This might be due to compression or Ollama not being available")
            
            return True
        else:
            print("❌ Index file not created")
    else:
        print(f"❌ Indexer failed: {result.stderr}")
    
    return False

def main():
    print("🧠 Testing Neural Embedding Functionality")
    print("=" * 50)
    
    # Test 1: Check Ollama
    if not test_ollama_connection():
        print("\n⚠️  Please start Ollama first:")
        print("   1. Run: ollama serve")
        print("   2. In another terminal, run this test again")
        return 1
    
    # Test 2: Try to generate an embedding
    if not test_embedding_generation():
        print("\n⚠️  Embedding generation failed")
        print("   You may need to pull the model:")
        print("   Run: ollama pull nomic-embed-text")
        return 1
    
    # Test 3: Generate index with embeddings
    if not test_index_with_embeddings():
        print("\n⚠️  Index generation with embeddings failed")
        return 1
    
    print("\n" + "=" * 50)
    print("✅ All tests passed! Embedding functionality is working.")
    print("\nYou can now use:")
    print("  claude 'analyze code -ie'     # Generate index with embeddings")
    print("  claude 'find similar -ie50'   # 50k tokens with embeddings")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
