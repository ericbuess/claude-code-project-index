---
allowed-tools: Bash(cp *), Bash(mkdir *), Bash(chmod *), Bash(python3 *)
description: Set up automatic project indexing for Claude Code
---

## Setup Project Indexing

Configure your project for seamless integration with Claude Code's project indexing system.

### What this does:

1. **Copies indexing scripts** to your project
2. **Sets up Claude Code hooks** for automatic maintenance  
3. **Creates initial PROJECT_INDEX.json** with semantic analysis
4. **Configures duplicate detection** (optional)

### Setup Process:

**Step 1: Copy scripts to your project**
!`mkdir -p scripts && cp -r /home/lessuseless/.claude-code-project-index/scripts/* scripts/ && echo "✓ Scripts copied"`

**Step 2: Make scripts executable**
!`find scripts -name "*.py" -exec chmod +x {} \; && echo "✓ Scripts made executable"`

**Step 3: Copy Claude Code configuration**  
!`mkdir -p .claude && cp /home/lessuseless/.claude-code-project-index/.claude/settings.json .claude/ && echo "✓ Hooks configured"`

**Step 4: Generate initial index**
!`python3 scripts/enhanced_project_index.py && echo "✓ Initial PROJECT_INDEX.json created"`

**Step 5: Add to .gitignore (optional)**
!`echo -e "\n# Claude Code Project Index\n.claude/\nPROJECT_INDEX.json" >> .gitignore && echo "✓ Added to .gitignore"`

### Verification:

Check that everything works: !`ls -la PROJECT_INDEX.json .claude/settings.json scripts/`

🎉 **Your project is now ready for automatic indexing with Claude Code!**

Use `/semantic-index`, `/duplicates`, and `/analyze` commands to manage your project intelligence.