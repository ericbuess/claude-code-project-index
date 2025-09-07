#!/usr/bin/env python3
"""
Update index hook - called after file edits to keep PROJECT_INDEX.json current
"""

import json
import sys
import os
import subprocess
from pathlib import Path

def main():
    """Simple update hook that calls reindex_if_needed"""
    try:
        # Just call the existing reindex script
        result = subprocess.run([
            "python3", 
            "scripts/reindex_if_needed.py"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Index update completed successfully")
        else:
            print(f"Index update had issues: {result.stderr}")
            
    except Exception as e:
        print(f"Update hook error: {e}")

if __name__ == "__main__":
    main()