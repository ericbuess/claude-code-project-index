---
allowed-tools: Bash(python3 *), Bash(cd *)
argument-hint: report | interactive | toggle [mode] | status
description: Manage duplicate code detection and cleanup
---

## Duplicate Code Manager

Detect, analyze, and clean up duplicate code in your project.

### Usage Options:

**Current project status:** !`pwd && python3 scripts/duplicate_mode_toggle.py --status 2>/dev/null || echo "Duplicate detection not configured"`

### Commands available:

1. **Generate duplicate report**: `python3 scripts/generate_duplicate_report.py`
2. **Interactive cleanup**: `python3 scripts/interactive_cleanup.py`  
3. **Toggle detection mode**: `python3 scripts/duplicate_mode_toggle.py --mode $ARGUMENTS`
4. **Status check**: `python3 scripts/duplicate_mode_toggle.py --status`

**Execute based on your argument: $ARGUMENTS**