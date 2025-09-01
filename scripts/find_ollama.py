#!/usr/bin/env python3
"""
Ollama finder and model manager for PROJECT_INDEX
Centralized Ollama detection, model management, and embedding generation

Features:
- Robust Ollama service detection
- Model availability checking and auto-pulling
- Embedding generation with error handling
- Platform-specific installation guidance
- Status reporting and diagnostics

Usage: python3 scripts/find_ollama.py [OPTIONS]
"""

__version__ = "0.1.0"

import json
import sys
import urllib.request
import urllib.error
import subprocess
import time
import platform
from typing import Dict, List, Optional, Tuple


class OllamaManager:
    """Centralized Ollama service and model management."""
    
    def __init__(self, endpoint: str = "http://localhost:11434", timeout: int = 10):
        self.endpoint = endpoint.rstrip('/')
        self.timeout = timeout
        self.default_model = "nomic-embed-text"
    
    def check_ollama_running(self) -> Tuple[bool, str]:
        """Check if Ollama service is running and accessible."""
        try:
            url = f"{self.endpoint}/api/tags"
            req = urllib.request.Request(url)
            
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    return True, "Ollama service is running"
                else:
                    return False, f"Ollama responded with status {response.status}"
        
        except urllib.error.URLError as e:
            if "Connection refused" in str(e):
                return False, "Ollama service not running (connection refused)"
            elif "timeout" in str(e).lower():
                return False, "Ollama service timeout (may be starting up)"
            else:
                return False, f"Ollama service error: {e}"
        except Exception as e:
            return False, f"Unexpected error checking Ollama: {e}"
    
    def get_available_models(self) -> Tuple[bool, List[str], str]:
        """Get list of available models from Ollama."""
        try:
            url = f"{self.endpoint}/api/tags"
            req = urllib.request.Request(url)
            
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    models = [model['name'] for model in data.get('models', [])]
                    return True, models, "Successfully retrieved model list"
                else:
                    return False, [], f"HTTP {response.status}"
        
        except Exception as e:
            return False, [], str(e)
    
    def is_model_available(self, model_name: str) -> Tuple[bool, str]:
        """Check if a specific model is available locally."""
        success, models, error = self.get_available_models()
        if not success:
            return False, f"Could not check models: {error}"
        
        # Check for exact match or partial match (models often have tags)
        for model in models:
            if model == model_name or model.startswith(f"{model_name}:"):
                return True, f"Model '{model_name}' is available as '{model}'"
        
        return False, f"Model '{model_name}' not found (available: {', '.join(models[:3])}{'...' if len(models) > 3 else ''})"
    
    def pull_model(self, model_name: str, show_progress: bool = True) -> Tuple[bool, str]:
        """Pull a model from Ollama registry."""
        try:
            url = f"{self.endpoint}/api/pull"
            data = json.dumps({"name": model_name}).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            
            if show_progress:
                print(f"🔄 Pulling model '{model_name}'... (this may take a few minutes)", file=sys.stderr)
            
            with urllib.request.urlopen(req, timeout=300) as response:  # 5 minute timeout for model pulling
                if response.status == 200:
                    # Read the streaming response
                    while True:
                        line = response.readline()
                        if not line:
                            break
                        
                        try:
                            chunk = json.loads(line.decode('utf-8'))
                            if show_progress and 'status' in chunk:
                                status = chunk['status']
                                if 'completed' in chunk and 'total' in chunk:
                                    completed = chunk['completed']
                                    total = chunk['total']
                                    percent = (completed / total * 100) if total > 0 else 0
                                    print(f"\r   {status}: {percent:.1f}%", end='', file=sys.stderr)
                                elif status != "pulling manifest":  # Avoid too much noise
                                    print(f"\r   {status}...", end='', file=sys.stderr)
                        except json.JSONDecodeError:
                            continue
                    
                    if show_progress:
                        print(f"\n✅ Model '{model_name}' pulled successfully", file=sys.stderr)
                    
                    return True, f"Model '{model_name}' pulled successfully"
                else:
                    return False, f"HTTP {response.status}"
        
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False, f"Model '{model_name}' not found in registry"
            else:
                return False, f"HTTP error {e.code}: {e.reason}"
        except Exception as e:
            return False, f"Error pulling model: {e}"
    
    def ensure_model_available(self, model_name: str = None) -> Tuple[bool, str]:
        """Ensure a model is available, pulling it if necessary."""
        if model_name is None:
            model_name = self.default_model
        
        # First check if Ollama is running
        running, error = self.check_ollama_running()
        if not running:
            return False, error
        
        # Check if model is already available
        available, status = self.is_model_available(model_name)
        if available:
            return True, status
        
        # Try to pull the model
        print(f"🔍 Model '{model_name}' not found locally, attempting to pull...", file=sys.stderr)
        success, error = self.pull_model(model_name)
        if success:
            return True, f"Model '{model_name}' is now available"
        else:
            return False, f"Failed to pull model '{model_name}': {error}"
    
    def generate_embedding(self, text: str, model_name: str = None) -> Tuple[bool, Optional[List[float]], str]:
        """Generate embedding for text using specified model."""
        if model_name is None:
            model_name = self.default_model
        
        # Ensure model is available
        available, error = self.ensure_model_available(model_name)
        if not available:
            return False, None, error
        
        try:
            url = f"{self.endpoint}/api/embeddings"
            data = json.dumps({
                "model": model_name,
                "prompt": text
            }).encode('utf-8')
            
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status == 200:
                    result = json.loads(response.read().decode('utf-8'))
                    embedding = result.get('embedding')
                    if embedding:
                        return True, embedding, f"Generated {len(embedding)}-dimensional embedding"
                    else:
                        return False, None, "No embedding in response"
                else:
                    return False, None, f"HTTP {response.status}"
        
        except Exception as e:
            return False, None, f"Error generating embedding: {e}"
    
    def test_embedding_generation(self) -> Tuple[bool, str]:
        """Test embedding generation with a simple example."""
        test_text = "def test_function(): return 'hello world'"
        success, embedding, error = self.generate_embedding(test_text)
        
        if success and embedding:
            return True, f"✅ Embedding test passed (generated {len(embedding)}-dimensional vector)"
        else:
            return False, f"❌ Embedding test failed: {error}"
    
    def get_status(self) -> Dict:
        """Get comprehensive status report."""
        status = {
            "ollama_running": False,
            "ollama_error": None,
            "models_available": [],
            "models_error": None,
            "default_model_available": False,
            "default_model_error": None,
            "embedding_test": False,
            "embedding_error": None,
            "endpoint": self.endpoint,
            "default_model": self.default_model
        }
        
        # Check if Ollama is running
        running, error = self.check_ollama_running()
        status["ollama_running"] = running
        if not running:
            status["ollama_error"] = error
            return status  # No point checking further if Ollama isn't running
        
        # Get available models
        success, models, error = self.get_available_models()
        if success:
            status["models_available"] = models
        else:
            status["models_error"] = error
        
        # Check default model
        available, error = self.is_model_available(self.default_model)
        status["default_model_available"] = available
        if not available:
            status["default_model_error"] = error
        
        # Test embedding generation
        if available:  # Only test if default model is available
            test_success, test_error = self.test_embedding_generation()
            status["embedding_test"] = test_success
            if not test_success:
                status["embedding_error"] = test_error
        
        return status


