#!/usr/bin/env python3
"""
Interactive cleanup workflow for eliminating duplicate code.
Guides users through prioritized duplicate elimination process.
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Any
import subprocess

try:
    from generate_duplicate_report import DuplicateReportGenerator
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from generate_duplicate_report import DuplicateReportGenerator


class InteractiveCleanup:
    """Interactive duplicate code cleanup workflow."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.report_generator = DuplicateReportGenerator(project_root)
        self.analysis = None
    
    def run_cleanup_workflow(self):
        """Run the complete interactive cleanup workflow."""
        print("🧹 Interactive Duplicate Code Cleanup")
        print("=" * 50)
        
        # Step 1: Generate analysis
        print("\n📊 Analyzing codebase for duplicates...")
        self.analysis = self.report_generator.analyze_duplicates()
        
        if 'error' in self.analysis:
            print(f"❌ Error: {self.analysis['error']}")
            return
        
        # Step 2: Show summary
        self._show_summary()
        
        # Step 3: Interactive cleanup
        self._interactive_menu()
    
    def _show_summary(self):
        """Display analysis summary."""
        summary = self.analysis['summary']
        
        print(f"\n📈 Analysis Summary:")
        print(f"  • Total Functions Analyzed: {self.analysis['total_functions_analyzed']}")
        print(f"  • Exact Duplicate Groups: {summary['total_duplicate_groups']}")
        print(f"  • Functions to Deduplicate: {summary['total_duplicate_functions']}")
        print(f"  • Similarity Clusters: {summary['total_similarity_clusters']}")
        print(f"  • Estimated Lines Saved: {summary['estimated_lines_saved']}")
        print(f"  • High Priority Items: {summary['top_priority_count']}")
    
    def _interactive_menu(self):
        """Main interactive menu."""
        while True:
            print(f"\n🔧 Cleanup Options:")
            print("1. 🚨 View exact duplicates (immediate action)")
            print("2. 📊 View similarity clusters (medium effort)")
            print("3. 📋 View cleanup priorities")
            print("4. 🤖 Launch cleanup sub-agents")
            print("5. 📄 Generate full report")
            print("6. ⚡ Quick wins (auto-fix easy duplicates)")
            print("7. 🔍 Search for specific patterns")
            print("8. 📚 Export cleanup plan")
            print("9. ❌ Exit")
            
            choice = input("\nSelect option (1-9): ").strip()
            
            if choice == '1':
                self._show_exact_duplicates()
            elif choice == '2':
                self._show_similarity_clusters()
            elif choice == '3':
                self._show_cleanup_priorities()
            elif choice == '4':
                self._launch_cleanup_agents()
            elif choice == '5':
                self._generate_full_report()
            elif choice == '6':
                self._quick_wins()
            elif choice == '7':
                self._search_patterns()
            elif choice == '8':
                self._export_cleanup_plan()
            elif choice == '9':
                print("👋 Cleanup workflow complete!")
                break
            else:
                print("❌ Invalid option. Please select 1-9.")
    
    def _show_exact_duplicates(self):
        """Display exact duplicates with action options."""
        exact_duplicates = self.analysis['exact_duplicates']
        
        if not exact_duplicates:
            print("\n✅ No exact duplicates found!")
            return
        
        print(f"\n🚨 Exact Duplicates ({len(exact_duplicates)} groups):")
        print("-" * 50)
        
        for i, dup in enumerate(exact_duplicates[:10]):  # Show top 10
            print(f"\n{i+1}. Duplicate Group (Impact: {dup['impact_score']:.1f})")
            print(f"   Count: {dup['count']} identical functions")
            print("   Functions:")
            for func in dup['functions']:
                print(f"     • {func['function_id']}")
                if 'complexity' in func and func['complexity']:
                    complexity = func['complexity'].get('cyclomatic', 'unknown')
                    print(f"       Complexity: {complexity}")
        
        # Action menu for exact duplicates
        self._exact_duplicate_actions()
    
    def _exact_duplicate_actions(self):
        """Action menu for exact duplicates."""
        print(f"\n🔧 Exact Duplicate Actions:")
        print("1. 🤖 Launch duplicate-eliminator agent")
        print("2. 📝 Create cleanup task list")
        print("3. 🔍 Inspect specific duplicate group")
        print("4. ⬅️ Back to main menu")
        
        choice = input("Select action (1-4): ").strip()
        
        if choice == '1':
            self._launch_duplicate_eliminator()
        elif choice == '2':
            self._create_cleanup_tasks()
        elif choice == '3':
            self._inspect_duplicate_group()
        elif choice == '4':
            return
    
    def _show_similarity_clusters(self):
        """Display similarity clusters."""
        clusters = self.analysis['similarity_clusters']
        
        if not clusters:
            print("\n✅ No similarity clusters found!")
            return
        
        print(f"\n📊 Similarity Clusters ({len(clusters)} clusters):")
        print("-" * 50)
        
        for i, cluster in enumerate(clusters[:10]):
            print(f"\n{i+1}. Similarity Cluster (Impact: {cluster['impact_score']:.1f})")
            print(f"   Count: {cluster['count']} similar functions")
            print(f"   Average Similarity: {cluster['average_similarity']*100:.1f}%")
            print("   Functions:")
            for func in cluster['functions'][:3]:  # Show first 3
                print(f"     • {func['function_id']}")
            if len(cluster['functions']) > 3:
                print(f"     ... and {len(cluster['functions']) - 3} more")
    
    def _show_cleanup_priorities(self):
        """Display cleanup priorities."""
        priorities = self.analysis['cleanup_priorities']
        
        if not priorities:
            print("\n✅ No cleanup priorities identified!")
            return
        
        print(f"\n📋 Cleanup Priorities ({len(priorities)} items):")
        print("-" * 50)
        
        high_priority = [p for p in priorities if p['priority'] == 'HIGH']
        medium_priority = [p for p in priorities if p['priority'] == 'MEDIUM']
        
        if high_priority:
            print("\n🔴 HIGH PRIORITY:")
            for i, item in enumerate(high_priority[:5]):
                print(f"  {i+1}. {item['description']}")
                print(f"     Effort: {item['effort']}, Impact: {item['impact_score']:.1f}")
        
        if medium_priority:
            print("\n🟡 MEDIUM PRIORITY:")
            for i, item in enumerate(medium_priority[:5]):
                print(f"  {i+1}. {item['description']}")
                print(f"     Effort: {item['effort']}, Impact: {item['impact_score']:.1f}")
    
    def _launch_cleanup_agents(self):
        """Launch specialized cleanup sub-agents."""
        print(f"\n🤖 Available Cleanup Agents:")
        print("1. duplicate-eliminator - Remove exact duplicates")
        print("2. utility-extractor - Extract shared utilities")  
        print("3. refactoring-advisor - Architectural guidance")
        print("4. ⬅️ Back to main menu")
        
        choice = input("Select agent (1-4): ").strip()
        
        if choice == '1':
            self._launch_duplicate_eliminator()
        elif choice == '2':
            self._launch_utility_extractor()
        elif choice == '3':
            self._launch_refactoring_advisor()
        elif choice == '4':
            return
    
    def _launch_duplicate_eliminator(self):
        """Launch the duplicate eliminator agent."""
        exact_duplicates = self.analysis['exact_duplicates']
        
        if not exact_duplicates:
            print("❌ No exact duplicates to eliminate!")
            return
        
        print("\n🤖 Launching duplicate-eliminator agent...")
        print("📋 Task: Eliminate exact duplicate functions")
        print(f"📊 Scope: {len(exact_duplicates)} duplicate groups")
        
        # Create task description for the agent
        task_description = self._create_eliminator_task()
        print(f"\n📝 Agent Task:")
        print(task_description)
        
        print("\n💡 To launch the agent in Claude Code:")
        print("Use: Task tool with subagent_type='duplicate-eliminator'")
        print(f"Prompt: {task_description}")
    
    def _launch_utility_extractor(self):
        """Launch the utility extractor agent."""
        clusters = self.analysis['similarity_clusters']
        high_similarity = [c for c in clusters if c['average_similarity'] > 0.8]
        
        if not high_similarity:
            print("❌ No high-similarity clusters to extract utilities from!")
            return
        
        print("\n🤖 Launching utility-extractor agent...")
        print("📋 Task: Extract shared utilities from similar code")
        print(f"📊 Scope: {len(high_similarity)} similarity clusters")
        
        task_description = self._create_extractor_task(high_similarity)
        print(f"\n📝 Agent Task:")
        print(task_description)
        
        print("\n💡 To launch the agent in Claude Code:")
        print("Use: Task tool with subagent_type='utility-extractor'")
        print(f"Prompt: {task_description}")
    
    def _launch_refactoring_advisor(self):
        """Launch the refactoring advisor agent."""
        priorities = self.analysis['cleanup_priorities']
        high_impact = [p for p in priorities if p['impact_score'] > 30]
        
        print("\n🤖 Launching refactoring-advisor agent...")
        print("📋 Task: Provide architectural guidance for complex refactoring")
        print(f"📊 Scope: {len(high_impact)} high-impact items")
        
        task_description = self._create_advisor_task(high_impact)
        print(f"\n📝 Agent Task:")
        print(task_description)
        
        print("\n💡 To launch the agent in Claude Code:")
        print("Use: Task tool with subagent_type='refactoring-advisor'")
        print(f"Prompt: {task_description}")
    
    def _create_eliminator_task(self) -> str:
        """Create task description for duplicate eliminator."""
        exact_duplicates = self.analysis['exact_duplicates']
        top_duplicates = exact_duplicates[:3]  # Focus on top 3
        
        task = "Eliminate the following exact duplicate functions:\n\n"
        for i, dup in enumerate(top_duplicates):
            task += f"{i+1}. Duplicate Group ({dup['count']} functions):\n"
            for func in dup['functions']:
                task += f"   - {func['function_id']}\n"
            task += f"   Impact Score: {dup['impact_score']:.1f}\n\n"
        
        task += "For each group:\n"
        task += "1. Analyze the duplicate functions to confirm they're identical\n"
        task += "2. Choose the best implementation or create a new shared utility\n"
        task += "3. Replace all duplicates with calls to the shared implementation\n"
        task += "4. Update imports and ensure tests pass\n"
        task += "5. Remove the now-unused duplicate functions\n\n"
        task += "Focus on the highest impact groups first."
        
        return task
    
    def _create_extractor_task(self, clusters: List[Dict]) -> str:
        """Create task description for utility extractor."""
        top_clusters = clusters[:3]
        
        task = "Extract shared utilities from the following similarity clusters:\n\n"
        for i, cluster in enumerate(top_clusters):
            task += f"{i+1}. Similarity Cluster ({cluster['count']} functions, {cluster['average_similarity']*100:.1f}% similar):\n"
            for func in cluster['functions']:
                task += f"   - {func['function_id']}\n"
            task += f"   Impact Score: {cluster['impact_score']:.1f}\n\n"
        
        task += "For each cluster:\n"
        task += "1. Analyze the similar functions to identify patterns and variations\n"
        task += "2. Design a configurable utility that handles all variations\n"
        task += "3. Create the new utility with proper configuration options\n"
        task += "4. Replace similar functions with calls to the new utility\n"
        task += "5. Add comprehensive tests for the new utility\n\n"
        task += "Prioritize clusters with the highest similarity and impact scores."
        
        return task
    
    def _create_advisor_task(self, items: List[Dict]) -> str:
        """Create task description for refactoring advisor."""
        task = "Provide architectural guidance for the following high-impact duplicate elimination:\n\n"
        
        task += "High-Impact Items:\n"
        for i, item in enumerate(items[:5]):
            task += f"{i+1}. {item['description']}\n"
            task += f"   Priority: {item['priority']}, Effort: {item['effort']}\n"
            task += f"   Impact Score: {item['impact_score']:.1f}\n\n"
        
        task += "Please provide:\n"
        task += "1. Risk assessment for each item\n"
        task += "2. Recommended refactoring approach and patterns\n"
        task += "3. Implementation sequence and dependencies\n"
        task += "4. Potential architectural improvements\n"
        task += "5. Testing and validation strategies\n\n"
        task += "Focus on maximizing long-term maintainability while minimizing implementation risk."
        
        return task
    
    def _generate_full_report(self):
        """Generate and display full markdown report."""
        report = self.report_generator.generate_report('markdown')
        
        # Save to file
        report_path = self.project_root / 'DUPLICATE_ANALYSIS_REPORT.md'
        with open(report_path, 'w') as f:
            f.write(report)
        
        print(f"\n📄 Full report generated: {report_path}")
        print("🔗 Open this file to see detailed analysis and recommendations")
        
        # Show first few lines
        lines = report.split('\n')
        print("\n📋 Report Preview:")
        print("-" * 30)
        for line in lines[:15]:
            print(line)
        print("...")
    
    def _quick_wins(self):
        """Identify and potentially auto-fix easy duplicates."""
        exact_duplicates = self.analysis['exact_duplicates']
        
        # Find low-effort, high-impact duplicates
        quick_wins = [
            dup for dup in exact_duplicates 
            if dup['impact_score'] > 20 and dup['count'] <= 3
        ]
        
        if not quick_wins:
            print("\n❌ No obvious quick wins identified.")
            print("💡 Consider using the full cleanup workflow for better results.")
            return
        
        print(f"\n⚡ Quick Wins Identified ({len(quick_wins)} groups):")
        print("-" * 40)
        
        for i, win in enumerate(quick_wins):
            print(f"\n{i+1}. {win['count']} duplicate functions (Impact: {win['impact_score']:.1f})")
            for func in win['functions']:
                print(f"   • {func['function_id']}")
        
        print(f"\n💡 These are good candidates for automated elimination.")
        print("🤖 Use the duplicate-eliminator agent to handle these efficiently.")
    
    def _search_patterns(self):
        """Search for specific duplicate patterns."""
        pattern = input("\n🔍 Enter search pattern (function name or keyword): ").strip()
        
        if not pattern:
            return
        
        # Search in exact duplicates
        matching_duplicates = []
        for dup in self.analysis['exact_duplicates']:
            for func in dup['functions']:
                if pattern.lower() in func['function_id'].lower():
                    matching_duplicates.append((dup, func))
        
        # Search in similarity clusters  
        matching_clusters = []
        for cluster in self.analysis['similarity_clusters']:
            for func in cluster['functions']:
                if pattern.lower() in func['function_id'].lower():
                    matching_clusters.append((cluster, func))
        
        print(f"\n🎯 Search Results for '{pattern}':")
        print("-" * 40)
        
        if matching_duplicates:
            print(f"\nExact Duplicates ({len(matching_duplicates)} matches):")
            for dup, func in matching_duplicates:
                print(f"  • {func['function_id']} (group of {dup['count']})")
        
        if matching_clusters:
            print(f"\nSimilarity Clusters ({len(matching_clusters)} matches):")
            for cluster, func in matching_clusters:
                print(f"  • {func['function_id']} ({cluster['average_similarity']*100:.1f}% similar cluster)")
        
        if not matching_duplicates and not matching_clusters:
            print("❌ No matches found.")
    
    def _export_cleanup_plan(self):
        """Export a structured cleanup plan."""
        plan_path = self.project_root / 'CLEANUP_PLAN.md'
        
        plan = self._generate_cleanup_plan()
        
        with open(plan_path, 'w') as f:
            f.write(plan)
        
        print(f"\n📋 Cleanup plan exported: {plan_path}")
        print("🔗 Use this plan to track cleanup progress")
    
    def _generate_cleanup_plan(self) -> str:
        """Generate structured cleanup plan."""
        priorities = self.analysis['cleanup_priorities']
        
        plan = "# Duplicate Code Cleanup Plan\n\n"
        plan += f"Generated: {self.analysis['analysis_timestamp']}\n\n"
        
        plan += "## Phase 1: High Priority Items\n\n"
        high_priority = [p for p in priorities if p['priority'] == 'HIGH']
        for i, item in enumerate(high_priority):
            plan += f"### Task {i+1}: {item['description']}\n"
            plan += f"- **Effort**: {item['effort']}\n"
            plan += f"- **Impact**: {item['impact_score']:.1f}\n"
            plan += f"- **Type**: {item['type']}\n"
            plan += "- **Status**: ⏳ Pending\n\n"
        
        plan += "## Phase 2: Medium Priority Items\n\n"
        medium_priority = [p for p in priorities if p['priority'] == 'MEDIUM']
        for i, item in enumerate(medium_priority):
            plan += f"### Task {i+1}: {item['description']}\n"
            plan += f"- **Effort**: {item['effort']}\n"
            plan += f"- **Impact**: {item['impact_score']:.1f}\n"
            plan += "- **Status**: ⏳ Pending\n\n"
        
        plan += "## Recommended Tools\n\n"
        for tool in self.analysis['recommendations']['tools_needed']:
            plan += f"- {tool}\n"
        
        plan += "\n## Progress Tracking\n\n"
        plan += "Update the status of each task as you complete them:\n"
        plan += "- ⏳ Pending\n"
        plan += "- 🟡 In Progress\n"
        plan += "- ✅ Completed\n"
        plan += "- ❌ Skipped\n"
        
        return plan
    
    def _inspect_duplicate_group(self):
        """Inspect a specific duplicate group in detail."""
        exact_duplicates = self.analysis['exact_duplicates']
        
        if not exact_duplicates:
            print("❌ No exact duplicates to inspect!")
            return
        
        print(f"\nAvailable duplicate groups:")
        for i, dup in enumerate(exact_duplicates[:10]):
            print(f"{i+1}. {dup['count']} functions (Impact: {dup['impact_score']:.1f})")
        
        try:
            choice = int(input(f"\nSelect group to inspect (1-{min(10, len(exact_duplicates))}): "))
            if 1 <= choice <= len(exact_duplicates):
                group = exact_duplicates[choice - 1]
                self._show_duplicate_group_details(group)
            else:
                print("❌ Invalid selection.")
        except ValueError:
            print("❌ Please enter a valid number.")
    
    def _show_duplicate_group_details(self, group: Dict[str, Any]):
        """Show detailed information about a duplicate group."""
        print(f"\n🔍 Duplicate Group Details")
        print("=" * 30)
        print(f"Type: {group['type']}")
        print(f"Count: {group['count']} functions")
        print(f"Impact Score: {group['impact_score']:.1f}")
        print(f"AST Fingerprint: {group['fingerprint'][:16]}...")
        
        print(f"\n📋 Functions in this group:")
        for func in group['functions']:
            print(f"\n  📄 {func['function_id']}")
            print(f"     File: {func['file_path']}")
            print(f"     Signature: {func['signature']}")
            if 'complexity' in func and func['complexity']:
                complexity = func['complexity'].get('cyclomatic', 'unknown')
                print(f"     Complexity: {complexity}")
        
        print(f"\n💡 Recommended Action:")
        print("1. Review all functions to confirm they're truly identical")
        print("2. Choose the best implementation or create a new utility")
        print("3. Extract to shared location (e.g., utils/ directory)")  
        print("4. Replace all occurrences with calls to shared implementation")
        print("5. Remove duplicate functions and update tests")
    
    def _create_cleanup_tasks(self):
        """Create cleanup tasks in todo format."""
        exact_duplicates = self.analysis['exact_duplicates']
        
        if not exact_duplicates:
            print("❌ No exact duplicates to create tasks for!")
            return
        
        print(f"\n📝 Creating cleanup tasks for {len(exact_duplicates)} duplicate groups...")
        
        tasks = []
        for i, dup in enumerate(exact_duplicates):
            task = f"Eliminate duplicate group {i+1}: {dup['count']} identical functions (Impact: {dup['impact_score']:.1f})"
            tasks.append(task)
        
        # Save tasks to file
        tasks_path = self.project_root / 'CLEANUP_TASKS.md'
        with open(tasks_path, 'w') as f:
            f.write("# Duplicate Cleanup Tasks\n\n")
            for i, task in enumerate(tasks):
                f.write(f"- [ ] {task}\n")
        
        print(f"✅ Tasks saved to: {tasks_path}")
        print("🔗 Track your progress by checking off completed tasks")


def main():
    """Main entry point for interactive cleanup."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Interactive duplicate code cleanup')
    parser.add_argument('--project-root', default='.', help='Project root directory')
    
    args = parser.parse_args()
    
    # Run interactive cleanup
    cleanup = InteractiveCleanup(args.project_root)
    cleanup.run_cleanup_workflow()


if __name__ == '__main__':
    main()