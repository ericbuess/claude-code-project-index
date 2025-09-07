#!/usr/bin/env python3
"""
SessionStart hook to load architectural context and patterns.
Provides Claude with project-specific architectural information at session start.
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional


class ArchitectureContextLoader:
    """Loads and formats architectural context for Claude sessions."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.index_path = self.project_root / 'PROJECT_INDEX.json'
        self.index_data = None
        self.load_index()
    
    def load_index(self):
        """Load the project index."""
        if not self.index_path.exists():
            self.index_data = {}
            return
        
        try:
            with open(self.index_path, 'r') as f:
                self.index_data = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load index: {e}", file=sys.stderr)
            self.index_data = {}
    
    def generate_context(self) -> str:
        """Generate architectural context for Claude session."""
        if not self.index_data:
            return "No architectural context available."
        
        context_parts = []
        
        # Project overview
        context_parts.append("## Project Architecture & Patterns")
        context_parts.append(self._get_project_overview())
        
        # Semantic analysis information
        if 'semantic_index' in self.index_data:
            context_parts.append("\\n## Code Quality & Patterns")
            context_parts.append(self._get_semantic_context())
        
        # Directory structure and organization
        context_parts.append("\\n## Project Organization")
        context_parts.append(self._get_organization_context())
        
        # Known duplicate clusters and similar code
        if 'semantic_index' in self.index_data:
            similarity_context = self._get_similarity_context()
            if similarity_context:
                context_parts.append("\\n## Known Code Patterns & Duplicates")
                context_parts.append(similarity_context)
        
        # Recent changes and development patterns
        context_parts.append("\\n## Development Guidelines")
        context_parts.append(self._get_development_guidelines())
        
        return "\\n".join(context_parts)
    
    def _get_project_overview(self) -> str:
        """Get basic project overview information."""
        overview = []
        
        stats = self.index_data.get('stats', {})
        if stats:
            overview.append(f"📊 **Project Size:** {stats.get('total_files', 0)} files across {stats.get('total_directories', 0)} directories")
            
            parsed_langs = stats.get('fully_parsed', {})
            if parsed_langs:
                lang_counts = [f"{lang}: {count}" for lang, count in parsed_langs.items()]
                overview.append(f"🔧 **Languages:** {', '.join(lang_counts)}")
        
        # Check for common project types
        files = self.index_data.get('files', {})
        project_indicators = []
        
        if any('package.json' in f for f in files.keys()):
            project_indicators.append("Node.js/JavaScript")
        if any('requirements.txt' in f or 'pyproject.toml' in f for f in files.keys()):
            project_indicators.append("Python")
        if any('Cargo.toml' in f for f in files.keys()):
            project_indicators.append("Rust")
        if any('go.mod' in f for f in files.keys()):
            project_indicators.append("Go")
        
        if project_indicators:
            overview.append(f"🏗️ **Project Type:** {', '.join(project_indicators)}")
        
        return "\\n".join(overview) if overview else "Standard project structure detected."
    
    def _get_semantic_context(self) -> str:
        """Get semantic analysis context."""
        semantic_index = self.index_data.get('semantic_index', {})
        if not semantic_index:
            return "No semantic analysis available."
        
        context = []
        
        # Architectural patterns
        arch_patterns = semantic_index.get('architectural_patterns', {})
        if arch_patterns:
            naming = arch_patterns.get('naming_conventions', {})
            if naming:
                context.append(f"📝 **Naming Convention:** {naming.get('functions', 'Mixed styles detected')}")
            
            design_patterns = arch_patterns.get('design_patterns', [])
            if design_patterns:
                context.append(f"🎨 **Design Patterns:** {', '.join(design_patterns)}")
        
        # Complexity analysis
        complexity = semantic_index.get('complexity_analysis', {})
        if complexity:
            total_funcs = complexity.get('total_functions', 0)
            avg_complexity = complexity.get('average_cyclomatic_complexity', 0)
            high_complexity = complexity.get('high_complexity_functions', [])
            
            context.append(f"⚡ **Code Complexity:** {total_funcs} functions, avg complexity: {avg_complexity:.1f}")
            
            if high_complexity:
                context.append(f"⚠️ **High Complexity Functions:** {len(high_complexity)} functions need attention")
        
        # Function patterns
        functions = semantic_index.get('functions', {})
        if functions:
            patterns = {}
            for func_data in functions.values():
                func_patterns = func_data.get('patterns', [])
                for pattern in func_patterns:
                    patterns[pattern] = patterns.get(pattern, 0) + 1
            
            if patterns:
                top_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:5]
                pattern_strs = [f"{pattern} ({count})" for pattern, count in top_patterns]
                context.append(f"🔍 **Common Patterns:** {', '.join(pattern_strs)}")
        
        return "\\n".join(context) if context else "Semantic analysis completed - no specific patterns detected."
    
    def _get_organization_context(self) -> str:
        """Get project organization and directory structure context."""
        context = []
        
        # Directory purposes
        dir_purposes = self.index_data.get('directory_purposes', {})
        if dir_purposes:
            context.append("📁 **Directory Structure:**")
            for directory, purpose in sorted(dir_purposes.items()):
                context.append(f"  • `{directory}/` - {purpose}")
        
        # File organization patterns
        files = self.index_data.get('files', {})
        if files:
            # Analyze file organization
            test_files = [f for f in files.keys() if 'test' in f.lower() or 'spec' in f.lower()]
            config_files = [f for f in files.keys() if 'config' in f.lower() or f.endswith('.json')]
            
            if test_files:
                context.append(f"🧪 **Testing:** {len(test_files)} test files found")
            if config_files:
                context.append(f"⚙️ **Configuration:** {len(config_files)} config files")
        
        return "\\n".join(context) if context else "Standard file organization."
    
    def _get_similarity_context(self) -> str:
        """Get information about code similarity clusters and patterns."""
        semantic_index = self.index_data.get('semantic_index', {})
        similarity_clusters = semantic_index.get('similarity_clusters', [])
        
        if not similarity_clusters:
            return None
        
        context = []
        
        # Show top similarity clusters
        high_similarity_clusters = [
            cluster for cluster in similarity_clusters 
            if len(cluster.get('functions', [])) > 2
        ]
        
        if high_similarity_clusters:
            context.append("🔗 **Similar Code Clusters Found:**")
            for i, cluster in enumerate(high_similarity_clusters[:3]):  # Top 3 clusters
                functions = cluster.get('functions', [])
                pattern = cluster.get('pattern', 'similar_implementation')
                context.append(f"  • Cluster {i+1}: {len(functions)} similar functions ({pattern})")
                
                # Show first few functions in cluster
                if len(functions) > 0:
                    sample_funcs = functions[:3]
                    context.append(f"    Examples: {', '.join(sample_funcs)}")
        
        # Show functions with high complexity
        functions = semantic_index.get('functions', {})
        complex_functions = []
        for func_id, func_data in functions.items():
            complexity = func_data.get('complexity', {})
            if complexity.get('cyclomatic', 0) > 8:  # High complexity threshold
                complex_functions.append((func_id, complexity.get('cyclomatic', 0)))
        
        if complex_functions:
            context.append("\\n⚠️ **High Complexity Functions to Watch:**")
            complex_functions.sort(key=lambda x: x[1], reverse=True)
            for func_id, complexity in complex_functions[:3]:
                context.append(f"  • {func_id} (complexity: {complexity})")
        
        return "\\n".join(context) if context else None
    
    def _get_development_guidelines(self) -> str:
        """Generate development guidelines based on project analysis."""
        guidelines = []
        
        # Based on semantic analysis
        semantic_index = self.index_data.get('semantic_index', {})
        if semantic_index:
            arch_patterns = semantic_index.get('architectural_patterns', {})
            
            # Naming conventions
            naming = arch_patterns.get('naming_conventions', {})
            if naming.get('functions') == 'snake_case':
                guidelines.append("🐍 Use `snake_case` for function names (project standard)")
            elif naming.get('functions') == 'camelCase':
                guidelines.append("🐪 Use `camelCase` for function names (project standard)")
            
            # Directory patterns
            dir_patterns = arch_patterns.get('directory_patterns', {})
            if dir_patterns.get('test_separation'):
                guidelines.append("🧪 Keep tests in separate directories (project pattern)")
            if dir_patterns.get('utility_separation'):
                guidelines.append("🔧 Place utility functions in dedicated utils directories")
        
        # Duplicate detection advice
        similarity_clusters = semantic_index.get('similarity_clusters', [])
        if len(similarity_clusters) > 2:
            guidelines.append("⚠️ **Duplicate Detection Active** - Check for existing implementations before writing new functions")
        
        # Complexity guidelines
        complexity = semantic_index.get('complexity_analysis', {})
        if complexity:
            avg_complexity = complexity.get('average_cyclomatic_complexity', 0)
            if avg_complexity > 5:
                guidelines.append(f"📊 Keep function complexity under {int(avg_complexity + 2)} (current avg: {avg_complexity:.1f})")
        
        # Default guidelines
        guidelines.extend([
            "🔍 **Before implementing:** Search for existing similar functionality",
            "🏗️ **Architecture:** Follow established patterns in the codebase",
            "📝 **Naming:** Use descriptive names that match project conventions"
        ])
        
        return "\\n".join(guidelines)
    
    def format_for_claude(self) -> Dict[str, Any]:
        """Format the context for Claude Code hook output."""
        context = self.generate_context()
        
        return {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context
            }
        }


def main():
    """Main hook entry point."""
    try:
        # Read hook input from stdin
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Get project directory
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR')
    if not project_dir:
        project_dir = os.getcwd()
    
    # Load architectural context
    loader = ArchitectureContextLoader(project_dir)
    output = loader.format_for_claude()
    
    # Output the context for Claude
    print(json.dumps(output))
    sys.exit(0)


if __name__ == '__main__':
    main()