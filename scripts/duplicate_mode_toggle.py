#!/usr/bin/env python3
"""
Mode toggle utility for duplicate detection system.
Allows switching between blocking and passive modes.
"""

import json
import sys
import os
import argparse
import time
from pathlib import Path
from typing import Dict, Any


class DuplicateModeManager:
    """Manages duplicate detection mode configuration."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.mode_config_path = self.project_root / '.claude' / 'duplicate_detection_mode.json'
        self.stats_path = self.project_root / '.claude' / 'duplicate_stats.json'
        self.settings_path = self.project_root / '.claude' / 'settings.json'
    
    def get_current_mode(self) -> Dict[str, Any]:
        """Get current mode configuration."""
        if not self.mode_config_path.exists():
            return {"mode": "not_configured", "error": "Mode config not found"}
        
        try:
            with open(self.mode_config_path, 'r') as f:
                config = json.load(f)
            return config
        except Exception as e:
            return {"mode": "error", "error": str(e)}
    
    def set_mode(self, mode: str, **options) -> Dict[str, Any]:
        """Set duplicate detection mode."""
        if mode not in ['blocking', 'passive', 'inactive']:
            return {"success": False, "error": f"Invalid mode: {mode}"}
        
        # Load existing config or create default
        if self.mode_config_path.exists():
            try:
                with open(self.mode_config_path, 'r') as f:
                    config = json.load(f)
            except Exception:
                config = self._get_default_config()
        else:
            config = self._get_default_config()
        
        # Update mode and options
        old_mode = config.get('mode', 'unknown')
        config['mode'] = mode
        config['last_updated'] = time.time()
        config['previous_mode'] = old_mode
        
        # Apply any additional options
        for key, value in options.items():
            if key in ['similarity_threshold', 'block_exact_duplicates', 
                      'block_high_similarity', 'block_naming_conflicts',
                      'log_all_detections', 'show_suggestions']:
                config[key] = value
        
        # Save configuration
        os.makedirs(self.mode_config_path.parent, exist_ok=True)
        try:
            with open(self.mode_config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            return {"success": False, "error": f"Could not save config: {e}"}
        
        # Update hooks configuration if needed
        if mode == 'inactive':
            self._disable_hooks()
        else:
            self._enable_hooks()
        
        return {
            "success": True,
            "old_mode": old_mode,
            "new_mode": mode,
            "config": config
        }
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "mode": "blocking",
            "similarity_threshold": 0.8,
            "block_exact_duplicates": True,
            "block_high_similarity": True,
            "block_naming_conflicts": False,
            "log_all_detections": True,
            "show_suggestions": True,
            "last_updated": time.time()
        }
    
    def _enable_hooks(self):
        """Enable duplicate detection hooks in settings."""
        self._update_hooks_config(enabled=True)
    
    def _disable_hooks(self):
        """Disable duplicate detection hooks in settings."""
        self._update_hooks_config(enabled=False)
    
    def _update_hooks_config(self, enabled: bool):
        """Update hooks configuration in .claude/settings.json."""
        if not self.settings_path.exists():
            # Create default settings if none exist
            settings = {"hooks": {}}
        else:
            try:
                with open(self.settings_path, 'r') as f:
                    settings = json.load(f)
            except Exception:
                settings = {"hooks": {}}
        
        if 'hooks' not in settings:
            settings['hooks'] = {}
        
        if enabled:
            # Enable PostToolUse hook
            settings['hooks']['PostToolUse'] = [
                {
                    "matcher": "Edit|Write|MultiEdit",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "$CLAUDE_PROJECT_DIR/scripts/duplicate_detector_enhanced.py",
                            "timeout": 5000
                        }
                    ]
                }
            ]
            
            # Ensure SessionStart hook is also enabled
            if 'SessionStart' not in settings['hooks']:
                settings['hooks']['SessionStart'] = [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "$CLAUDE_PROJECT_DIR/scripts/load_architecture_context.py"
                            }
                        ]
                    }
                ]
        else:
            # Remove PostToolUse hook for duplicate detection
            if 'PostToolUse' in settings['hooks']:
                # Remove or comment out duplicate detection hook
                post_hooks = settings['hooks']['PostToolUse']
                settings['hooks']['PostToolUse'] = [
                    hook for hook in post_hooks 
                    if 'duplicate_detector' not in hook.get('hooks', [{}])[0].get('command', '')
                ]
                
                # If no hooks left, remove the key
                if not settings['hooks']['PostToolUse']:
                    del settings['hooks']['PostToolUse']
        
        # Save updated settings
        os.makedirs(self.settings_path.parent, exist_ok=True)
        try:
            with open(self.settings_path, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not update hooks config: {e}", file=sys.stderr)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get detection statistics."""
        if not self.stats_path.exists():
            return {"stats_available": False}
        
        try:
            with open(self.stats_path, 'r') as f:
                stats = json.load(f)
            return {"stats_available": True, "stats": stats}
        except Exception as e:
            return {"stats_available": False, "error": str(e)}
    
    def reset_stats(self) -> bool:
        """Reset detection statistics."""
        try:
            if self.stats_path.exists():
                self.stats_path.unlink()
            return True
        except Exception:
            return False
    
    def show_status(self) -> str:
        """Show current status in human-readable format."""
        config = self.get_current_mode()
        stats_result = self.get_stats()
        
        status = []
        status.append("🔧 Duplicate Detection System Status")
        status.append("=" * 40)
        
        # Mode information
        mode = config.get('mode', 'unknown')
        if mode == 'blocking':
            status.append("🛡️ Mode: BLOCKING (Active - blocks duplicate code)")
        elif mode == 'passive':
            status.append("👁️ Mode: PASSIVE (Monitor - logs but allows duplicates)")
        elif mode == 'inactive':
            status.append("⚪ Mode: INACTIVE (System disabled)")
        else:
            status.append(f"❓ Mode: {mode.upper()}")
        
        # Configuration details
        if 'error' not in config:
            status.append(f"\n📋 Configuration:")
            status.append(f"  • Similarity Threshold: {config.get('similarity_threshold', 0.8)*100:.0f}%")
            status.append(f"  • Block Exact Duplicates: {'✅' if config.get('block_exact_duplicates') else '❌'}")
            status.append(f"  • Block High Similarity: {'✅' if config.get('block_high_similarity') else '❌'}")
            status.append(f"  • Block Naming Conflicts: {'✅' if config.get('block_naming_conflicts') else '❌'}")
            
            last_updated = config.get('last_updated')
            if last_updated:
                import datetime
                update_time = datetime.datetime.fromtimestamp(last_updated).strftime('%Y-%m-%d %H:%M:%S')
                status.append(f"  • Last Updated: {update_time}")
        
        # Statistics
        if stats_result.get('stats_available'):
            stats = stats_result['stats']
            status.append(f"\n📊 Detection Statistics:")
            status.append(f"  • Total Detections: {stats.get('total_detections', 0)}")
            status.append(f"  • Blocks Prevented: {stats.get('blocks_prevented', 0)}")
            status.append(f"  • Passive Warnings: {stats.get('passive_warnings_issued', 0)}")
            status.append(f"  • Exact Duplicates: {stats.get('exact_duplicates_found', 0)}")
            status.append(f"  • Semantic Similarities: {stats.get('semantic_similarities_found', 0)}")
            
            last_detection = stats.get('last_detection')
            if last_detection:
                import datetime
                detection_time = datetime.datetime.fromtimestamp(last_detection).strftime('%Y-%m-%d %H:%M:%S')
                status.append(f"  • Last Detection: {detection_time}")
        else:
            status.append(f"\n📊 No statistics available")
        
        return "\n".join(status)


