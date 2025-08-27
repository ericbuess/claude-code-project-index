#!/usr/bin/env bash
set -eo pipefail

# Claude Code PROJECT_INDEX Installer
# Installs PROJECT_INDEX to ~/.claude-code-project-index

echo "Claude Code PROJECT_INDEX Installer"
echo "===================================="
echo ""

# Fixed installation location
INSTALL_DIR="$HOME/.claude-code-project-index"

# Detect OS type
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="macos"
    echo "✓ Detected macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_TYPE="linux"
    echo "✓ Detected Linux"
else
    echo "❌ Error: Unsupported OS type: $OSTYPE"
    echo "This installer supports macOS and Linux only"
    exit 1
fi

# Check dependencies
echo ""
echo "Checking dependencies..."

# Check for git and jq
for cmd in git jq; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "❌ Error: $cmd is required but not installed"
        echo "Please install $cmd and try again"
        exit 1
    fi
done

# Find Python intelligently
# When running via curl | bash, BASH_SOURCE is not set
if [[ -n "${BASH_SOURCE[0]:-}" ]]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
else
    # Running via curl | bash - scripts won't be available yet
    SCRIPT_DIR=""
fi

if [[ -n "$SCRIPT_DIR" && -f "$SCRIPT_DIR/scripts/find_python.sh" ]]; then
    PYTHON_CMD=$(bash "$SCRIPT_DIR/scripts/find_python.sh")
else
    # Fallback to simple check if find_python.sh doesn't exist yet
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo "❌ Error: Python 3.8+ is required but not found"
        echo "Please install Python 3.8+ and try again"
        exit 1
    fi
fi

if [[ -z "$PYTHON_CMD" ]]; then
    exit 1
fi

echo "✓ All dependencies satisfied"

# Check if already installed
if [[ -d "$INSTALL_DIR" ]]; then
    echo ""
    echo "⚠️  Found existing installation at $INSTALL_DIR"
    
    # Check if we're running interactively or via pipe
    if [ -t 0 ]; then
        # Interactive mode - can use read
        read -p "Remove and reinstall? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Installation cancelled"
            exit 0
        fi
    else
        # Non-interactive mode (curl | bash) - auto-reinstall
        echo "Running in non-interactive mode, removing and reinstalling..."
    fi
    
    echo "Removing existing installation..."
    rm -rf "$INSTALL_DIR"
fi

# Clone or copy repository
echo ""
echo "Installing PROJECT_INDEX..."

