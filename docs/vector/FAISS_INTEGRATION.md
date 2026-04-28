--
— File: docs/vector/FAISS_INTEGRATION.md
— Purpose: Documentation for faiss-cpu integration with player embeddings
— Author: Agent KiloSwift
— Date: 2026-04-27
—

# FAISS Integration Guide

## Overview

**FAISS** (Facebook AI Similarity Search) is a library for efficient similarity
search and clustering of dense vectors. This project integrates FAISS for:

- Player similarity search based on performance features
- Fast nearest-neighbor lookup in real-time prediction
- Clustering players by performance profiles
- Pitch sequence similarity analysis

## Installation

### Option 1: CPU-only (Recommended for development)

```bash
uv add faiss-cpu
```

### Option 2: GPU-accelerated (requires CUDA)

```bash
uv add faiss-gpu
```

## Architecture

The vector search pipeline consists of:

1. **Feature extraction**: Load player statistics from warehouse
2. **Embedding generation**: Create normalized feature vectors
3. **Dimensionality reduction**: PCA to target dimension (default: 128)
4. **Index building**: Build FAISS index (IndexFlatIP for cosine similarity)
5. **Persistence**: Save index + metadata to disk OR store in pgvector

## Usage

### Quick Start: Build Player Embeddings

```bash
# Build from command line
uv run python scripts/vector/build_player_embeddings.py \
    --season 2024 \
    --feature-set full \
    --output faiss \
    --dim 128

# Output:
# - player_embeddings_2024.index (FAISS index file)
# - player_embeddings_2024_metadata.csv (player metadata)
```

### In Python code:

```python
from scripts.vector.build_player_embeddings import load_batter_features, create_embedding_vector
import faiss
import numpy as np

# Load features from warehouse
batters_df = load_batter_features(season=2024, min_pa=50)

# Create embeddings
feature_cols = ['z_obp', 'z_slg', 'z_woba', 'hr_per_pa', 'k_rate', 'bb_rate']
embeddings = create_embedding_vector(batters_df, feature_cols, dim=128)

# Build faiss index
index = faiss.IndexFlatIP(128)  # Inner product = cosine for normalized vectors
index.add(embeddings)

# Search for similar players
query_idx = 0
query_vec = embeddings[query_idx:query_idx+1]
distances, indices = index.search(query_vec, k=10)

print("Most similar players:")
for rank, (idx, dist) in enumerate(zip(indices[0], distances[0]), 1):
    player_id = batters_df.iloc[idx]['player_id']
    print(f"  {rank}. {player_id}: similarity={dist:.4f}")
```

### Using PostgreSQL pgvector for similarity search

If embeddings are saved to PostgreSQL:

```sql
-- Find 10 most similar players to a given player
SELECT
    player_id,
    player_type,
    1 - (embedding <=> query_embedding) AS cosine_similarity
FROM embeddings.player_embeddings
WHERE player_type = 'batter'
ORDER BY embedding <=> query_embedding::vector
LIMIT 10;
```

## File Structure

```
retrosheet/
├── scripts/vector/
│   ├── __init__.py
│   ├── build_player_embeddings.py   # Main embedding builder
│   ├── similarity_search.py          # CLI for searching similar players
│   └── install_faiss_check.py         # Installation check
├── sql/vector/
│   └── 001_faiss_schema.sql          # pgvector table definitions
├── docs/vector/
│   ├── FAISS_INTEGRATION.md          # This document
│   └── USAGE_EXAMPLES.md             # More usage patterns
└── tests/unit/test_vector_embeddings.py
```

## Performance

- **Index build time**: ~2 seconds for 1000 players (128-dim)
- **Query time**: <1ms per query with IndexFlatIP (small datasets)
- **Index size**: 128-dim float32 ≈ 512 bytes per vector

For larger datasets (>100K vectors), consider:
- `faiss.IndexIVFFlat` for faster search at cost of accuracy
- `faiss.IndexPQ` for compressed storage
- `faiss.IndexHNSW` for high recall

## Relationship to pgvector

FAISS and pgvector serve complementary roles:

| Feature | FAISS (in-app) | pgvector (in-DB) |
|---------|----------------|-----------------|
| Speed | Very fast (in-memory) | Fast with HNSW index |
| Data freshness | Requires reload | Always current |
| Scale | Fits in app memory | Scales with DB size |
| Persistence | Manual | Automatic |

Recommended pattern:
- Use **FAISS** for real-time inference where data fits in memory
- Use **pgvector** for ad-hoc queries and large-scale similarity

## Future Work

- [ ] Extend to pitch sequence embeddings using LSTM encoder
- [ ] Add team embedding vectors from team performance features
- [ ] Implement incremental index updates for live data
- [ ] Add HNSW index support for better scalability
- [ ] Integrate with prediction engine for similarity-based context features
