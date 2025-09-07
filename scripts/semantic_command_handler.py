#!/usr/bin/env python3
"""
Command handler for /semantic-index slash command
Handles all sub-commands without multi-line bash issues
"""

import sys
import os
import subprocess
import json
from pathlib import Path

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

def show_status():
    """Show project status"""
    print("📊 PROJECT STATUS:")
    
    if os.path.exists("PROJECT_INDEX.json"):
        size = os.path.getsize("PROJECT_INDEX.json")
        print(f"✅ Index size: {size} bytes")
        
        try:
            with open("PROJECT_INDEX.json", "r") as f:
                index = json.load(f)
            print(f"📁 Files: {index.get('stats', {}).get('total_files', 'N/A')}")
            print(f"🗂️  Dirs: {index.get('stats', {}).get('total_directories', 'N/A')}")
            print(f"🧬 Semantic: {'semantic_index' in index}")
        except:
            print("⚠️  Could not parse index file")
    else:
        print("❌ No PROJECT_INDEX.json found")
        print("💡 Run: /semantic-index setup")

def setup_project():
    """Set up project indexing"""
    print("⚙️  Setting up project indexing...")
    
    # Copy hooks configuration
    os.makedirs(".claude", exist_ok=True)
    settings_path = os.path.expanduser("~/.claude-code-project-index/.claude/settings.json")
    if os.path.exists(settings_path):
        run_command(f"cp {settings_path} .claude/")
        print("✅ Hooks configured")
    else:
        print("⚠️  No hooks configuration found, skipping")
    
    # Copy scripts locally
    os.makedirs("scripts", exist_ok=True)
    global_scripts = os.path.expanduser("~/.claude/scripts")
    project_scripts = "/home/lessuseless/.claude-code-project-index/scripts"
    
    if os.path.exists(global_scripts):
        run_command(f"cp -r {global_scripts}/* scripts/")
        print("✅ Scripts copied from global location")
    elif os.path.exists(project_scripts):
        run_command(f"cp -r {project_scripts}/* scripts/")
        print("✅ Scripts copied from project repository")
    else:
        print("❌ Could not find scripts directory")
        return False
    
    # Generate initial index
    print("🏗️  Generating initial PROJECT_INDEX.json...")
    if run_command("python3 scripts/enhanced_project_index.py"):
        print("✅ Setup complete! Index created and hooks configured.")
        print("📊 You can now use:")
        print("   • /semantic-index build     - Update index")
        print("   • /semantic-index duplicates - Check for duplicates")
        print("   • /embedded-index setup     - Neural embeddings")
        return True
    else:
        print("❌ Failed to generate index")
        return False

def main():
    """Main command handler"""
    args = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    
    if args in ["status", ""]:
        show_status()
    
    elif args in ["build", "incremental"]:
        print("🔄 Running incremental update...")
        run_command("python3 ~/.claude/scripts/reindex_if_needed.py")
    
    elif args == "full":
        print("🏗️  Full semantic rebuild...")
        run_command("python3 ~/.claude/scripts/enhanced_project_index.py")
    
    elif args == "duplicates":
        print("🔍 Checking for duplicates...")
        run_command("python3 ~/.claude/scripts/duplicate_mode_toggle.py --status")
        print("📋 Generate report with: /semantic-index duplicates report")
    
    elif args == "duplicates report":
        print("📊 Generating duplicate analysis report...")
        run_command("python3 ~/.claude/scripts/generate_duplicate_report.py")
    
    elif args == "duplicates interactive":
        print("🛠️  Starting interactive cleanup...")
        run_command("python3 ~/.claude/scripts/interactive_cleanup.py")
    
    elif args == "analyze":
        print("🔬 Running semantic analysis...")
        run_command("python3 ~/.claude/scripts/semantic_analyzer.py")
    
    elif args == "setup":
        setup_project()
    
    else:
        print("📚 USAGE: /semantic-index [command]")
        print("")
        print("Commands:")
        print("  build         - Incremental update (default)")
        print("  full          - Complete rebuild with semantic analysis")
        print("  duplicates    - Show duplicate detection status")
        print("  duplicates report     - Generate duplicate analysis")
        print("  duplicates interactive - Interactive cleanup")
        print("  analyze       - Run semantic analysis only")
        print("  status        - Show current index status")
        print("  setup         - Initialize project indexing")

if __name__ == "__main__":
    main()