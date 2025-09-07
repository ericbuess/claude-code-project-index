#!/usr/bin/env python3
"""
Command handler for /embedded-index slash command
Handles neural embedding commands without multi-line bash issues
"""

import sys
import os
import subprocess
import time
import requests

def run_command(cmd, shell=True):
    """Run a command and return success status"""
    try:
        result = subprocess.run(cmd, shell=shell, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running command: {e}", file=sys.stderr)
        return False

def check_ollama():
    """Check if Ollama is running"""
    try:
        response = requests.get("http://127.0.0.1:11434/api/version", timeout=2)
        return response.status_code == 200
    except:
        return False

def setup_embeddings():
    """Set up neural embeddings"""
    print("🔧 Setting up neural embeddings...")
    
    # Install Python dependencies
    print("📦 Installing Python dependencies...")
    if not run_command("pip install --user requests numpy scikit-learn"):
        print("⚠️  Some dependencies may have failed to install")
    
    # Start Ollama if not running
    if not check_ollama():
        print("🚀 Starting Ollama server...")
        subprocess.Popen(["nix", "run", "nixpkgs#ollama", "--", "serve"], 
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        print("Waiting for Ollama to start...")
        for i in range(10):
            time.sleep(2)
            if check_ollama():
                print("✅ Ollama started successfully")
                break
            print(".", end="", flush=True)
        else:
            print("\n❌ Ollama failed to start")
            return False
    else:
        print("✅ Ollama already running")
    
    # Pull nomic-embed-text model
    print("📥 Pulling nomic-embed-text model (this may take a few minutes)...")
    print("This is a ~270MB download, please be patient...")
    
    try:
        response = requests.post("http://127.0.0.1:11434/api/pull", 
                               json={"name": "nomic-embed-text"}, 
                               stream=True)
        
        for line in response.iter_lines():
            if line:
                import json
                try:
                    data = json.loads(line)
                    if data.get("status") == "success":
                        print("✅ Model downloaded successfully")
                        break
                    elif "pulling" in data.get("status", ""):
                        print(".", end="", flush=True)
                except:
                    continue
        print("")
    except Exception as e:
        print(f"❌ Failed to download model: {e}")
        return False
    
    print("✅ Setup complete!")
    print("💡 Test with: /embedded-index build")
    return True

def main():
    """Main command handler"""
    args = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    
    if args == "setup":
        setup_embeddings()
    
    elif args == "build":
        print("🏗️  Building neural embeddings index...")
        if not check_ollama():
            print("❌ Ollama not running. Try: /embedded-index setup")
            return
        run_command("python3 ~/.claude/scripts/neural_embeddings.py --build")
    
    elif args.startswith("search "):
        query = args[7:]  # Remove "search " prefix
        print(f"🔍 Neural search for: \"{query}\"")
        run_command(f"python3 ~/.claude/scripts/neural_embeddings.py --search \"{query}\"")
    
    elif args.startswith("similar "):
        function = args[8:]  # Remove "similar " prefix
        print(f"🎯 Finding functions similar to: {function}")
        run_command(f"python3 ~/.claude/scripts/neural_embeddings.py --similar \"{function}\"")
    
    elif args == "analyze":
        print("🔬 Neural semantic analysis...")
        run_command("python3 ~/.claude/scripts/neural_embeddings.py --analyze")
    
    else:
        print("🧠 NEURAL EMBEDDED INDEX")
        print("")
        print("Commands:")
        print("  setup                    - Install Ollama + nomic-embed-text")
        print("  build                    - Generate neural embeddings")
        print("  search <query>          - Natural language code search")
        print("  similar <function>      - Find semantically similar functions")
        print("  analyze                 - Discover semantic clusters")
        print("")
        print("🚀 Capabilities:")
        print("  • Natural language search: 'find error handling'")
        print("  • Cross-language similarity detection")
        print("  • Intent-based code clustering")
        print("  • Semantic duplicate detection")
        print("")
        print("💡 First time? Run: /embedded-index setup")

if __name__ == "__main__":
    main()