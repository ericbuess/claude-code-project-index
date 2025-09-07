#!/usr/bin/env python3
"""
Generate comprehensive duplicate code analysis report for existing codebases.
Identifies and prioritizes duplicate code for cleanup efforts.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict

# Import utilities
try:
    from index_utils import (
        find_similar_functions,
        create_ast_fingerprint,
        compute_code_similarity,
        extract_python_signatures,
        extract_javascript_signatures,
        extract_shell_signatures,
        PARSEABLE_LANGUAGES
    )
    from semantic_analyzer import SemanticAnalyzer
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from index_utils import (
        find_similar_functions,
        create_ast_fingerprint,
        compute_code_similarity,
        extract_python_signatures,
        extract_javascript_signatures,
        extract_shell_signatures,
        PARSEABLE_LANGUAGES
    )
    from semantic_analyzer import SemanticAnalyzer


class DuplicateReportGenerator:
    """Generate comprehensive reports on duplicate code in existing projects."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.index_path = self.project_root / 'PROJECT_INDEX.json'
        self.index_data = None
        self.load_index()
    
    def load_index(self):
        """Load the project index with semantic data."""
        if not self.index_path.exists():
            print("❌ PROJECT_INDEX.json not found. Run semantic analysis first.")
            sys.exit(1)
        
        with open(self.index_path, 'r') as f:
            self.index_data = json.load(f)
        
        if 'semantic_index' not in self.index_data:
            print("❌ Semantic index not found. Run semantic_analyzer.py first.")
            sys.exit(1)
    
    def analyze_duplicates(self) -> Dict[str, Any]:
        """Perform comprehensive duplicate analysis."""
        semantic_index = self.index_data['semantic_index']
        functions = semantic_index.get('functions', {})
        
        if not functions:
            return {"error": "No functions found in semantic index"}
        
        # Analyze different types of duplicates
        exact_duplicates = self._find_exact_duplicates(functions)
        similarity_clusters = self._find_similarity_clusters(functions)
        naming_similarities = self._find_naming_similarities(functions)
        
        # Calculate cleanup priorities
        cleanup_priorities = self._calculate_cleanup_priorities(
            exact_duplicates, similarity_clusters, functions
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            exact_duplicates, similarity_clusters, cleanup_priorities
        )
        
        return {
            "analysis_timestamp": self.index_data.get('indexed_at', ''),
            "total_functions_analyzed": len(functions),
            "exact_duplicates": exact_duplicates,
            "similarity_clusters": similarity_clusters,
            "naming_similarities": naming_similarities,
            "cleanup_priorities": cleanup_priorities,
            "recommendations": recommendations,
            "summary": self._generate_summary(exact_duplicates, similarity_clusters)
        }
    
    def _find_exact_duplicates(self, functions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find functions with identical AST fingerprints."""
        fingerprint_groups = defaultdict(list)
        
        for func_id, func_data in functions.items():
            fingerprint = func_data.get('ast_fingerprint')
            if fingerprint:
                fingerprint_groups[fingerprint].append({
                    'function_id': func_id,
                    'signature': func_data.get('signature', ''),
                    'complexity': func_data.get('complexity', {}),
                    'file_path': func_id.split(':')[0] if ':' in func_id else 'unknown'
                })
        
        # Only return groups with multiple functions (duplicates)
        exact_duplicates = []
        for fingerprint, group in fingerprint_groups.items():
            if len(group) > 1:
                exact_duplicates.append({
                    'type': 'exact_structural_duplicate',
                    'fingerprint': fingerprint,
                    'count': len(group),
                    'functions': group,
                    'impact_score': self._calculate_impact_score(group)
                })
        
        # Sort by impact score (highest first)
        exact_duplicates.sort(key=lambda x: x['impact_score'], reverse=True)
        return exact_duplicates
    
    def _find_similarity_clusters(self, functions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find clusters of similar functions using TF-IDF similarity."""
        clusters = []
        processed_functions = set()
        
        for func_id, func_data in functions.items():
            if func_id in processed_functions:
                continue
            
            # Find similar functions for this one
            tfidf_vector = func_data.get('tfidf_vector', [])
            if not tfidf_vector:
                continue
            
            similar_cluster = [func_id]
            processed_functions.add(func_id)
            
            # Compare with all other functions
            for other_func_id, other_func_data in functions.items():
                if other_func_id in processed_functions:
                    continue
                
                other_vector = other_func_data.get('tfidf_vector', [])
                if not other_vector:
                    continue
                
                similarity = compute_code_similarity(tfidf_vector, other_vector)
                if similarity >= 0.7:  # 70% similarity threshold for clusters
                    similar_cluster.append(other_func_id)
                    processed_functions.add(other_func_id)
            
            # Only create cluster if we found similar functions
            if len(similar_cluster) > 1:
                cluster_functions = []
                for cluster_func_id in similar_cluster:
                    cluster_func_data = functions[cluster_func_id]
                    cluster_functions.append({
                        'function_id': cluster_func_id,
                        'signature': cluster_func_data.get('signature', ''),
                        'complexity': cluster_func_data.get('complexity', {}),
                        'file_path': cluster_func_id.split(':')[0] if ':' in cluster_func_id else 'unknown'
                    })
                
                clusters.append({
                    'type': 'similarity_cluster',
                    'count': len(similar_cluster),
                    'functions': cluster_functions,
                    'average_similarity': self._calculate_average_similarity(similar_cluster, functions),
                    'impact_score': self._calculate_impact_score(cluster_functions)
                })
        
        # Sort by impact score
        clusters.sort(key=lambda x: x['impact_score'], reverse=True)
        return clusters
    
    def _find_naming_similarities(self, functions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find functions with very similar names."""
        naming_groups = []
        function_names = [(func_id, func_id.split(':')[-1]) for func_id in functions.keys()]
        
        processed = set()
        for i, (func_id1, name1) in enumerate(function_names):
            if func_id1 in processed:
                continue
            
            similar_names = [func_id1]
            for j, (func_id2, name2) in enumerate(function_names):
                if i != j and func_id2 not in processed:
                    similarity = self._string_similarity(name1.lower(), name2.lower())
                    if 0.8 <= similarity < 1.0:  # Very similar but not identical
                        similar_names.append(func_id2)
            
            if len(similar_names) > 1:
                for func_id in similar_names:
                    processed.add(func_id)
                
                naming_groups.append({
                    'type': 'similar_naming',
                    'count': len(similar_names),
                    'functions': [{'function_id': fid, 'name': fid.split(':')[-1]} for fid in similar_names]
                })
        
        return naming_groups
    
    def _calculate_impact_score(self, function_group: List[Dict[str, Any]]) -> float:
        """Calculate impact score for a group of duplicate functions."""
        # Factors: number of duplicates, complexity, file spread
        count_score = len(function_group) * 10  # More duplicates = higher impact
        
        # Complexity score (higher complexity = higher impact)
        complexity_scores = []
        for func in function_group:
            complexity = func.get('complexity', {})
            cyclomatic = complexity.get('cyclomatic', 1)
            complexity_scores.append(cyclomatic)
        
        avg_complexity = sum(complexity_scores) / len(complexity_scores) if complexity_scores else 1
        complexity_score = avg_complexity * 5
        
        # File spread score (duplicates across files = higher impact)
        unique_files = len(set(func.get('file_path', '') for func in function_group))
        spread_score = unique_files * 3
        
        return count_score + complexity_score + spread_score
    
    def _calculate_average_similarity(self, func_ids: List[str], functions: Dict[str, Any]) -> float:
        """Calculate average similarity within a cluster."""
        similarities = []
        vectors = []
        
        for func_id in func_ids:
            vector = functions[func_id].get('tfidf_vector', [])
            if vector:
                vectors.append(vector)
        
        if len(vectors) < 2:
            return 0.0
        
        # Calculate pairwise similarities
        for i in range(len(vectors)):
            for j in range(i + 1, len(vectors)):
                similarity = compute_code_similarity(vectors[i], vectors[j])
                similarities.append(similarity)
        
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity using character bigrams."""
        if not s1 or not s2:
            return 0.0
        
        bigrams1 = set(s1[i:i+2] for i in range(len(s1)-1))
        bigrams2 = set(s2[i:i+2] for i in range(len(s2)-1))
        
        if not bigrams1 and not bigrams2:
            return 1.0
        if not bigrams1 or not bigrams2:
            return 0.0
        
        intersection = len(bigrams1.intersection(bigrams2))
        union = len(bigrams1.union(bigrams2))
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_cleanup_priorities(self, exact_duplicates: List[Dict], 
                                    similarity_clusters: List[Dict], 
                                    functions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Calculate cleanup priorities based on impact and effort."""
        priorities = []
        
        # Add exact duplicates (easy wins)
        for duplicate in exact_duplicates:
            priorities.append({
                'type': 'exact_duplicate',
                'priority': 'HIGH',
                'effort': 'LOW',
                'impact_score': duplicate['impact_score'],
                'count': duplicate['count'],
                'description': f"Extract {duplicate['count']} identical functions into shared utility",
                'functions': duplicate['functions']
            })
        
        # Add similarity clusters (medium effort)
        for cluster in similarity_clusters:
            if cluster['average_similarity'] > 0.85:  # High similarity
                effort = 'MEDIUM'
                priority = 'HIGH'
            elif cluster['average_similarity'] > 0.75:
                effort = 'MEDIUM'
                priority = 'MEDIUM'
            else:
                effort = 'HIGH'
                priority = 'LOW'
            
            priorities.append({
                'type': 'similarity_cluster',
                'priority': priority,
                'effort': effort,
                'impact_score': cluster['impact_score'],
                'count': cluster['count'],
                'average_similarity': cluster['average_similarity'],
                'description': f"Refactor {cluster['count']} similar functions ({cluster['average_similarity']*100:.0f}% similar)",
                'functions': cluster['functions']
            })
        
        # Sort by priority (HIGH > MEDIUM > LOW) then by impact score
        priority_order = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        priorities.sort(key=lambda x: (priority_order[x['priority']], x['impact_score']), reverse=True)
        
        return priorities
    
    def _generate_recommendations(self, exact_duplicates: List[Dict], 
                                similarity_clusters: List[Dict], 
                                priorities: List[Dict]) -> Dict[str, List[str]]:
        """Generate specific recommendations for cleanup."""
        recommendations = {
            'immediate_actions': [],
            'medium_term': [],
            'long_term': [],
            'tools_needed': []
        }
        
        # Immediate actions (exact duplicates with high impact)
        high_impact_exact = [p for p in priorities if p['type'] == 'exact_duplicate' and p['impact_score'] > 30]
        if high_impact_exact:
            recommendations['immediate_actions'].extend([
                f"Extract {len(high_impact_exact)} high-impact duplicate function groups into shared utilities",
                "Focus on duplicates that span multiple files first",
                "Create utility modules for the most frequently duplicated patterns"
            ])
        
        # Medium term (similarity clusters)
        high_similarity = [p for p in priorities if p['type'] == 'similarity_cluster' and p['average_similarity'] > 0.8]
        if high_similarity:
            recommendations['medium_term'].extend([
                f"Refactor {len(high_similarity)} high-similarity function clusters",
                "Design configurable implementations for similar functions",
                "Consider design patterns (Strategy, Template Method) for similar logic"
            ])
        
        # Long term (lower similarity, architectural changes)
        recommendations['long_term'].extend([
            "Review overall architecture for duplication patterns",
            "Establish coding standards to prevent future duplicates",
            "Consider domain-driven design for complex business logic"
        ])
        
        # Tools needed
        recommendations['tools_needed'].extend([
            "duplicate-eliminator sub-agent for automated extraction",
            "utility-extractor for creating shared modules",
            "refactoring-advisor for complex similarity clusters"
        ])
        
        return recommendations
    
    def _generate_summary(self, exact_duplicates: List[Dict], similarity_clusters: List[Dict]) -> Dict[str, Any]:
        """Generate executive summary of duplicate analysis."""
        total_exact_functions = sum(d['count'] for d in exact_duplicates)
        total_similar_functions = sum(c['count'] for c in similarity_clusters)
        
        # Calculate potential savings
        estimated_lines_saved = total_exact_functions * 15  # Assume 15 lines per function average
        
        return {
            'total_duplicate_groups': len(exact_duplicates),
            'total_duplicate_functions': total_exact_functions,
            'total_similarity_clusters': len(similarity_clusters),
            'total_similar_functions': total_similar_functions,
            'estimated_lines_saved': estimated_lines_saved,
            'estimated_maintenance_reduction': f"{((total_exact_functions + total_similar_functions) / 2):.0f} functions",
            'top_priority_count': len([d for d in exact_duplicates if d['impact_score'] > 30]),
            'complexity_note': 'Focus on high-complexity duplicates for maximum impact'
        }
    
    def generate_report(self, output_format: str = 'json') -> str:
        """Generate the complete duplicate analysis report."""
        analysis = self.analyze_duplicates()
        
        if output_format == 'json':
            return json.dumps(analysis, indent=2)
        elif output_format == 'markdown':
            return self._format_markdown_report(analysis)
        else:
            return str(analysis)
    
    def _format_markdown_report(self, analysis: Dict[str, Any]) -> str:
        """Format analysis as readable markdown report."""
        report = ["# Duplicate Code Analysis Report\n"]
        
        # Summary
        summary = analysis['summary']
        report.append("## Executive Summary\n")
        report.append(f"- **Total Duplicate Groups:** {summary['total_duplicate_groups']}")
        report.append(f"- **Functions to Deduplicate:** {summary['total_duplicate_functions']}")
        report.append(f"- **Similarity Clusters:** {summary['total_similarity_clusters']}")
        report.append(f"- **Estimated Lines Saved:** {summary['estimated_lines_saved']}")
        report.append(f"- **High Priority Items:** {summary['top_priority_count']}\n")
        
        # Exact Duplicates
        if analysis['exact_duplicates']:
            report.append("## 🚨 Exact Duplicates (Immediate Action Required)\n")
            for i, dup in enumerate(analysis['exact_duplicates'][:5]):  # Top 5
                report.append(f"### Duplicate Group {i+1}")
                report.append(f"- **Count:** {dup['count']} identical functions")
                report.append(f"- **Impact Score:** {dup['impact_score']:.1f}")
                report.append("- **Functions:**")
                for func in dup['functions']:
                    report.append(f"  - `{func['function_id']}`")
                report.append("")
        
        # Cleanup Priorities
        if analysis['cleanup_priorities']:
            report.append("## 📋 Cleanup Priorities\n")
            high_priority = [p for p in analysis['cleanup_priorities'] if p['priority'] == 'HIGH'][:5]
            for i, priority in enumerate(high_priority):
                report.append(f"### Priority {i+1}: {priority['description']}")
                report.append(f"- **Effort:** {priority['effort']}")
                report.append(f"- **Impact:** {priority['impact_score']:.1f}")
                report.append("")
        
        # Recommendations
        recommendations = analysis['recommendations']
        report.append("## 💡 Recommendations\n")
        report.append("### Immediate Actions")
        for action in recommendations['immediate_actions']:
            report.append(f"- {action}")
        
        report.append("\n### Medium Term")
        for action in recommendations['medium_term']:
            report.append(f"- {action}")
        
        report.append("\n### Tools Needed")
        for tool in recommendations['tools_needed']:
            report.append(f"- {tool}")
        
        return "\n".join(report)


def main():
    """Main entry point for duplicate report generation."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate duplicate code analysis report')
    parser.add_argument('--project-root', default='.', help='Project root directory')
    parser.add_argument('--format', choices=['json', 'markdown'], default='markdown', 
                       help='Output format')
    parser.add_argument('--output', help='Output file (default: stdout)')
    
    args = parser.parse_args()
    
    # Generate report
    generator = DuplicateReportGenerator(args.project_root)
    report = generator.generate_report(args.format)
    
    # Output report
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"Report saved to {args.output}")
    else:
        print(report)


if __name__ == '__main__':
    main()