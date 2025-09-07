#!/usr/bin/env python3
"""
Basic reindex_if_needed.py for fix/nixos-compatibility branch
Simple version that just runs the basic indexer when needed
"""

import json
import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime


def main():
    """Main hook entry point."""
    # Check if we're in a git repository or have a PROJECT_INDEX.json
    current_dir = Path.cwd()
    index_path = None
    project_root = current_dir
    
    # Search up the directory tree
    check_dir = current_dir
    while check_dir != check_dir.parent:
        # Check for PROJECT_INDEX.json
        potential_index = check_dir / 'PROJECT_INDEX.json'
        if potential_index.exists():
            index_path = potential_index
            project_root = check_dir
            break
        
        # Check for .git directory
        if (check_dir / '.git').is_dir():
            project_root = check_dir
            index_path = check_dir / 'PROJECT_INDEX.json'
            break
            
        check_dir = check_dir.parent
    
    if not index_path or not index_path.exists():
        # No index exists - skip silently
        return
    
    # Simple staleness check - reindex if older than 7 days
    try:
        index_mtime = os.path.getmtime(index_path)
        current_time = datetime.now().timestamp()
        age_hours = (current_time - index_mtime) / 3600
        
        if age_hours > 168:  # 7 days
            # Run basic reindex
            script_path = Path(__file__).parent / 'project_index.py'
            if script_path.exists():
                result = subprocess.run(
                    [sys.executable, str(script_path)],
                    cwd=project_root,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print("♻️  Refreshed project index (weekly update)")
    except Exception:
        pass  # Silent failure for basic version


if __name__ == '__main__':
    main()