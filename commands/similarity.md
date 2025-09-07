---
name: similarity
description: Find similar code using cached embeddings from PROJECT_INDEX.json
args:
  - name: mode
    description: Operation mode (query, duplicates, build-cache)
    required: false
    default: query
  - name: algorithm
    description: Similarity algorithm (cosine, euclidean, manhattan, dot-product, jaccard, weighted-cosine)
    required: false
    default: cosine
  - name: output
    description: Output file path for results
    required: false
  - name: query
    description: Code snippet or function to find similar matches for
    required: false
---

# Similarity Analysis

Analyze code similarity using cached neural embeddings from PROJECT_INDEX.json.

## Usage

```bash
/index:similarity                         # Interactive query mode
/index:similarity:query                   # Explicit query mode
/index:similarity:duplicates              # Find duplicate code
/index:similarity:build-cache             # Build similarity cache
/index:similarity:query:cosine:results.json  # Query with cosine + custom output
```

## Modes

- **query** (default) - Interactive mode to search for similar code
- **duplicates** - Automatically find potential duplicate functions
- **build-cache** - Pre-compute similarity matrix for faster searches

## Algorithms

- **cosine** (default) - Best for semantic code similarity
- **euclidean** - Geometric distance, good for exact matches
- **manhattan** - Robust to noise, good for structural similarity
- **dot-product** - Fast computation, unnormalized similarity
- **jaccard** - Set-based similarity for sparse representations
- **weighted-cosine** - TF-IDF weighted similarity for keyword importance

Results include similarity scores, function signatures, and code context.