#!/usr/bin/env python3
"""
Stop hook for PROJECT_INDEX.json - Always regenerate if index exists.
This ensures the index captures any changes made during the session.
"""

import json
import sys
import os
import subprocess
from pathlib import Path


def main():
    """Stop hook - regenerate index if PROJECT_INDEX.json exists."""
    # Find PROJECT_INDEX.json by searching up the directory tree
    current_dir = Path.cwd()
    project_root = None
    
    check_dir = current_dir
    while check_dir != check_dir.parent:
        if (check_dir / 'PROJECT_INDEX.json').exists():
            project_root = check_dir
            break
        check_dir = check_dir.parent
    
    # If no PROJECT_INDEX.json found, nothing to do
    if not project_root:
        return
    
    # Find the project_index.py script
    # First check if we're in the project itself
    local_script = project_root / 'scripts' / 'project_index.py'
    if local_script.exists():
        script_path = local_script
    else:
        # Use the system-installed version
        script_path = Path.home() / '.claude-code-project-index' / 'scripts' / 'project_index.py'
        if not script_path.exists():
            print("Warning: Could not find project_index.py", file=sys.stderr)
            return
    
    # Find Python command
    python_cmd_file = Path.home() / '.claude-code-project-index' / '.python_cmd'
    if python_cmd_file.exists():
        python_cmd = python_cmd_file.read_text().strip()
    else:
        # Try common Python commands
        for cmd in ['python3', 'python', 'python3.12', 'python3.11', 'python3.10', 'python3.9', 'python3.8']:
            try:
                result = subprocess.run([cmd, '--version'], capture_output=True, text=True)
                if result.returncode == 0:
                    python_cmd = cmd
                    break
            except:
                continue
        else:
            print("Warning: Could not find Python", file=sys.stderr)
            return
    
    # Run the indexer silently
    try:
        os.chdir(project_root)
        result = subprocess.run(
            [python_cmd, str(script_path)],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            # Success - notify user that index was refreshed
            output = {"suppressOutput": False}
            print("🔄 PROJECT_INDEX.json refreshed with latest changes")
            sys.stdout.write(json.dumps(output) + '\n')
        else:
            # Failed but don't interrupt the user's workflow
            print(f"Warning: Failed to refresh index: {result.stderr}", file=sys.stderr)
            
    except subprocess.TimeoutExpired:
        print("Warning: Index refresh timed out", file=sys.stderr)
    except Exception as e:
        print(f"Warning: Index refresh error: {e}", file=sys.stderr)


if __name__ == '__main__':
    main()