# If we're running from the repo, copy files
# (SCRIPT_DIR already set above during Python detection)
if [[ -f "$SCRIPT_DIR/scripts/project_index.py" || -f "$SCRIPT_DIR/README.md" ]]; then
    echo "Installing from local repository..."
    
    # Create install directory
    mkdir -p "$INSTALL_DIR"
    
    # Copy essential files
    cp "$SCRIPT_DIR/install.sh" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/uninstall.sh" "$INSTALL_DIR/" 2>/dev/null || true
    cp "$SCRIPT_DIR/scripts/project-index-helper.sh" "$INSTALL_DIR/scripts/" 2>/dev/null || true
    cp "$SCRIPT_DIR/README.md" "$INSTALL_DIR/" 2>/dev/null || true
    cp "$SCRIPT_DIR/LICENSE" "$INSTALL_DIR/" 2>/dev/null || true
    cp "$SCRIPT_DIR/.gitignore" "$INSTALL_DIR/" 2>/dev/null || true
    
    # Create scripts directory and copy all scripts
    mkdir -p "$INSTALL_DIR/scripts"
    cp "$SCRIPT_DIR"/*.py "$INSTALL_DIR/scripts/" 2>/dev/null || true
    cp "$SCRIPT_DIR/scripts"/*.py "$INSTALL_DIR/scripts/" 2>/dev/null || true
    cp "$SCRIPT_DIR/scripts"/*.sh "$INSTALL_DIR/scripts/" 2>/dev/null || true
    
    # Remove the old setup script if it was copied
    rm -f "$INSTALL_DIR/scripts/setup_hooks.py"
    
    echo "✓ Files copied to $INSTALL_DIR"
else
    # Clone from GitHub
    echo "Cloning from GitHub..."
    git clone https://github.com/ericbuess/claude-code-project-index.git "$INSTALL_DIR"
    
    # Move Python files to scripts directory
    mkdir -p "$INSTALL_DIR/scripts"
    mv "$INSTALL_DIR"/*.py "$INSTALL_DIR/scripts/" 2>/dev/null || true
    rm -f "$INSTALL_DIR/scripts/setup_hooks.py"
    
    echo "✓ Repository cloned to $INSTALL_DIR"
fi

# Make scripts executable
chmod +x "$INSTALL_DIR/install.sh" 2>/dev/null || true
chmod +x "$INSTALL_DIR/uninstall.sh" 2>/dev/null || true
chmod +x "$INSTALL_DIR/scripts/project-index-helper.sh" 2>/dev/null || true
chmod +x "$INSTALL_DIR/scripts/find_python.sh" 2>/dev/null || true
chmod +x "$INSTALL_DIR/scripts/run_python.sh" 2>/dev/null || true

# Save the Python command for later use
echo "$PYTHON_CMD" > "$INSTALL_DIR/.python_cmd"
echo "   ✓ Python command saved: $PYTHON_CMD"

# Create /index command
echo ""
echo "Creating /index command..."
mkdir -p "$HOME/.claude/commands"
cat > "$HOME/.claude/commands/index.md" << 'EOF'
---
name: index
description: Create or update PROJECT_INDEX.json for the current project
---

# PROJECT_INDEX Command

This command creates or updates a PROJECT_INDEX.json file that gives Claude architectural awareness of your codebase.

The indexer script is located at:
`~/.claude-code-project-index/scripts/project_index.py`

## What it does

The PROJECT_INDEX creates a comprehensive map of your project including:
- Directory structure and file organization
- Function and class signatures with type annotations
- Call graphs showing what calls what
- Import dependencies
- Documentation structure
- Directory purposes

## Usage

Simply type `/index` in any project directory to create or update the index.

## About the Tool

**PROJECT_INDEX** is a community tool created by Eric Buess that helps Claude Code understand your project structure better. 

- **GitHub**: https://github.com/ericbuess/claude-code-project-index
- **Purpose**: Prevents code duplication, ensures proper file placement, maintains architectural consistency
- **Philosophy**: Fork and customize for your needs - Claude can modify it instantly

## How to Use the Index

After running `/index`, you can:
1. Reference it directly: `@PROJECT_INDEX.json what functions call authenticate_user?`
2. Use with -i flag: `refactor the auth system -i`
3. Add to CLAUDE.md for auto-loading: `@PROJECT_INDEX.json`

## Implementation

When you run `/index`, Claude will:
1. Check if PROJECT_INDEX is installed at ~/.claude-code-project-index
2. Run the indexer script at ~/.claude-code-project-index/scripts/project_index.py to create/update PROJECT_INDEX.json
3. Provide feedback on what was indexed
4. The index is then available as PROJECT_INDEX.json

## Troubleshooting

If the index is too large for your project, ask Claude:
"The indexer creates too large an index. Please modify it to only index src/ and lib/ directories"

For other issues, the tool is designed to be customized - just describe your problem to Claude!
EOF
echo "✓ Created /index command"

# Update hooks in settings.json
echo ""
echo "Configuring hooks..."

SETTINGS_FILE="$HOME/.claude/settings.json"

# Ensure settings.json exists
if [[ ! -f "$SETTINGS_FILE" ]]; then
    echo "{}" > "$SETTINGS_FILE"
fi

# Create a backup
cp "$SETTINGS_FILE" "${SETTINGS_FILE}.backup"

# Update hooks using jq - removes old PROJECT_INDEX hooks and adds new ones
jq '
  # Initialize hooks if not present
  if .hooks == null then .hooks = {} else . end |
  
  # Initialize UserPromptSubmit if not present (for index-aware mode)
  if .hooks.UserPromptSubmit == null then .hooks.UserPromptSubmit = [] else . end |
  
  # Filter out any existing PROJECT_INDEX UserPromptSubmit hooks, then add the new one
  .hooks.UserPromptSubmit = ([.hooks.UserPromptSubmit[] | select(
    all(.hooks[]?.command // ""; 
      contains("i_flag_hook.py") | not) and
    all(.hooks[]?.command // ""; 
      contains("project_index") | not)
  )] + [{
    "hooks": [{
      "type": "command",
      "command": "'"$HOME"'/.claude-code-project-index/scripts/run_python.sh '"$HOME"'/.claude-code-project-index/scripts/i_flag_hook.py",
      "timeout": 20
    }]
  }]) |
  
  # Initialize Stop if not present
  if .hooks.Stop == null then .hooks.Stop = [] else . end |
  
  # Filter out any existing PROJECT_INDEX Stop hooks, then add the new one
  .hooks.Stop = ([.hooks.Stop[] | select(
    all(.hooks[]?.command // ""; 
      contains("stop_hook.py") | not) and
    all(.hooks[]?.command // ""; 
      contains("reindex_if_needed.py") | not) and
    all(.hooks[]?.command // ""; 
      contains("project_index") | not)
  )] + [{
    "matcher": "",
    "hooks": [{
      "type": "command",
      "command": "'"$HOME"'/.claude-code-project-index/scripts/run_python.sh '"$HOME"'/.claude-code-project-index/scripts/stop_hook.py",
      "timeout": 10
    }]
  }])
' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"

echo "✓ Hooks configured in settings.json"

# Test installation
echo ""
echo "Testing installation..."
if $PYTHON_CMD "$INSTALL_DIR/scripts/project_index.py" --version 2>/dev/null | grep -q "PROJECT_INDEX"; then
    echo "✓ Installation test passed"
else
    echo "⚠️  Version check failed, but installation completed"
    echo "   You can still use /index command normally"
fi

echo ""
echo "=========================================="
echo "✅ PROJECT_INDEX installed successfully!"
echo "=========================================="
echo ""
echo "📁 Installation location: $INSTALL_DIR"
echo ""
echo "📝 Manual cleanup needed:"
echo "   Please remove these old files from ~/.claude/scripts/ if they exist:"
echo "   • project_index.py"
echo "   • update_index.py"
echo "   • reindex_if_needed.py"
echo "   • index_utils.py"
echo "   • detect_external_changes.py"
echo ""
echo "🚀 Usage:"
echo "   • Add -i flag to any prompt for index-aware mode (e.g., 'fix auth bug -i')"
echo "   • Use -ic flag to export to clipboard for large context AI models"
echo "   • Reference with @PROJECT_INDEX.json when you need architectural awareness"
echo "   • The index is created automatically when you use -i flag"
echo ""
echo "📚 For more information, see: $INSTALL_DIR/README.md"