def main():
    """Main CLI interface for mode management."""
    parser = argparse.ArgumentParser(description='Manage duplicate detection modes')
    parser.add_argument('--project-root', default='.', help='Project root directory')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show current status')
    
    # Set mode command
    set_parser = subparsers.add_parser('set', help='Set detection mode')
    set_parser.add_argument('mode', choices=['blocking', 'passive', 'inactive'], 
                           help='Detection mode')
    set_parser.add_argument('--threshold', type=float, help='Similarity threshold (0.0-1.0)')
    set_parser.add_argument('--block-exact', action='store_true', help='Block exact duplicates')
    set_parser.add_argument('--no-block-exact', action='store_true', help='Don\'t block exact duplicates')
    set_parser.add_argument('--block-similar', action='store_true', help='Block similar functions')
    set_parser.add_argument('--no-block-similar', action='store_true', help='Don\'t block similar functions')
    set_parser.add_argument('--block-naming', action='store_true', help='Block naming conflicts')
    set_parser.add_argument('--no-block-naming', action='store_true', help='Don\'t block naming conflicts')
    
    # Reset stats command
    reset_parser = subparsers.add_parser('reset-stats', help='Reset detection statistics')
    
    # Quick mode switches
    blocking_parser = subparsers.add_parser('blocking', help='Switch to blocking mode')
    passive_parser = subparsers.add_parser('passive', help='Switch to passive mode')
    off_parser = subparsers.add_parser('off', help='Turn off detection')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = DuplicateModeManager(args.project_root)
    
    if args.command == 'status':
        print(manager.show_status())
    
    elif args.command == 'set':
        options = {}
        if args.threshold is not None:
            options['similarity_threshold'] = args.threshold
        if args.block_exact:
            options['block_exact_duplicates'] = True
        elif args.no_block_exact:
            options['block_exact_duplicates'] = False
        if args.block_similar:
            options['block_high_similarity'] = True
        elif args.no_block_similar:
            options['block_high_similarity'] = False
        if args.block_naming:
            options['block_naming_conflicts'] = True
        elif args.no_block_naming:
            options['block_naming_conflicts'] = False
        
        result = manager.set_mode(args.mode, **options)
        if result['success']:
            print(f"✅ Mode changed from '{result['old_mode']}' to '{result['new_mode']}'")
        else:
            print(f"❌ Error: {result['error']}")
    
    elif args.command in ['blocking', 'passive', 'off']:
        mode_map = {'blocking': 'blocking', 'passive': 'passive', 'off': 'inactive'}
        mode = mode_map[args.command]
        
        result = manager.set_mode(mode)
        if result['success']:
            print(f"✅ Switched to {mode} mode")
        else:
            print(f"❌ Error: {result['error']}")
    
    elif args.command == 'reset-stats':
        if manager.reset_stats():
            print("✅ Statistics reset")
        else:
            print("❌ Failed to reset statistics")


if __name__ == '__main__':
    main()