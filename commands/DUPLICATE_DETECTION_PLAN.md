# Duplicate Detection & Architecture Enforcement System
## Implementation Plan for Claude Code Project Index

### Overview
This document outlines a comprehensive system for detecting duplicate code and enforcing architectural patterns in real-time as Claude Code writes code. The system uses local embeddings (TF-IDF) and AST analysis to provide immediate feedback without external dependencies.

## Problem Statement
- Agents gradually create "labyrinthine" codebases with duplicate logic
- Similar functionality gets reimplemented in different places
- Architectural patterns drift over time
- No real-time feedback when code duplication occurs

## Solution Architecture

### Core Components

#### 1. Semantic Analysis Layer
- **TF-IDF Vectorization**: Create embeddings from code tokens
- **AST Fingerprinting**: Extract structural patterns
- **Pattern Extraction**: Identify architectural conventions
- **No external dependencies**: Uses sklearn, ast, difflib

#### 2. Real-time Detection
- **PostToolUse Hooks**: Intercept code modifications
- **Similarity Scoring**: Compare against existing code
- **Blocking Feedback**: Alert Claude to duplicates
- **Suggestions**: Propose existing implementations

#### 3. Architectural Enforcement
- **Pattern Recognition**: Learn from existing code
- **Consistency Checking**: Detect violations
- **Naming Conventions**: Enforce project standards
- **Design Patterns**: Identify and suggest patterns

## Implementation Phases

### Phase 1: Core System (Immediate Implementation)

#### 1.1 Enhanced Index Structure
```json
{
  "semantic_index": {
    "functions": {
      "file_path:function_name": {
        "signature": "def func(param: Type) -> ReturnType",
        "ast_fingerprint": "hash_of_structure",
        "tfidf_vector": [0.1, 0.2, ...],
        "complexity": 5,
        "patterns": ["validation", "repository"],
        "dependencies": ["module1", "module2"]
      }
    },
    "similarity_clusters": [
      {
        "pattern": "validation",
        "functions": ["func1", "func2"],
        "similarity_matrix": [[1.0, 0.85], [0.85, 1.0]]
      }
    ],
    "architectural_patterns": {
      "naming_conventions": {
        "functions": "snake_case",
        "classes": "PascalCase",
        "validators": "validate_*"
      },
      "file_organization": {
        "services": "src/services/*",
        "utils": "src/utils/*"
      }
    }
  }
}
```

#### 1.2 Semantic Analyzer (`scripts/semantic_analyzer.py`)
```python
import ast
import hashlib
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

class SemanticAnalyzer:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            token_pattern=r'\b\w+\b',
            max_features=100,
            ngram_range=(1, 2)
        )
        
    def create_ast_fingerprint(self, code):
        """Create structural fingerprint from AST"""
        tree = ast.parse(code)
        # Extract control flow patterns
        structure = self.extract_structure(tree)
        return hashlib.md5(str(structure).encode()).hexdigest()
    
    def create_tfidf_embedding(self, code_corpus):
        """Generate TF-IDF vectors for code similarity"""
        vectors = self.vectorizer.fit_transform(code_corpus)
        return vectors.toarray()
    
    def compute_similarity(self, vec1, vec2):
        """Cosine similarity between vectors"""
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
```

#### 1.3 Duplicate Detector Hook (`scripts/duplicate_detector.py`)
```python
#!/usr/bin/env python3
import json
import sys
import os

def check_similarity(new_code, index_path):
    """Check if new code is similar to existing code"""
    # Load semantic index
    with open(index_path) as f:
        index = json.load(f)
    
    # Analyze new code
    analyzer = SemanticAnalyzer()
    new_fingerprint = analyzer.create_ast_fingerprint(new_code)
    
    # Check for duplicates
    duplicates = []
    for func_id, func_data in index['semantic_index']['functions'].items():
        if func_data['ast_fingerprint'] == new_fingerprint:
            duplicates.append({
                'function': func_id,
                'similarity': 1.0,
                'type': 'exact_structural_match'
            })
        # Check TF-IDF similarity
        similarity = analyzer.compute_similarity(
            new_vector, func_data['tfidf_vector']
        )
        if similarity > 0.8:
            duplicates.append({
                'function': func_id,
                'similarity': similarity,
                'type': 'semantic_similarity'
            })
    
    return duplicates

# Hook implementation
input_data = json.load(sys.stdin)
tool_name = input_data.get('tool_name')

if tool_name in ['Edit', 'Write', 'MultiEdit']:
    file_content = input_data['tool_input'].get('content', '')
    duplicates = check_similarity(file_content, 'PROJECT_INDEX.json')
    
    if duplicates:
        output = {
            "decision": "block",
            "reason": f"⚠️ Duplicate code detected:\\n" + 
                     f"• Similar to {duplicates[0]['function']} " +
                     f"({duplicates[0]['similarity']*100:.0f}% match)\\n" +
                     "Consider using existing implementation or extracting shared logic."
        }
        print(json.dumps(output))
        sys.exit(0)
```

