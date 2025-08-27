#!/usr/bin/env bash
set -eo pipefail

# Claude Code PROJECT_INDEX Uninstaller
# Removes PROJECT_INDEX from ~/.claude-code-project-index

echo "Claude Code PROJECT_INDEX Uninstaller"
echo "======================================"
echo ""

INSTALL_DIR="$HOME/.claude-code-project-index"

echo "This will remove:"
echo "  • PROJECT_INDEX hooks from ~/.claude/settings.json"
echo "  • Installation directory at $INSTALL_DIR"
echo "  • Old /index command if present"
echo ""
echo "⚠️  Note: This will NOT remove:"
echo "  • Any PROJECT_INDEX.json files in your projects"
echo ""

# Check if we're running interactively or via pipe
if [ -t 0 ]; then
    # Interactive mode - can use read
    read -p "Continue with uninstall? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Uninstall cancelled"
        exit 0
    fi
else
    # Non-interactive mode (curl | bash) - skip confirmation
    echo "Running in non-interactive mode, proceeding with uninstall..."
    echo ""
fi

echo ""
echo "Uninstalling PROJECT_INDEX..."

# Remove /index command file
if [[ -f "$HOME/.claude/commands/index.md" ]]; then
    echo "Removing /index command..."
    rm -f "$HOME/.claude/commands/index.md"
    echo "✓ /index command removed"
fi

# Remove hooks from settings.json
SETTINGS_FILE="$HOME/.claude/settings.json"
if [[ -f "$SETTINGS_FILE" ]]; then
    echo "Removing hooks from settings.json..."
    
    # Backup settings
    cp "$SETTINGS_FILE" "${SETTINGS_FILE}.uninstall-backup"
    
    # Remove PROJECT_INDEX hooks using jq
    jq '
      # Remove PROJECT_INDEX UserPromptSubmit hooks
      if .hooks.UserPromptSubmit then
        .hooks.UserPromptSubmit = [.hooks.UserPromptSubmit[] | select(
          all(.hooks[]?.command // ""; 
            contains("claude-code-project-index") | not) and
          all(.hooks[]?.command // ""; 
            contains("i_flag_hook.py") | not) and
          all(.hooks[]?.command // ""; 
            contains("project_index") | not)
        )]
      else . end |
      
      # Remove PROJECT_INDEX PostToolUse hooks
      if .hooks.PostToolUse then
        .hooks.PostToolUse = [.hooks.PostToolUse[] | select(
          all(.hooks[]?.command // ""; 
            contains("claude-code-project-index") | not) and
          all(.hooks[]?.command // ""; 
            contains("update_index.py") | not) and
          all(.hooks[]?.command // ""; 
            contains("project_index") | not)
        )]
      else . end |
      
      # Remove PROJECT_INDEX Stop hooks
      if .hooks.Stop then
        .hooks.Stop = [.hooks.Stop[] | select(
          all(.hooks[]?.command // ""; 
            contains("claude-code-project-index") | not) and
          all(.hooks[]?.command // ""; 
            contains("stop_hook.py") | not) and
          all(.hooks[]?.command // ""; 
            contains("reindex_if_needed.py") | not) and
          all(.hooks[]?.command // ""; 
            contains("project_index") | not)
        )]
      else . end |
      
      # Clean up empty arrays
      if .hooks.UserPromptSubmit == [] then del(.hooks.UserPromptSubmit) else . end |
      if .hooks.PostToolUse == [] then del(.hooks.PostToolUse) else . end |
      if .hooks.Stop == [] then del(.hooks.Stop) else . end |
      
      # Clean up empty hooks object
      if .hooks == {} then del(.hooks) else . end
    ' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"
    
    echo "✓ Hooks removed"
fi

# Remove installation directory
if [[ -d "$INSTALL_DIR" ]]; then
    echo "Removing installation directory..."
    rm -rf "$INSTALL_DIR"
    echo "✓ Directory removed"
fi

echo ""
echo "=========================================="
echo "✅ PROJECT_INDEX uninstalled successfully!"
echo "=========================================="
echo ""
echo "📝 Manual cleanup (if desired):"
echo "   Remove PROJECT_INDEX.json files from your projects:"
echo "   • Find them with: find ~ -name 'PROJECT_INDEX.json' -type f 2>/dev/null"
echo ""
echo "To reinstall, run:"
echo "   curl -fsSL https://raw.githubusercontent.com/ericbuess/claude-code-project-index/main/install.sh | bash"