def show_install_guide():
    """Show platform-specific Ollama installation instructions."""
    system = platform.system().lower()
    
    print("📦 Ollama Installation Guide", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    print("", file=sys.stderr)
    
    if system == "darwin":  # macOS
        print("🍎 macOS Installation:", file=sys.stderr)
        print("  • Download from: https://ollama.ai/download", file=sys.stderr)
        print("  • Homebrew: brew install ollama", file=sys.stderr)
        print("  • MacPorts: sudo port install ollama", file=sys.stderr)
    
    elif system == "linux":
        print("🐧 Linux Installation:", file=sys.stderr)
        print("  • Curl installer: curl -fsSL https://ollama.ai/install.sh | sh", file=sys.stderr)
        print("  • Manual download: https://ollama.ai/download", file=sys.stderr)
        print("  • Debian/Ubuntu: Download .deb from releases", file=sys.stderr)
        print("  • Fedora/RHEL: Download .rpm from releases", file=sys.stderr)
    
    elif system == "windows":
        print("🪟 Windows Installation:", file=sys.stderr)
        print("  • Download from: https://ollama.ai/download", file=sys.stderr)
        print("  • Windows installer (.exe) available", file=sys.stderr)
    
    else:
        print(f"❓ {system.capitalize()} Installation:", file=sys.stderr)
        print("  • Check: https://ollama.ai/download", file=sys.stderr)
    
    print("", file=sys.stderr)
    print("🚀 After Installation:", file=sys.stderr)
    print("  1. Start Ollama: ollama serve", file=sys.stderr)
    print("  2. Test installation: ollama list", file=sys.stderr)
    print("  3. Pull embedding model: ollama pull nomic-embed-text", file=sys.stderr)
    print("", file=sys.stderr)
    print("💡 For automatic startup:", file=sys.stderr)
    print("  • macOS: Ollama app starts automatically", file=sys.stderr)
    print("  • Linux: Set up systemd service", file=sys.stderr)
    print("  • Windows: Set up Windows service", file=sys.stderr)
    print("", file=sys.stderr)


def print_status(status: Dict):
    """Print formatted status report."""
    print("🔍 Ollama Status Report", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    print("", file=sys.stderr)
    
    # Ollama service status
    if status["ollama_running"]:
        print("✅ Ollama service: Running", file=sys.stderr)
        print(f"   Endpoint: {status['endpoint']}", file=sys.stderr)
    else:
        print("❌ Ollama service: Not running", file=sys.stderr)
        print(f"   Error: {status['ollama_error']}", file=sys.stderr)
        print("", file=sys.stderr)
        print("💡 To start Ollama:", file=sys.stderr)
        print("   ollama serve", file=sys.stderr)
        return
    
    # Models status
    if status.get("models_available"):
        print(f"📦 Available models: {len(status['models_available'])}", file=sys.stderr)
        for model in status["models_available"][:5]:  # Show first 5
            print(f"   • {model}", file=sys.stderr)
        if len(status["models_available"]) > 5:
            print(f"   ... and {len(status['models_available']) - 5} more", file=sys.stderr)
    else:
        print("❌ Models: Could not retrieve list", file=sys.stderr)
        if status.get("models_error"):
            print(f"   Error: {status['models_error']}", file=sys.stderr)
    
    print("", file=sys.stderr)
    
    # Default model status
    if status["default_model_available"]:
        print(f"✅ Default model '{status['default_model']}': Available", file=sys.stderr)
    else:
        print(f"❌ Default model '{status['default_model']}': Not available", file=sys.stderr)
        if status.get("default_model_error"):
            print(f"   Error: {status['default_model_error']}", file=sys.stderr)
        print("   💡 To install:", file=sys.stderr)
        print(f"      ollama pull {status['default_model']}", file=sys.stderr)
        return
    
    # Embedding test status
    if status["embedding_test"]:
        print("✅ Embedding generation: Working", file=sys.stderr)
    else:
        print("❌ Embedding generation: Failed", file=sys.stderr)
        if status.get("embedding_error"):
            print(f"   Error: {status['embedding_error']}", file=sys.stderr)
    
    print("", file=sys.stderr)
    print("🎉 Ollama is ready for embedding generation!", file=sys.stderr)


def main():
    """Command-line interface for Ollama management."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Ollama finder and model manager for PROJECT_INDEX',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s --check                              # Quick availability check
  %(prog)s --status                             # Detailed status report
  %(prog)s --ensure-model nomic-embed-text      # Ensure model is available
  %(prog)s --test-embedding                     # Test embedding generation
  %(prog)s --install-guide                      # Show installation instructions
  %(prog)s --pull-model mxbai-embed-large       # Pull a specific model

Return codes:
  0: Success (Ollama ready for embeddings)
  1: Ollama not running
  2: Model not available
  3: Embedding generation failed
        '''
    )
    
    parser.add_argument('--version', action='version', version=f'find_ollama v{__version__}')
    
    parser.add_argument('--check', action='store_true',
                       help='Quick check if Ollama is running')
    
    parser.add_argument('--status', action='store_true',
                       help='Detailed status report')
    
    parser.add_argument('--ensure-model', type=str, metavar='MODEL',
                       help='Ensure a model is available (pull if needed)')
    
    parser.add_argument('--pull-model', type=str, metavar='MODEL',
                       help='Pull a specific model')
    
    parser.add_argument('--test-embedding', action='store_true',
                       help='Test embedding generation')
    
    parser.add_argument('--install-guide', action='store_true',
                       help='Show installation instructions')
    
    parser.add_argument('--endpoint', default='http://localhost:11434',
                       help='Ollama API endpoint (default: http://localhost:11434)')
    
    parser.add_argument('--timeout', type=int, default=10,
                       help='Request timeout in seconds (default: 10)')
    
    parser.add_argument('--model', default='nomic-embed-text',
                       help='Default embedding model (default: nomic-embed-text)')
    
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Minimal output (for scripting)')
    
    args = parser.parse_args()
    
    # Show installation guide
    if args.install_guide:
        show_install_guide()
        return 0
    
    # Initialize manager
    manager = OllamaManager(args.endpoint, args.timeout)
    manager.default_model = args.model
    
    # Quick check
    if args.check:
        running, error = manager.check_ollama_running()
        if args.quiet:
            sys.exit(0 if running else 1)
        
        if running:
            print("✅ Ollama is running", file=sys.stderr)
            return 0
        else:
            print(f"❌ Ollama not running: {error}", file=sys.stderr)
            return 1
    
    # Pull specific model
    if args.pull_model:
        success, error = manager.pull_model(args.pull_model, not args.quiet)
        if success:
            if not args.quiet:
                print(f"✅ Model '{args.pull_model}' pulled successfully", file=sys.stderr)
            return 0
        else:
            if not args.quiet:
                print(f"❌ Failed to pull '{args.pull_model}': {error}", file=sys.stderr)
            return 2
    
    # Ensure model is available
    if args.ensure_model:
        success, error = manager.ensure_model_available(args.ensure_model)
        if args.quiet:
            sys.exit(0 if success else 2)
        
        if success:
            print(f"✅ Model '{args.ensure_model}' is available", file=sys.stderr)
            return 0
        else:
            print(f"❌ Model '{args.ensure_model}' not available: {error}", file=sys.stderr)
            return 2
    
    # Test embedding generation
    if args.test_embedding:
        success, error = manager.test_embedding_generation()
        if args.quiet:
            sys.exit(0 if success else 3)
        
        if success:
            print(error, file=sys.stderr)  # Success message is in 'error' field
            return 0
        else:
            print(error, file=sys.stderr)
            return 3
    
    # Default: show status
    if args.status or not any([args.check, args.pull_model, args.ensure_model, args.test_embedding]):
        status = manager.get_status()
        
        if args.quiet:
            # For quiet mode, exit with appropriate code
            if not status["ollama_running"]:
                sys.exit(1)
            elif not status["default_model_available"]:
                sys.exit(2)
            elif not status["embedding_test"]:
                sys.exit(3)
            else:
                sys.exit(0)
        
        print_status(status)
        
        # Return appropriate exit code
        if not status["ollama_running"]:
            return 1
        elif not status["default_model_available"]:
            return 2
        elif not status["embedding_test"]:
            return 3
        else:
            return 0
    
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n❌ Interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)