#### 1.4 Architecture Context Loader (`scripts/load_architecture_context.py`)
```python
#!/usr/bin/env python3
import json
import sys

def load_architecture_context():
    """Load architectural patterns and conventions"""
    with open('PROJECT_INDEX.json') as f:
        index = json.load(f)
    
    patterns = index.get('semantic_index', {}).get('architectural_patterns', {})
    duplicates = index.get('semantic_index', {}).get('similarity_clusters', [])
    
    context = []
    
    if patterns:
        context.append("## Project Architecture Patterns")
        context.append(f"- Naming: {patterns.get('naming_conventions', {})}")
        context.append(f"- Organization: {patterns.get('file_organization', {})}")
    
    if duplicates:
        context.append("\\n## Known Code Clusters")
        for cluster in duplicates[:5]:  # Top 5 clusters
            context.append(f"- {cluster['pattern']}: {len(cluster['functions'])} similar functions")
    
    return "\\n".join(context)

# SessionStart hook
output = {
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": load_architecture_context()
    }
}
print(json.dumps(output))
```

### Phase 2: Sub-agent Definitions

#### 2.1 Duplicate Detector Agent (`.claude/agents/duplicate-detector.md`)
```markdown
---
name: duplicate-detector
description: Proactively analyzes code for duplicates and suggests consolidation. Use when refactoring or after implementing new features.
tools: Read, Grep, Glob, Task
---

You are a code duplication specialist focused on identifying and eliminating redundant code.

When invoked:
1. Analyze the recent changes or specified code area
2. Search for similar patterns across the codebase
3. Identify exact duplicates, near-duplicates, and semantic similarities
4. Suggest refactoring opportunities

Analysis approach:
- Compare function signatures and parameter patterns
- Identify similar control flow structures
- Find repeated code blocks across files
- Detect copy-paste with minor modifications

For each duplicate found, provide:
- Similarity percentage and type (exact/structural/semantic)
- Location of existing implementations
- Suggested consolidation approach
- Example of refactored code

Focus on reducing code duplication while maintaining clarity and appropriate abstraction levels.
```

#### 2.2 Architecture Enforcer Agent (`.claude/agents/architecture-enforcer.md`)
```markdown
---
name: architecture-enforcer
description: Ensures code follows established architectural patterns and conventions. Use proactively when adding new features or modules.
tools: Read, Grep, Glob, Edit
---

You are an architectural consistency guardian ensuring code follows established patterns.

When invoked:
1. Identify the architectural patterns in the existing codebase
2. Check if new code follows these patterns
3. Detect violations of conventions
4. Suggest pattern-compliant alternatives

Key responsibilities:
- Enforce naming conventions (functions, classes, files)
- Verify proper layer separation (service/repository/controller)
- Check dependency directions
- Ensure consistent error handling
- Validate proper use of design patterns

For violations found:
- Explain the established pattern
- Show examples from the codebase
- Provide corrected version
- Explain why consistency matters

Maintain balance between consistency and pragmatic flexibility.
```

### Phase 3: Configuration

#### 3.1 Hook Configuration (`.claude/settings.json`)
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/scripts/duplicate_detector.py",
            "timeout": 5000
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/scripts/load_architecture_context.py"
          }
        ]
      }
    ]
  }
}
```

## Future Enhancements (Phase 2)

### Advanced Embeddings
```python
# Layer additional embedding models
class EnhancedAnalyzer(SemanticAnalyzer):
    def __init__(self):
        super().__init__()
        # Add sentence-transformers if available
        try:
            from sentence_transformers import SentenceTransformer
            self.semantic_model = SentenceTransformer('microsoft/codebert-base')
            self.use_semantic = True
        except ImportError:
            self.use_semantic = False
    
    def create_semantic_embedding(self, code):
        if self.use_semantic:
            return self.semantic_model.encode(code)
        return self.create_tfidf_embedding([code])[0]
```

### MCP Integration
```bash
# Add embedding service via MCP
claude mcp add --transport http code-embeddings https://api.embeddings.service/mcp

# The service would provide:
# - Advanced code embeddings
# - Cross-project pattern learning
# - Team-wide duplicate detection
```

### Metrics Dashboard
- Track duplicate detection rate
- Measure code consolidation over time
- Identify refactoring opportunities
- Quantify technical debt reduction

## Testing Strategy

### Test Cases
1. **Exact Duplicate**: Copy-paste the same function
2. **Variable Rename**: Same logic, different variable names
3. **Structural Similar**: Same control flow, different operations
4. **Semantic Similar**: Different implementation, same purpose
5. **False Positive**: Legitimately similar but separate concerns

### Expected Outcomes
- Immediate detection of copy-paste code
- Suggestions for existing utilities
- Pattern consistency enforcement
- Reduced code duplication over time

## Success Metrics
- **Detection Rate**: >90% of duplicates caught
- **False Positive Rate**: <10% incorrect warnings
- **Performance**: <500ms analysis time
- **Code Reduction**: 15-30% less duplicate code

## Rollout Plan
1. Install enhanced indexer
2. Build initial semantic index
3. Configure hooks
4. Create sub-agents
5. Test with sample project
6. Monitor and tune thresholds
7. Add advanced features based on usage

## Troubleshooting

### Common Issues
- **High false positives**: Tune similarity threshold (default 0.8)
- **Missed duplicates**: Check TF-IDF parameters, add more features
- **Performance issues**: Limit vector size, use caching
- **Integration problems**: Verify hook configuration, check permissions

### Debug Commands
```bash
# Test duplicate detection
echo '{"tool_name":"Write","tool_input":{"content":"def validate_email(email): ..."}}' | python scripts/duplicate_detector.py

# Check semantic index
python -c "import json; print(json.load(open('PROJECT_INDEX.json'))['semantic_index'])"

# Verify hooks
claude code --debug  # Shows hook execution
```

## Conclusion
This system provides immediate, actionable feedback on code duplication while laying the foundation for more sophisticated analysis. The phased approach ensures quick wins while maintaining extensibility for future enhancements.