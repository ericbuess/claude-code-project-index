---
allowed-tools: Bash(mkdir *), Bash(cp *), Bash(ls *), Bash(jq *)
description: Complete semantic project indexing and analysis suite
---

## 🧠 Semantic Project Indexer

### Setup Command

!`mkdir -p .claude scripts`

!`cp ~/.claude-code-project-index/.claude/settings.json .claude/ 2>/dev/null || echo "No settings to copy"`

!`cp -r ~/.claude/scripts/* scripts/ 2>/dev/null || cp -r ~/.claude-code-project-index/scripts/* scripts/`

!`ls -la scripts/enhanced_project_index.py`

**To complete setup, run:**
```bash
python3 scripts/enhanced_project_index.py
```

### Status

!`ls -la PROJECT_INDEX.json`

!`jq -r '.stats | "Files: \(.total_files), Dirs: \(.total_directories)"' PROJECT_INDEX.json 2>/dev/null || echo "No index found"`