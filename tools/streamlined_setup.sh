#!/usr/bin/env bash
# Streamlined setup for duplicate detection system
# Addresses common friction points and automates the full setup

set -eo pipefail

PROJECT_ROOT="$(pwd)"
SYSTEM_DIR="$HOME/.claude-code-project-index"

echo "🚀 Streamlined Duplicate Detection Setup"
echo "=" * 50

# Step 1: Verify system installation
if [[ ! -d "$SYSTEM_DIR" ]]; then
    echo "❌ Claude Code Project Index not found at $SYSTEM_DIR"
    echo "💡 Please install first: https://github.com/your-repo/claude-code-project-index"
    exit 1
fi

echo "✅ System found at $SYSTEM_DIR"

# Step 2: Create PROJECT_INDEX.json with semantic analysis
echo ""
echo "📊 Step 1: Building comprehensive project index..."
if bash "$SYSTEM_DIR/scripts/project-index-helper.sh"; then
    echo "✅ Basic index created"
else
    echo "❌ Failed to create basic index"
    exit 1
fi

# Step 3: Run semantic analysis automatically
echo ""
echo "🧠 Step 2: Adding semantic analysis (duplicate detection)..."
if python3 "$SYSTEM_DIR/scripts/semantic_analyzer.py" "$PROJECT_ROOT"; then
    echo "✅ Semantic analysis complete"
else
    echo "❌ Failed to run semantic analysis"
    echo "💡 Make sure sklearn is installed: pip install scikit-learn"
    exit 1
fi

# Step 4: Set up dual-mode configuration
echo ""
echo "⚙️ Step 3: Configuring dual-mode detection..."

# Create .claude directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/.claude"

# Copy enhanced settings
if cp "$SYSTEM_DIR/.claude/settings_dual_mode.json" "$PROJECT_ROOT/.claude/settings.json"; then
    echo "✅ Dual-mode hooks configured"
else
    echo "❌ Failed to configure hooks"
    exit 1
fi

# Initialize in passive mode (safer for first-time users)
if python3 "$SYSTEM_DIR/scripts/duplicate_mode_toggle.py" --project-root "$PROJECT_ROOT" passive; then
    echo "✅ Initialized in passive mode (safe for learning)"
else
    echo "❌ Failed to initialize mode"
    exit 1
fi

# Step 5: Generate initial duplicate report
echo ""
echo "📋 Step 4: Generating initial duplicate analysis..."
if python3 "$SYSTEM_DIR/scripts/generate_duplicate_report.py" --project-root "$PROJECT_ROOT" --format markdown --output "DUPLICATE_ANALYSIS_REPORT.md"; then
    echo "✅ Duplicate report saved to DUPLICATE_ANALYSIS_REPORT.md"
else
    echo "❌ Failed to generate duplicate report"
    exit 1
fi

# Step 6: Test status line
echo ""
echo "📈 Step 5: Testing status line..."
if echo '{"model":{"display_name":"Test"},"workspace":{"current_dir":"'$PROJECT_ROOT'"}}' | "$SYSTEM_DIR/.claude/duplicate-status.sh" > /dev/null 2>&1; then
    echo "✅ Status line working"
else
    echo "❌ Status line test failed"
    exit 1
fi

# Success summary
echo ""
echo "🎉 Setup Complete!"
echo "=" * 30
echo ""
echo "📊 Your duplicate detection system is now active with:"
echo "  • 👁️ PASSIVE MODE - Monitors duplicates without blocking"
echo "  • 📈 STATUS LINE - Real-time detection status"
echo "  • 📋 DUPLICATE REPORT - Initial analysis completed"
echo ""
echo "🔧 Quick Commands:"
echo "  • Switch to blocking: python3 $SYSTEM_DIR/scripts/duplicate_mode_toggle.py blocking"
echo "  • View status: python3 $SYSTEM_DIR/scripts/duplicate_mode_toggle.py status"
echo "  • Interactive cleanup: python3 $SYSTEM_DIR/scripts/interactive_cleanup.py"
echo ""
echo "📄 Files Created:"
echo "  • PROJECT_INDEX.json (with semantic analysis)"
echo "  • .claude/settings.json (dual-mode configuration)"
echo "  • DUPLICATE_ANALYSIS_REPORT.md (initial analysis)"
echo ""
echo "💡 Next Steps:"
echo "  1. Read DUPLICATE_ANALYSIS_REPORT.md to see current duplicates"
echo "  2. Start in PASSIVE mode to learn the system"
echo "  3. Switch to BLOCKING mode when ready: duplicate_mode_toggle.py blocking"
echo ""
echo "🚀 Claude Code will now show duplicate detection status in the status line!"