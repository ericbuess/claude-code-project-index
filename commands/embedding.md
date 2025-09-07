---
name: embedding
description: Generate PROJECT_INDEX.json with neural embeddings and similarity analysis
args:
  - name: algorithm
    description: Similarity algorithm (cosine, euclidean, manhattan, dot-product, jaccard, weighted-cosine)
    required: false
    default: cosine
  - name: output
    description: Output file path for similarity results
    required: false
  - name: size
    description: Target index size in KB
    required: false
    default: 50
---

# Index with Embeddings and Similarity

Generate PROJECT_INDEX.json with neural embeddings using Ollama and perform similarity analysis.

## Usage

```bash
/index:embedding                          # Basic embedding generation
/index:embedding:cosine                   # With cosine similarity algorithm
/index:embedding:euclidean:custom.json    # Euclidean algorithm + custom output
/index:embedding:cosine::100              # Cosine algorithm + 100KB size
```

## Implementation

The command generates embeddings using the nomic-embed-text model via Ollama and includes similarity analysis capabilities.

Available algorithms:
- **cosine** (default) - Cosine similarity, best for semantic similarity
- **euclidean** - Euclidean distance, geometric similarity  
- **manhattan** - Manhattan distance, robust to outliers
- **dot-product** - Dot product similarity, fast computation
- **jaccard** - Jaccard similarity for sparse vectors
- **weighted-cosine** - Weighted cosine with TF-IDF

The embedding data is cached in PROJECT_INDEX.json for performance.