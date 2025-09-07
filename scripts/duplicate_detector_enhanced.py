#!/usr/bin/env python3
"""
Enhanced PostToolUse hook for dual-mode duplicate code detection.
Supports both blocking (active) and passive (monitoring) modes.
"""

import json
import sys
import os
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

# Import utilities from index_utils
try:
    from index_utils import (
        find_similar_functions,
        create_ast_fingerprint,
        create_tfidf_embeddings,
        compute_code_similarity,
        normalize_code_for_comparison,
        extract_python_signatures,
        extract_javascript_signatures,
        extract_shell_signatures,
        PARSEABLE_LANGUAGES
    )
    from duplicate_detector import DuplicateDetector
except ImportError:
    # Add current directory to path for imports
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from index_utils import (
        find_similar_functions,
        create_ast_fingerprint,
        create_tfidf_embeddings,
        compute_code_similarity,
        normalize_code_for_comparison,
        extract_python_signatures,
        extract_javascript_signatures,
        extract_shell_signatures,
        PARSEABLE_LANGUAGES
    )
    from duplicate_detector import DuplicateDetector


class EnhancedDuplicateDetector(DuplicateDetector):
    """Enhanced duplicate detector with dual-mode support."""
    
    def __init__(self, project_root: str):
        super().__init__(project_root)
        self.mode_config_path = self.project_root / '.claude' / 'duplicate_detection_mode.json'
        self.detection_log_path = self.project_root / '.claude' / 'duplicate_detection.log'
        self.stats_path = self.project_root / '.claude' / 'duplicate_stats.json'
        self.load_mode_config()
        self.load_stats()
    
    def load_mode_config(self):
        """Load mode configuration (blocking vs passive)."""
        default_config = {
            "mode": "blocking",  # "blocking" or "passive"
            "similarity_threshold": 0.8,
            "block_exact_duplicates": True,
            "block_high_similarity": True,
            "block_naming_conflicts": False,
            "log_all_detections": True,
            "show_suggestions": True,
            "last_updated": time.time()
        }
        
        if self.mode_config_path.exists():
            try:
                with open(self.mode_config_path, 'r') as f:
                    self.config = json.load(f)
                # Merge with defaults for any missing keys
                for key, value in default_config.items():
                    if key not in self.config:
                        self.config[key] = value
            except Exception as e:
                print(f"Warning: Could not load mode config: {e}", file=sys.stderr)
                self.config = default_config
        else:
            self.config = default_config
            self.save_mode_config()
    
    def save_mode_config(self):
        """Save current mode configuration."""
        self.config['last_updated'] = time.time()
        os.makedirs(self.mode_config_path.parent, exist_ok=True)
        try:
            with open(self.mode_config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save mode config: {e}", file=sys.stderr)
    
    def load_stats(self):
        """Load detection statistics."""
        default_stats = {
            "total_detections": 0,
            "exact_duplicates_found": 0,
            "semantic_similarities_found": 0,
            "naming_conflicts_found": 0,
            "blocks_prevented": 0,
            "passive_warnings_issued": 0,
            "last_detection": None,
            "session_start": time.time()
        }
        
        if self.stats_path.exists():
            try:
                with open(self.stats_path, 'r') as f:
                    self.stats = json.load(f)
                # Merge with defaults
                for key, value in default_stats.items():
                    if key not in self.stats:
                        self.stats[key] = value
            except Exception as e:
                print(f"Warning: Could not load stats: {e}", file=sys.stderr)
                self.stats = default_stats
        else:
            self.stats = default_stats
    
    def save_stats(self):
        """Save detection statistics."""
        os.makedirs(self.stats_path.parent, exist_ok=True)
        try:
            with open(self.stats_path, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save stats: {e}", file=sys.stderr)
    
    def log_detection(self, detection_type: str, details: Dict[str, Any]):
        """Log detection event."""
        if not self.config.get('log_all_detections', True):
            return
        
        log_entry = {
            "timestamp": time.time(),
            "type": detection_type,
            "mode": self.config['mode'],
            "details": details
        }
        
        os.makedirs(self.detection_log_path.parent, exist_ok=True)
        try:
            with open(self.detection_log_path, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            print(f"Warning: Could not write log: {e}", file=sys.stderr)
    
    def update_stats(self, duplicates: List[Dict[str, Any]], blocked: bool):
        """Update detection statistics."""
        self.stats['total_detections'] += 1
        self.stats['last_detection'] = time.time()
        
        for duplicate in duplicates:
            if duplicate['type'] == 'exact_structural_duplicate':
                self.stats['exact_duplicates_found'] += 1
            elif duplicate['type'] == 'semantic_similarity':
                self.stats['semantic_similarities_found'] += 1
            elif duplicate['type'] == 'similar_naming':
                self.stats['naming_conflicts_found'] += 1
        
        if blocked:
            self.stats['blocks_prevented'] += 1
        else:
            self.stats['passive_warnings_issued'] += 1
        
        self.save_stats()
    
    def analyze_with_mode_awareness(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze code change with mode-aware response."""
        # Perform standard duplicate analysis
        analysis = self.analyze_code_change(tool_input)
        
        if analysis.get('no_duplicates', True):
            return {'no_duplicates': True}
        
        duplicates = analysis.get('duplicates', [])
        file_path = analysis.get('file_path', '')
        
        # Filter duplicates based on configuration
        filtered_duplicates = self._filter_duplicates_by_config(duplicates)
        
        if not filtered_duplicates:
            return {'no_duplicates': True}
        
        # Determine response based on mode
        mode = self.config['mode']
        should_block = mode == 'blocking' and self._should_block(filtered_duplicates)
        
        # Log the detection
        self.log_detection('duplicate_found', {
            'file_path': file_path,
            'duplicate_count': len(filtered_duplicates),
            'mode': mode,
            'blocked': should_block,
            'duplicates': filtered_duplicates
        })
        
        # Update statistics
        self.update_stats(filtered_duplicates, should_block)
        
        if should_block:
            # Blocking mode - prevent the operation
            return {
                'duplicates_found': True,
                'mode': 'blocking',
                'duplicates': filtered_duplicates,
                'file_path': file_path,
                'block_operation': True
            }
        else:
            # Passive mode - just inform
            return {
                'duplicates_found': True,
                'mode': 'passive',
                'duplicates': filtered_duplicates,
                'file_path': file_path,
                'block_operation': False
            }
    
    def _filter_duplicates_by_config(self, duplicates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter duplicates based on configuration settings."""
        filtered = []
        
        for duplicate in duplicates:
            include = False
            
            if duplicate['type'] == 'exact_structural_duplicate' and self.config.get('block_exact_duplicates', True):
                include = True
            elif duplicate['type'] == 'semantic_similarity':
                similarity = duplicate.get('similarity', 0)
                threshold = self.config.get('similarity_threshold', 0.8)
                if similarity >= threshold and self.config.get('block_high_similarity', True):
                    include = True
            elif duplicate['type'] == 'similar_naming' and self.config.get('block_naming_conflicts', False):
                include = True
            
            if include:
                filtered.append(duplicate)
        
        return filtered
    
    def _should_block(self, duplicates: List[Dict[str, Any]]) -> bool:
        """Determine if operation should be blocked based on duplicates found."""
        # Always block exact duplicates in blocking mode
        exact_duplicates = [d for d in duplicates if d['type'] == 'exact_structural_duplicate']
        if exact_duplicates:
            return True
        
        # Block high similarity if configured
        high_similarity = [d for d in duplicates if d['type'] == 'semantic_similarity' and d.get('similarity', 0) >= 0.9]
        if high_similarity and self.config.get('block_high_similarity', True):
            return True
        
        return False
    
    def generate_mode_aware_message(self, duplicates: List[Dict[str, Any]], file_path: str, mode: str) -> str:
        """Generate appropriate message based on mode."""
        if mode == 'blocking':
            return self.generate_warning_message(duplicates, file_path)
        else:
            return self.generate_passive_message(duplicates, file_path)
    
    def generate_passive_message(self, duplicates: List[Dict[str, Any]], file_path: str) -> str:
        """Generate passive monitoring message."""
        if not duplicates:
            return ""
        
        messages = ["ℹ️ Duplicate code detected (passive mode):"]
        
        # Group by type
        exact_duplicates = [d for d in duplicates if d['type'] == 'exact_structural_duplicate']
        semantic_duplicates = [d for d in duplicates if d['type'] == 'semantic_similarity']
        naming_duplicates = [d for d in duplicates if d['type'] == 'similar_naming']
        
        if exact_duplicates:
            messages.append("\\n🔍 Exact duplicates found:")
            for dup in exact_duplicates[:2]:  # Limit to top 2
                messages.append(f"  • {dup['message']}")
                messages.append(f"    Similar to: {dup['existing_function']}")
        
        if semantic_duplicates:
            messages.append("\\n📊 Similar implementations found:")
            for dup in semantic_duplicates[:2]:  # Limit to top 2
                messages.append(f"  • {dup['message']}")
                messages.append(f"    Similar to: {dup['existing_function']}")
        
        if naming_duplicates:
            messages.append("\\n📝 Similar names found:")
            for dup in naming_duplicates[:1]:  # Limit to top 1
                messages.append(f"  • {dup['message']}")
        
        if self.config.get('show_suggestions', True):
            messages.append("\\n💡 Suggestions:")
            messages.append("  • Review existing implementations before continuing")
            messages.append("  • Consider consolidating similar functionality")
            messages.append("  • Switch to blocking mode: /duplicate-mode blocking")
        
        return "\\n".join(messages)
    
    def get_mode_status(self) -> Dict[str, Any]:
        """Get current mode and statistics for status display."""
        return {
            'mode': self.config['mode'],
            'active': self.config['mode'] == 'blocking',
            'stats': self.stats,
            'config': self.config,
            'last_detection': self.stats.get('last_detection'),
            'session_detections': self.stats.get('total_detections', 0)
        }


def main():
    """Main hook entry point with dual-mode support."""
    try:
        # Read hook input from stdin
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Extract relevant information
    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})
    
    # Only process code editing tools
    if tool_name not in ['Edit', 'Write', 'MultiEdit']:
        sys.exit(0)
    
    # Get project directory
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR')
    if not project_dir:
        project_dir = os.getcwd()
    
    # Initialize enhanced detector
    detector = EnhancedDuplicateDetector(project_dir)
    
    # Analyze the code change with mode awareness
    analysis = detector.analyze_with_mode_awareness(tool_input)
    
    # If duplicates found, respond according to mode
    if analysis.get('duplicates_found', False):
        duplicates = analysis.get('duplicates', [])
        file_path = analysis.get('file_path', '')
        mode = analysis.get('mode', 'blocking')
        should_block = analysis.get('block_operation', False)
        
        message = detector.generate_mode_aware_message(duplicates, file_path, mode)
        
        if should_block:
            # Blocking mode - prevent operation
            output = {
                "decision": "block",
                "reason": message
            }
            print(json.dumps(output))
            sys.exit(0)
        else:
            # Passive mode - just inform (allow operation to proceed)
            # We could optionally output an info message here, but for now just log
            pass
    
    # No duplicates found or passive mode - allow operation to proceed
    sys.exit(0)


if __name__ == '__main__':
    main()