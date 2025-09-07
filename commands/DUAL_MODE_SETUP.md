# Dual-Mode Duplicate Detection Setup

This guide shows how to set up the enhanced dual-mode duplicate detection system with status line integration.

## 🔄 System Modes

### 1. **Blocking Mode** (Active)
- 🛡️ **Prevents** duplicate code from being written
- **Blocks** Claude's tool execution when duplicates detected
- **Immediate feedback** for course correction
- **Best for**: Active development, preventing technical debt

### 2. **Passive Mode** (Monitoring)
- 👁️ **Monitors** and logs duplicate code 
- **Allows** operations to proceed
- **Informs** Claude of duplicates without blocking
- **Best for**: Legacy codebases, learning phase

### 3. **Inactive Mode** (Off)
- ⚪ **Disables** duplicate detection entirely
- **No monitoring** or blocking
- **Best for**: Temporary development, testing

## 🚀 Quick Setup

### 1. Copy Enhanced Settings
```bash
cp .claude/settings_dual_mode.json .claude/settings.json
```

### 2. Initialize Mode Configuration
```bash
# Start in blocking mode (recommended)
python scripts/duplicate_mode_toggle.py blocking

# Or start in passive mode
python scripts/duplicate_mode_toggle.py passive
```

### 3. Build Semantic Index (if not done already)
```bash
python scripts/semantic_analyzer.py
```

## 📊 Status Line Integration

The status line shows real-time duplicate detection status:

### Status Line Format:
```
[Model] 📁 project | 🛡️ DD-Active(5:3:2) 2m | 🌿 main
```

**Breakdown:**
- `[Model]` - Current Claude model
- `📁 project` - Current directory
- `🛡️ DD-Active` - Detection mode (🛡️=blocking, 👁️=passive, ⚪=inactive)
- `(5:3:2)` - Stats: (total:blocks:warnings)
- `2m` - Time since last detection
- `🌿 main` - Git branch

### Status Icons:
- 🛡️ **DD-Active** - Blocking mode enabled
- 👁️ **DD-Monitor** - Passive monitoring enabled  
- ⚪ **DD-Inactive** - System disabled
- ❓ **DD-Unknown** - Configuration error

## 🔧 Mode Management

### Quick Mode Switches:
```bash
# Switch to blocking mode
python scripts/duplicate_mode_toggle.py blocking

# Switch to passive monitoring
python scripts/duplicate_mode_toggle.py passive

# Turn off detection
python scripts/duplicate_mode_toggle.py off
```

### Advanced Configuration:
```bash
# Set custom similarity threshold
python scripts/duplicate_mode_toggle.py set passive --threshold 0.7

# Configure what to block/monitor
python scripts/duplicate_mode_toggle.py set blocking --block-exact --no-block-naming
```

### Check Status:
```bash
python scripts/duplicate_mode_toggle.py status
```

Example output:
```
🔧 Duplicate Detection System Status
========================================
🛡️ Mode: BLOCKING (Active - blocks duplicate code)

📋 Configuration:
  • Similarity Threshold: 80%
  • Block Exact Duplicates: ✅
  • Block High Similarity: ✅
  • Block Naming Conflicts: ❌
  • Last Updated: 2024-08-23 14:30:15

📊 Detection Statistics:
  • Total Detections: 12
  • Blocks Prevented: 8
  • Passive Warnings: 4
  • Exact Duplicates: 3
  • Semantic Similarities: 9
  • Last Detection: 2024-08-23 14:25:42
```

## 🎯 Usage Patterns

### Development Workflow:
1. **Start in passive mode** to learn codebase patterns
2. **Review detection logs** to understand duplicate patterns  
3. **Switch to blocking mode** for active duplicate prevention
4. **Monitor status line** for real-time feedback

### Team Collaboration:
1. **Passive mode** for junior developers (learning)
2. **Blocking mode** for senior developers (enforcement)
3. **Share detection logs** for code review discussions

### Legacy Cleanup:
1. **Passive mode** during initial analysis
2. **Use cleanup tools** to eliminate existing duplicates
3. **Switch to blocking mode** to prevent new duplicates

## ⚙️ Configuration Files

### Mode Configuration (`/.claude/duplicate_detection_mode.json`):
```json
{
  "mode": "blocking",
  "similarity_threshold": 0.8,
  "block_exact_duplicates": true,
  "block_high_similarity": true,
  "block_naming_conflicts": false,
  "log_all_detections": true,
  "show_suggestions": true
}
```

### Detection Statistics (`/.claude/duplicate_stats.json`):
```json
{
  "total_detections": 12,
  "exact_duplicates_found": 3,
  "semantic_similarities_found": 9,
  "blocks_prevented": 8,
  "passive_warnings_issued": 4,
  "last_detection": 1692794742.123
}
```

## 🔍 Monitoring & Debugging

### View Detection Log:
```bash
tail -f .claude/duplicate_detection.log
```

### Reset Statistics:
```bash
python scripts/duplicate_mode_toggle.py reset-stats
```

### Test Status Line:
```bash
echo '{"model":{"display_name":"Test"},"workspace":{"current_dir":"'$(pwd)'"}}' | ./.claude/duplicate-status.sh
```

## 🚨 Troubleshooting

### Status Line Not Showing:
1. Verify script is executable: `chmod +x .claude/duplicate-status.sh`
2. Check settings.json has statusLine configuration
3. Test script manually (see test command above)

### Mode Changes Not Taking Effect:
1. Check .claude/settings.json was updated
2. Restart Claude Code session
3. Verify hook configuration with `python scripts/duplicate_mode_toggle.py status`

### No Detections Happening:
1. Ensure semantic index exists: `python scripts/semantic_analyzer.py`
2. Check mode is not "inactive"
3. Verify scripts are executable and error-free

## 💡 Pro Tips

- **Use passive mode initially** to understand your codebase's duplicate patterns
- **Monitor the status line** to see detection activity in real-time
- **Switch modes based on context** (blocking for new features, passive for exploration)
- **Review detection logs** to improve your coding patterns
- **Share statistics** with team for duplicate reduction metrics

## 📈 Success Metrics

Track your duplicate reduction progress:
- **Blocks Prevented**: How many duplicates were stopped
- **Detection Rate**: Total detections per coding session
- **Mode Effectiveness**: Compare blocking vs passive results
- **Time to Detection**: How quickly duplicates are caught

The dual-mode system gives you flexible control over duplicate detection while providing rich feedback through the status line! 🎉