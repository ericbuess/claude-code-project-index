---
allowed-tools: Bash(python3 *), Bash(cd *), Bash(ls *), Bash(find *)
argument-hint: [size-in-kb] | full | quick | status
description: Generate or refresh project index
---

## Project Index Manager

Generate, refresh, or check the status of your PROJECT_INDEX.json file.

### Usage Options:

1. **Default indexing**: `!python3 scripts/project_index.py`
2. **Full semantic analysis**: `!python3 scripts/enhanced_project_index.py` 
3. **Quick refresh**: `!python3 scripts/reindex_if_needed.py`
4. **Interactive size**: Handle $ARGUMENTS as size specification

### Commands to run:

Current directory status: !`pwd && ls -la PROJECT_INDEX.json 2>/dev/null || echo "No index found"`

**Generate the index based on your request:**

$ARGUMENTS