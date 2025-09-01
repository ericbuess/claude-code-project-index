#!/usr/bin/env python3
"""
UserPromptSubmit hook for intelligent PROJECT_INDEX.json analysis.
Detects -i[number] and -ic[number] flags for dynamic index generation.
"""

import json
import sys
import os
import re
import subprocess
import hashlib
import time
from pathlib import Path
from datetime import datetime

# Import centralized Ollama management
try:
    from find_ollama import OllamaManager
except ImportError:
    # Fallback if find_ollama.py is not in the same directory
    sys.path.insert(0, str(Path(__file__).parent))
    from find_ollama import OllamaManager

# Constants
DEFAULT_SIZE_K = 50  # Default 50k tokens
MIN_SIZE_K = 1       # Minimum 1k tokens
CLAUDE_MAX_K = 100   # Max 100k for Claude (leaves room for reasoning)
EXTERNAL_MAX_K = 800 # Max 800k for external AI

def ensure_ollama_for_embeddings():
    """Check if Ollama is installed/running and nomic-embed-text model is available.
    Returns: (success: bool, message: str)
    """
    try:
        manager = OllamaManager()
        success, message = manager.ensure_model_available()
        return success, message
    except Exception as e:
        return False, f"Error checking Ollama: {str(e)}"

def find_project_root():
    """Find project root by looking for .git or common project markers."""
    current = Path.cwd()
    
    # First check current directory for project markers
    if (current / '.git').exists():
        return current
    
    # Check for other project markers
    project_markers = ['package.json', 'pyproject.toml', 'setup.py', 'Cargo.toml', 'go.mod']
    for marker in project_markers:
        if (current / marker).exists():
            return current
        
    # Search up the tree for .git
    for parent in current.parents:
        if (parent / '.git').exists():
            return parent
            
    # Default to current directory
    return current

def get_last_interactive_size():
    """Get the last remembered -i size from the index."""
    try:
        project_root = find_project_root()
        index_path = project_root / 'PROJECT_INDEX.json'
        
        if index_path.exists():
            with open(index_path, 'r') as f:
                index = json.load(f)
                meta = index.get('_meta', {})
                last_size = meta.get('last_interactive_size_k')
                
                if last_size:
                    print(f"📝 Using remembered size: {last_size}k", file=sys.stderr)
                    return last_size
    except:
        pass
    
    # Fall back to default
    return DEFAULT_SIZE_K

def parse_index_flag(prompt):
    """Parse -i, -ic, or -ie flag with optional size.
    Returns: (size_k, clipboard_mode, embedding_mode, cleaned_prompt)
    """
    # Pattern matches -i[number], -ic[number], or -ie[number]
    match = re.search(r'-i([ce]?)(\d+)?(?:\s|$)', prompt)
    
    if not match:
        return None, None, None, prompt
    
    mode_char = match.group(1)
    clipboard_mode = mode_char == 'c'
    embedding_mode = mode_char == 'e'
    
    # If no explicit size provided, check for remembered size
    if match.group(2):
        size_k = int(match.group(2))
    else:
        # For plain -i or -ie without size, try to use last remembered size
        if not clipboard_mode:
            size_k = get_last_interactive_size()
        else:
            # For -ic, always use default
            size_k = DEFAULT_SIZE_K
    
    # Validate size limits
    if size_k < MIN_SIZE_K:
        print(f"⚠️ Minimum size is {MIN_SIZE_K}k, using {MIN_SIZE_K}k", file=sys.stderr)
        size_k = MIN_SIZE_K
    
    if not clipboard_mode and size_k > CLAUDE_MAX_K:
        print(f"⚠️ Claude max is {CLAUDE_MAX_K}k (need buffer for reasoning), using {CLAUDE_MAX_K}k", file=sys.stderr)
        size_k = CLAUDE_MAX_K
    elif clipboard_mode and size_k > EXTERNAL_MAX_K:
        print(f"⚠️ Maximum size is {EXTERNAL_MAX_K}k, using {EXTERNAL_MAX_K}k", file=sys.stderr)
        size_k = EXTERNAL_MAX_K
    
    # Clean prompt (remove flag)
    cleaned_prompt = re.sub(r'-i[ce]?\d*\s*', '', prompt).strip()
    
    return size_k, clipboard_mode, embedding_mode, cleaned_prompt

