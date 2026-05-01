#!/usr/bin/env python3
"""
File: scripts/vector/similarity_search.py
Purpose: CLI tool for searching similar players using faiss or pgvector
Author: Agent KiloSwift
Date: 2026-04-27
Usage: uv run python scripts/vector/similarity_search.py --player-id 123456 --type batter --top-k 10
Dependencies: faiss-cpu, numpy, psycopg (optional for pgvector backend)
"""

import argparse
import sys
from pathlib import Path


# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np

from baseball.core.db import get_db_connection


def parse_args():
    parser = argparse.ArgumentParser(description='Find similar players using precomputed embeddings')
    parser.add_argument('--player-id', type=int, required=True, help='Player ID to find similar players for')
    parser.add_argument('--type', choices=['batter', 'pitcher'], required=True, help='Player type')
    parser.add_argument('--season', type=int, default=2024, help='Season (default: 2024)')
    parser.add_argument('--top-k', type=int, default=10, help='Number of similar players to return')
    parser.add_argument('--backend', choices=['faiss', 'pgvector'], default='pgvector', help='Search backend')
    parser.add_argument('--index-path', type=Path, help='Path to faiss index file (required if backend=faiss)')
    parser.add_argument('--min-similarity', type=float, default=0.5, help='Minimum cosine similarity (0-1)')
    return parser.parse_args()

def load_embedding_pgvector(player_id: int, player_type: str, season: int):
    """Load a player's embedding from PostgreSQL pgvector."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT embedding
            FROM embeddings.player_embeddings
            WHERE player_id = %s AND player_type = %s AND season = %s
        """, (player_id, player_type, season))
        row = cur.fetchone()
        if row is None:
            return None
        return np.array(row[0], dtype=np.float32)

def search_similar_pgvector(player_id: int, player_type: str, season: int, top_k: int, min_sim: float):
    """Find similar players using pgvector similarity search."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                pe.player_id,
                pe.player_type,
                (1 - (pe.embedding <=> q.embedding)) AS similarity,
                p.player_name
            FROM
                embeddings.player_embeddings pe,
                (SELECT embedding FROM embeddings.player_embeddings
                 WHERE player_id = %s AND player_type = %s AND season = %s) q,
                core.players p ON pe.player_id = p.player_id
            WHERE
                pe.player_id != %s
                AND pe.player_type = %s
                AND 1 - (pe.embedding <=> q.embedding) >= %s
            ORDER BY pe.embedding <=> q.embedding
            LIMIT %s
        """, (player_id, player_type, season, player_id, player_type, min_sim, top_k))
        return cur.fetchall()

def search_similar_faiss(player_id: int, player_type: str, season: int, top_k: int, min_sim: float, index_path: Path):
    """Find similar players using FAISS index."""
    import faiss

    # Load embedding for query player
    query_vec = load_embedding_pgvector(player_id, player_type, season)
    if query_vec is None:
        print(f'❌ Player {player_id} not found in embeddings for {season}')
        sys.exit(1)

    # Load FAISS index
    if not index_path.exists():
        print(f'❌ FAISS index not found at {index_path}')
        sys.exit(1)
    index = faiss.read_index(str(index_path))

    # Search (index contains normalized vectors, query already normalized)
    query_vec = query_vec.reshape(1, -1)
    faiss.normalize_L2(query_vec)
    distances, indices = index.search(query_vec, min(top_k + 1, index.ntotal))

    # Map indices back to player IDs (need metadata)
    # This requires metadata file: player_embeddings_2024_metadata.csv
    metadata_path = index_path.parent / f'{index_path.stem}_metadata.csv'
    if not metadata_path.exists():
        print(f'❌ Metadata not found at {metadata_path}')
        sys.exit(1)

    import pandas as pd
    metadata = pd.read_csv(metadata_path)

    results = []
    for dist, idx in zip(distances[0], indices[0], strict=False):
        if idx >= len(metadata):
            continue
        sim = float(dist)  # FAISS returns inner product = cosine similarity for normalized vectors
        if sim < min_sim:
            continue
        row = metadata.iloc[idx]
        results.append((row['player_id'], row['player_type'], sim, row.get('player_name', 'Unknown')))

    return results

def main():
    args = parse_args()
    print(f'🔍 Searching for similar {args.type}s to player {args.player_id} (season {args.season})...')

    if args.backend == 'pgvector':
        results = search_similar_pgvector(args.player_id, args.type, args.season, args.top_k, args.min_similarity)
    else:
        if not args.index_path:
            print('❌ --index-path required for faiss backend')
            sys.exit(1)
        results = search_similar_faiss(args.player_id, args.type, args.season, args.top_k, args.min_similarity, args.index_path)

    if not results:
        print('No similar players found matching criteria.')
        return 0

    print(f'\n✅ Top {len(results)} similar players:')
    print(f"{'Rank':<6} {'Player ID':<12} {'Name':<25} {'Type':<8} {'Similarity':<10}")
    print('-' * 65)
    for rank, (pid, ptype, sim, name) in enumerate(results, 1):
        print(f'{rank:<6} {pid:<12} {name:<25} {ptype:<8} {sim:.4f}')

    return 0

if __name__ == '__main__':
    sys.exit(main())
