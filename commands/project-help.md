---
description: Quick reference for project indexing commands
---

## 📚 Project Indexing Quick Reference

### Available Commands:

- `/semantic-index [full|incremental]` - Build/update PROJECT_INDEX.json with semantic analysis
- `/duplicates [report|interactive|status]` - Manage duplicate code detection  
- `/analyze` - Run comprehensive semantic analysis
- `/index [size-kb|full|quick|status]` - Generate or refresh basic index
- `/setup-indexing` - Set up automatic indexing for your project

### Common Workflows:

**🚀 First time setup:**
```
/setup-indexing
```

**🔄 Daily use:**
```
/semantic-index incremental    # Smart updates
/duplicates status            # Check for issues  
```

**🔍 Deep analysis:**
```  
/semantic-index full          # Complete rebuild
/duplicates interactive       # Clean up duplicates
/analyze                      # Architecture review
```

### What Each Tool Provides:

- **semantic-index**: TF-IDF embeddings, AST fingerprints, complexity metrics
- **duplicates**: Real-time detection, cleanup workflows, reporting
- **analyze**: Architecture patterns, vocabulary analysis, similarity clusters

### Files Created:

- `PROJECT_INDEX.json` - Main index with semantic data
- `.claude/settings.json` - Automatic hook configuration  
- `scripts/` - All indexing and analysis tools

💡 **Tip**: The system automatically maintains your index as you code!