def calculate_files_hash(project_root):
    """Calculate hash of non-ignored files to detect changes."""
    try:
        # Use git ls-files to get non-ignored files
        result = subprocess.run(
            ['git', 'ls-files', '--cached', '--others', '--exclude-standard'],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            files = result.stdout.strip().split('\n') if result.stdout.strip() else []
        else:
            # Fallback to manual file discovery
            files = []
            for file_path in project_root.rglob('*'):
                if file_path.is_file() and not any(part.startswith('.') for part in file_path.parts):
                    files.append(str(file_path.relative_to(project_root)))
        
        # Hash file paths and modification times
        hasher = hashlib.sha256()
        for file_path in sorted(files):
            full_path = project_root / file_path
            if full_path.exists():
                try:
                    mtime = str(full_path.stat().st_mtime)
                    hasher.update(f"{file_path}:{mtime}".encode())
                except:
                    pass
        
        return hasher.hexdigest()[:16]
    except Exception as e:
        print(f"Warning: Could not calculate files hash: {e}", file=sys.stderr)
        return "unknown"

def should_regenerate_index(project_root, index_path, requested_size_k, require_embeddings=False):
    """Determine if index needs regeneration.
    If require_embeddings is True, force regeneration when embeddings are missing.
    """
    if not index_path.exists():
        return True, "No index exists"
    
    try:
        # Read metadata
        with open(index_path, 'r') as f:
            index = json.load(f)
            meta = index.get('_meta', {})
        
        # Get last generation info
        last_target = meta.get('target_size_k', 0)
        last_files_hash = meta.get('files_hash', '')
        includes_embeddings = meta.get('includes_embeddings', False)
        
        # If embeddings are required but not present, regenerate
        if require_embeddings and not includes_embeddings:
            return True, "Embeddings missing in existing index"
        
        # Check if files changed
        current_files_hash = calculate_files_hash(project_root)
        if current_files_hash != last_files_hash and current_files_hash != "unknown":
            return True, f"Files changed since last index"
        
        # Check if different size requested
        if abs(requested_size_k - last_target) > 2:  # Allow 2k tolerance
            return True, f"Different size requested ({requested_size_k}k vs {last_target}k)"
        
        # Use existing index
        actual_k = meta.get('actual_size_k', last_target)
        return False, f"Using cached index ({actual_k}k actual, {last_target}k target)"
    
    except Exception as e:
        print(f"Warning: Could not read index metadata: {e}", file=sys.stderr)
        return True, "Could not read index metadata"

def generate_index_at_size(project_root, target_size_k, is_clipboard_mode=False, include_embeddings=False):
    """Generate index at specific token size.
    If include_embeddings is True, the indexer will attempt to include neural embeddings.
    """
    mode_note = " with embeddings" if include_embeddings else ""
    print(f"🎯 Generating {target_size_k}k token index{mode_note}...", file=sys.stderr)
    
    # Find indexer script
    local_indexer = Path(__file__).parent / 'project_index.py'
    system_indexer = Path.home() / '.claude-code-project-index' / 'scripts' / 'project_index.py'
    
    indexer_path = local_indexer if local_indexer.exists() else system_indexer
    
    if not indexer_path.exists():
        print("⚠️ PROJECT_INDEX.json indexer not found", file=sys.stderr)
        return False
    
    try:
        # Find Python command
        python_cmd_file = Path.home() / '.claude-code-project-index' / '.python_cmd'
        if python_cmd_file.exists():
            python_cmd = python_cmd_file.read_text().strip()
        else:
            python_cmd = sys.executable
        
        # Pass target size and embedding settings as environment variables
        env = os.environ.copy()
        env['INDEX_TARGET_SIZE_K'] = str(target_size_k)
        if include_embeddings:
            env['INCLUDE_EMBEDDINGS'] = '1'
            # Allow overrides via env, but provide sensible defaults
            env.setdefault('EMBED_MODEL_NAME', 'nomic-embed-text')
            env.setdefault('EMBED_ENDPOINT', 'http://localhost:11434')
        
        result = subprocess.run(
            [python_cmd, str(indexer_path)],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=(180 if include_embeddings else 30),  # allow more time when generating embeddings
            env=env
        )
        
        if result.returncode == 0:
            # Update metadata with target size and hash
            index_path = project_root / 'PROJECT_INDEX.json'
            if index_path.exists():
                with open(index_path, 'r') as f:
                    index = json.load(f)
                
                # Measure actual size
                index_str = json.dumps(index, indent=2)
                actual_tokens = len(index_str) // 4  # Rough estimate: 4 chars = 1 token
                actual_size_k = actual_tokens // 1000
                
                # Add/update metadata
                if '_meta' not in index:
                    index['_meta'] = {}
                
                metadata_update = {
                    'generated_at': time.time(),
                    'target_size_k': target_size_k,
                    'actual_size_k': actual_size_k,
                    'files_hash': calculate_files_hash(project_root),
                    'compression_ratio': f"{(actual_size_k/target_size_k)*100:.1f}%" if target_size_k > 0 else "N/A",
                    'includes_embeddings': bool(include_embeddings),
                }
                
                # Remember -i size for next time (but not -ic)
                if not is_clipboard_mode:
                    metadata_update['last_interactive_size_k'] = target_size_k
                    print(f"💾 Remembering size {target_size_k}k for next -i", file=sys.stderr)
                
                index['_meta'].update(metadata_update)
                
                # Save updated index
                with open(index_path, 'w') as f:
                    json.dump(index, f, indent=2)
                
                print(f"✅ Created PROJECT_INDEX.json ({actual_size_k}k actual, {target_size_k}k target){' with embeddings' if include_embeddings else ''}", file=sys.stderr)
                return True
            else:
                print("⚠️ Index file not created", file=sys.stderr)
                return False
        else:
            print(f"⚠️ Failed to create index: {result.stderr}", file=sys.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️ Index creation timed out", file=sys.stderr)
        return False
    except Exception as e:
        print(f"⚠️ Error creating index: {e}", file=sys.stderr)
        return False

def copy_to_clipboard(prompt, index_path):
    """Copy prompt, instructions, and index to clipboard for external AI."""
    try:
        # Try VM Bridge first (works with any size over mosh)
        vm_bridge_available = False
        bridge_client = None
        
        try:
            import sys
            # Try multiple VM Bridge locations in order of preference
            vm_bridge_paths = [
                os.path.expanduser('~/.claude-ericbuess/tools/vm-bridge'),  # New standard location
                '/home/ericbuess/Projects/vm-bridge',  # Legacy project location
                os.path.expanduser('~/.local/lib/python/vm_bridge')  # Old tunnel location
            ]
            
            # Try network version first (no tunnel needed)
            for bridge_path in vm_bridge_paths:
                if os.path.exists(bridge_path):
                    sys.path.insert(0, bridge_path)
                    try:
                        from vm_client_network import VMBridgeClient as NetworkClient
                        
                        # Try to auto-detect or use known Mac IP
                        for mac_ip in ['10.211.55.2', '10.211.55.1', '192.168.1.1']:
                            try:
                                test_client = NetworkClient(host=mac_ip)
                                if test_client.is_daemon_running():
                                    bridge_client = test_client
                                    print(f"🌉 VM Bridge network daemon detected at {mac_ip}", file=sys.stderr)
                                    vm_bridge_available = True
                                    break
                            except:
                                continue
                        
                        if vm_bridge_available:
                            break
                    except ImportError:
                        # Try next path
                        continue
                    
            # Fall back to localhost tunnel version if network not available
            if not vm_bridge_available:
                for bridge_path in vm_bridge_paths:
                    if os.path.exists(bridge_path):
                        sys.path.insert(0, bridge_path)
                        try:
                            from vm_client import VMBridgeClient
                            bridge_client = VMBridgeClient()
                            if bridge_client.is_daemon_running():
                                print("🌉 VM Bridge tunnel daemon detected", file=sys.stderr)
                                vm_bridge_available = True
                                break
                        except ImportError:
                            continue
                    
        except ImportError:
            vm_bridge_available = False
        # Create clipboard-specific instructions (no tools, no subagent references)
        clipboard_instructions = """You are analyzing a codebase index to help identify relevant files and code sections.

## YOUR TASK
Analyze the PROJECT_INDEX.json below to identify the most relevant code sections for the user's request.
The index contains file structures, function signatures, call graphs, and dependencies.

## WHAT TO LOOK FOR
- Identify specific files and functions related to the request
- Trace call graphs to understand code flow
- Note dependencies and relationships
- Consider architectural patterns

## IMPORTANT: RESPONSE FORMAT
Your response will be copied and pasted to Claude Code. Format your response as:

### 📍 RELEVANT CODE LOCATIONS

**Primary Files to Examine:**
- `path/to/file.py` - [Why relevant]
  - `function_name()` (line X) - [What it does]
  - Called by: [list any callers]
  - Calls: [list what it calls]

**Related Files:**
- `path/to/related.py` - [Connection to task]

### 🔍 KEY INSIGHTS
- [Architectural patterns observed]
- [Dependencies to consider]
- [Potential challenges or gotchas]

### 💡 RECOMMENDATIONS
- Start by examining: [specific file]
- Focus on: [specific functions/classes]
- Consider: [any special considerations]

Do NOT include the original user prompt in your response.
Focus on providing actionable file locations and insights."""
        
        # Load index
        with open(index_path, 'r') as f:
            index = json.load(f)
        
        # Build clipboard content
        clipboard_content = f"""# Codebase Analysis Request

## Task for You
{prompt}

## Instructions
{clipboard_instructions}

## PROJECT_INDEX.json
{json.dumps(index, indent=2)}
"""
        
        # Try to copy to clipboard
        clipboard_success = False
        
        # Try VM Bridge first if available (works with any size over mosh)
        if vm_bridge_available:
            try:
                if bridge_client.copy_to_clipboard(clipboard_content):
                    print(f"✅ Copied to Mac clipboard via VM Bridge ({len(clipboard_content)} chars)", file=sys.stderr)
                    print(f"🌉 No size limits with VM Bridge!", file=sys.stderr)
                    
                    # Also notify on Mac
                    bridge_client.notify(f"Clipboard updated: {len(clipboard_content)} chars from VM")
                    
                    # Save to file as backup
                    fallback_path = Path.cwd() / '.clipboard_content.txt'
                    with open(fallback_path, 'w') as f:
                        f.write(clipboard_content)
                    print(f"📁 Also saved to {fallback_path} as backup", file=sys.stderr)
                    
                    return ('vm_bridge', len(clipboard_content))
            except Exception as e:
                print(f"⚠️ VM Bridge failed: {e}", file=sys.stderr)
                # Fall through to other methods
        
        # Check if we're in an SSH session (clipboard won't work across SSH)
        is_ssh = os.environ.get('SSH_CONNECTION') or os.environ.get('SSH_CLIENT')
        
        # For SSH sessions, try OSC 52 or other methods
        if is_ssh:
            fallback_path = Path.cwd() / '.clipboard_content.txt'
            with open(fallback_path, 'w') as f:
                f.write(clipboard_content)
            
            # Import base64 at the beginning for all methods
            import base64
            
            # Try multiple clipboard methods for SSH sessions
            clipboard_success = False
            
            # Check content size first - OSC 52 has limits, especially over mosh
            content_size = len(clipboard_content)
            # Testing shows mosh/tmux cuts off at ~12KB, so stay safely under that
            mosh_limit = 11000  # Just under the 12KB cutoff we observed
            
            if content_size <= mosh_limit:
                # Small enough for OSC 52 - try to send directly to clipboard
                try:
                    # Base64 encode and remove newlines
                    b64_content = base64.b64encode(clipboard_content.encode('utf-8')).decode('ascii')
                    
                    # Get the correct TTY device
                    tty_device = None
                    is_tmux = os.environ.get('TMUX')
                    
                    if is_tmux:
                        # Inside tmux: get the client tty
                        try:
                            result = subprocess.run(['tmux', 'display-message', '-p', '#{client_tty}'],
                                                  capture_output=True, text=True, check=True)
                            tty_device = result.stdout.strip()
                        except:
                            tty_device = "/dev/tty"
                    else:
                        tty_device = "/dev/tty"
                    
                    # Send OSC 52 sequence with proper format
                    if is_tmux:
                        # Inside tmux: use DCS passthrough (this is the KEY!)
                        osc52_sequence = f"\033Ptmux;\033\033]52;c;{b64_content}\007\033\\"
                    else:
                        # Outside tmux: use standard OSC 52
                        osc52_sequence = f"\033]52;c;{b64_content}\007"
                    
                    # Write directly to TTY device (not stderr)
                    try:
                        with open(tty_device, 'w') as tty:
                            tty.write(osc52_sequence)
                            tty.flush()
                        clipboard_success = True
                        print(f"✅ Sent to Mac clipboard via OSC 52 ({content_size} chars)", file=sys.stderr)
                    except PermissionError:
                        # Fallback to stderr if can't open TTY
                        sys.stderr.write(osc52_sequence)
                        sys.stderr.flush()
                        clipboard_success = True
                        print(f"✅ Sent to Mac clipboard via OSC 52 ({content_size} chars)", file=sys.stderr)
                        
                except Exception as e:
                    print(f"⚠️ OSC 52 failed: {e}", file=sys.stderr)
            else:
                # Too large for mosh/tmux's ~12KB limit - use alternative methods
                # Testing shows clipboard gets truncated at ~12KB over mosh
                print(f"📋 Content exceeds mosh/tmux's 12KB limit ({content_size} chars)", file=sys.stderr)
                
                # Load into tmux buffer for local access
                try:
                    proc = subprocess.Popen(['tmux', 'load-buffer', '-'], stdin=subprocess.PIPE,
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    proc.communicate(clipboard_content.encode('utf-8'))
                    if proc.returncode == 0:
                        print(f"✅ Loaded into tmux buffer", file=sys.stderr)
                        
                        # Try to trigger automatic Mac clipboard sync
                        # This runs a command on the tmux client (Mac) side
                        sync_cmd = f"ssh {os.environ.get('USER', 'user')}@10.211.55.4 'cat ~/Projects/claude-code-project-index/.clipboard_content.txt' | pbcopy"
                        tmux_run = f"tmux run-shell '{sync_cmd}'"
                        
                        try:
                            subprocess.run(['tmux', 'run-shell', sync_cmd], 
                                         capture_output=True, timeout=2)
                            print(f"🚀 Attempting automatic clipboard sync to Mac...", file=sys.stderr)
                        except:
                            pass
                except:
                    pass
                
                print(f"", file=sys.stderr)
                print(f"To manually copy to Mac clipboard, run this on your Mac:", file=sys.stderr)
                print(f"   ssh {os.environ.get('USER', 'user')}@10.211.55.4 'cat ~/Projects/claude-code-project-index/.clipboard_content.txt' | pbcopy", file=sys.stderr)
                print(f"", file=sys.stderr)
                print(f"ℹ️  Mosh/tmux limits clipboard to ~12KB. For larger content, consider:", file=sys.stderr)
                print(f"   - Using SSH instead of mosh for this operation", file=sys.stderr)
                print(f"   - Or using the manual command above", file=sys.stderr)
            
            # Also try tmux buffer for local pasting
            try:
                proc = subprocess.Popen(['tmux', 'load-buffer', '-'], stdin=subprocess.PIPE,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                proc.communicate(clipboard_content.encode('utf-8'))
                if proc.returncode == 0:
                    print(f"✅ Loaded into tmux buffer (use prefix + ] to paste)", file=sys.stderr)
            except:
                pass
            
            print(f"📁 Full content saved to {fallback_path}", file=sys.stderr)
            
            if clipboard_success:
                return ('ssh_clipboard', str(fallback_path))
            else:
                return ('ssh_file_large', str(fallback_path))
        
        # First try xclip directly (most reliable for Linux)
        try:
            result = subprocess.run(['which', 'xclip'], capture_output=True)
            if result.returncode == 0:
                # Use xclip with a virtual display if needed
                env = os.environ.copy()
                if not env.get('DISPLAY'):
                    # Check if Xvfb is running on :99
                    xvfb_check = subprocess.run(['pgrep', '-f', 'Xvfb.*:99'], capture_output=True)
                    if xvfb_check.returncode != 0:
                        # Start Xvfb if not running
                        subprocess.Popen(['Xvfb', ':99', '-screen', '0', '1024x768x24'],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        time.sleep(0.5)
                    env['DISPLAY'] = ':99'
                
                # Copy to clipboard using xclip
                proc = subprocess.Popen(['xclip', '-selection', 'clipboard'],
                                      stdin=subprocess.PIPE, env=env,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                proc.communicate(clipboard_content.encode('utf-8'))
                if proc.returncode == 0:
                    clipboard_success = True
                    print(f"✅ Copied to clipboard via xclip: {len(clipboard_content)} chars", file=sys.stderr)
                    print(f"📋 Ready to paste into Gemini, Claude.ai, ChatGPT, or other AI", file=sys.stderr)
                    return ('clipboard', len(clipboard_content))
        except:
            pass
        
        # Fallback to pyperclip if xclip didn't work
        if not clipboard_success:
            try:
                import pyperclip
                pyperclip.copy(clipboard_content)
                print(f"✅ Copied to clipboard via pyperclip: {len(clipboard_content)} chars", file=sys.stderr)
                print(f"📋 Ready to paste into Gemini, Claude.ai, ChatGPT, or other AI", file=sys.stderr)
                return ('clipboard', len(clipboard_content))
            except (ImportError, Exception) as e:
                pass
        
        # Final fallback to file if clipboard methods failed
        if not clipboard_success:
            fallback_path = Path.cwd() / '.clipboard_content.txt'
            with open(fallback_path, 'w') as f:
                f.write(clipboard_content)
            print(f"✅ Saved to {fallback_path} (copy manually)", file=sys.stderr)
            return ('file', str(fallback_path))
    except Exception as e:
        print(f"⚠️ Error preparing clipboard content: {e}", file=sys.stderr)
        return ('error', str(e))

def main():
    """Process UserPromptSubmit hook for -i, -ic, and -ie flag detection."""
    try:
        # Read hook input
        input_data = json.load(sys.stdin)
        prompt = input_data.get('prompt', '')
        
        # Parse flag
        size_k, clipboard_mode, embedding_mode, cleaned_prompt = parse_index_flag(prompt)
        
        if size_k is None:
            # No index flag, let prompt proceed normally
            sys.exit(0)
        
        # Find project root
        project_root = find_project_root()
        index_path = project_root / 'PROJECT_INDEX.json'
        
        # If embedding mode requested, check Ollama runtime
        include_embeddings = False
        if embedding_mode:
            ok, msg = ensure_ollama_for_embeddings()
            if ok:
                include_embeddings = True
                print(f"🧠 Embedding mode: {msg}", file=sys.stderr)
            else:
                print(f"⚠️ Embeddings disabled: {msg}", file=sys.stderr)
        
        # Check if regeneration needed
        should_regen, reason = should_regenerate_index(project_root, index_path, size_k, require_embeddings=include_embeddings)
        
        if should_regen:
            print(f"🔄 Regenerating index: {reason}", file=sys.stderr)
            if not generate_index_at_size(project_root, size_k, clipboard_mode, include_embeddings=include_embeddings):
                print("⚠️ Proceeding without PROJECT_INDEX.json", file=sys.stderr)
                sys.exit(0)
        else:
            print(f"✅ {reason}", file=sys.stderr)
        
        # Handle clipboard mode
        if clipboard_mode:
            copy_result = copy_to_clipboard(cleaned_prompt, index_path)
            if copy_result[0] == 'vm_bridge':
                # Successfully copied via VM Bridge
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": f"""
🌉 Clipboard Mode - VM Bridge Success!

✅ Index copied to Mac clipboard via VM Bridge ({copy_result[1]} chars).
🚀 No size limits with this method!
📁 Also saved to: .clipboard_content.txt

Paste directly into external AI (Gemini, Claude.ai, ChatGPT) for analysis.

**CRITICAL INSTRUCTION FOR CLAUDE**: STOP! Do NOT proceed with the original request. The user wants to use an external AI for analysis. You should:
1. ONLY acknowledge that the content was copied to clipboard
2. WAIT for the user to paste the external AI's response
3. DO NOT attempt to answer or work on: "{cleaned_prompt}"

Simply respond with something like: "✅ Index copied to clipboard for external AI analysis. Please paste the response here when ready."

User's request (DO NOT ANSWER): {cleaned_prompt}
"""
                    }
                }
            elif copy_result[0] == 'clipboard':
                # Successfully copied to clipboard
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": f"""
📋 Clipboard Mode Activated

Index and instructions copied to clipboard ({size_k}k tokens, {copy_result[1]} chars).
Paste into external AI (Gemini, Claude.ai, ChatGPT) for analysis.

**CRITICAL INSTRUCTION FOR CLAUDE**: STOP! Do NOT proceed with the original request. The user wants to use an external AI for analysis. You should:
1. ONLY acknowledge that the content was copied to clipboard
2. WAIT for the user to paste the external AI's response
3. DO NOT attempt to answer or work on: "{cleaned_prompt}"

Simply respond with something like: "✅ Index copied to clipboard for external AI analysis. Please paste the response here when ready."

User's request (DO NOT ANSWER): {cleaned_prompt}
"""
                    }
                }
            elif copy_result[0] == 'ssh_clipboard':
                # SSH session with successful clipboard copy
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": f"""
📋 Clipboard Mode - Mac Clipboard Success!

✅ Index copied to your Mac's clipboard via pbcopy ({size_k}k tokens).
📁 Also saved to: {copy_result[1]}

Paste directly into external AI (Gemini, Claude.ai, ChatGPT) for analysis.

**CRITICAL INSTRUCTION FOR CLAUDE**: STOP! Do NOT proceed with the original request. The user wants to use an external AI for analysis. You should:
1. ONLY acknowledge that the content was copied to clipboard
2. WAIT for the user to paste the external AI's response
3. DO NOT attempt to answer or work on: "{cleaned_prompt}"

Simply respond with something like: "✅ Index copied to clipboard for external AI analysis. Please paste the response here when ready."

User's request (DO NOT ANSWER): {cleaned_prompt}
"""
                    }
                }
            elif copy_result[0] == 'ssh_file_large':
                # SSH session with large content - manual copy needed
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": f"""
📋 Clipboard Mode - Content Too Large for Auto-Copy

Index saved to: {copy_result[1]} ({size_k}k tokens).
⚠️ Content exceeds mosh/OSC 52 limit (7.5KB) for automatic clipboard.

To copy the full index to your Mac clipboard, run this command on your Mac:
ssh {os.environ.get('USER', 'user')}@10.211.55.4 'cat ~/Projects/claude-code-project-index/.clipboard_content.txt' | pbcopy

Then paste into external AI (Gemini, Claude.ai, ChatGPT) for analysis.

**CRITICAL INSTRUCTION FOR CLAUDE**: STOP! Do NOT proceed with the original request. The user wants to use an external AI for analysis. You should:
1. ONLY acknowledge that the content was copied to clipboard
2. WAIT for the user to paste the external AI's response
3. DO NOT attempt to answer or work on: "{cleaned_prompt}"

Simply respond with something like: "✅ Index copied to clipboard for external AI analysis. Please paste the response here when ready."

User's request (DO NOT ANSWER): {cleaned_prompt}
"""
                    }
                }
            elif copy_result[0] == 'file':
                # Saved to file fallback
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": f"""
📁 Clipboard Mode (File Fallback)

Index and instructions saved to: {copy_result[1]} ({size_k}k tokens).
⚠️ pyperclip not installed - content saved to file instead.

To copy: cat {copy_result[1]} | pbcopy  # macOS
         cat {copy_result[1]} | xclip   # Linux

Then paste into external AI (Gemini, Claude.ai, ChatGPT) for analysis.

**CRITICAL INSTRUCTION FOR CLAUDE**: STOP! Do NOT proceed with the original request. The user wants to use an external AI for analysis. You should:
1. ONLY acknowledge that the content was copied to clipboard
2. WAIT for the user to paste the external AI's response
3. DO NOT attempt to answer or work on: "{cleaned_prompt}"

Simply respond with something like: "✅ Index copied to clipboard for external AI analysis. Please paste the response here when ready."

User's request (DO NOT ANSWER): {cleaned_prompt}
"""
                    }
                }
            else:
                # Error case
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": f"""
❌ Clipboard Mode Failed

Error: {copy_result[1]}

Please check the error and try again.
User's request (DO NOT ANSWER): {cleaned_prompt}
"""
                    }
                }
        else:
            # Standard mode - prepare for subagent
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": f"""
## 🎯 Index-Aware Mode Activated

Generated/loaded {size_k}k token index.

**IMPORTANT**: You MUST use the index-analyzer subagent to analyze the codebase structure before proceeding with the request.

Use it like this:
"I'll analyze the codebase structure to understand the relevant code sections for your request."

Then explicitly invoke: "Using the index-analyzer subagent to analyze PROJECT_INDEX.json..."

The subagent will provide deep code intelligence including:
- Essential code paths and dependencies
- Call graphs and impact analysis
- Architectural insights and patterns
- Strategic recommendations

Original request (without -i flag): {cleaned_prompt}

PROJECT_INDEX.json location: {index_path}
"""
                }
            }
        
        print(json.dumps(output))
        sys.exit(0)
        
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Hook error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()