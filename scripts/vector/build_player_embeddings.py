#!/usr/bin/env python3
"""
File: scripts/vector/build_player_embeddings.py
Purpose: Build player embeddings from feature data for similarity search using faiss
Author: Agent KiloSwift
Date: 2026-04-27
Usage: uv run python scripts/vector/build_player_embeddings.py --season 2024
Dependencies: faiss-cpu, numpy, psycopg, pandas
Notes: Creates vector embeddings of players based on their performance features
"""

import argparse

This script creates vector representations of players based on their
performance statistics, enabling similarity search and clustering.
Output can be stored in PostgreSQL (using pgvector) or saved to disk
(for faiss-cpu indexing).
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from baseball.core.db import get_db_connection

def parse_args():
    parser = argparse.ArgumentParser(description="Build player embeddings from feature data")
    parser.add_argument(
        "--season",
        type=int,
        default=2024,
        help="Season to build embeddings for (default: 2024)"
    )
    parser.add_argument(
        "--feature-set",
        choices=["basic", "advanced", "full"],
        default="full",
        help="Feature set to use for embeddings"
    )
    parser.add_argument(
        "--output",
        choices=["postgres", "numpy", "faiss"],
        default="postgres",
        help="Output format: postgres (pgvector), numpy (.npy), or faiss index"
    )
    parser.add_argument(
        "--dim",
        type=int,
        default=128,
        help="Embedding dimension (default: 128)"
    )
    parser.add_argument(
        "--min-pa",
        type=int,
        default=50,
        help="Minimum plate appearances for batters (default: 50)"
    )
    parser.add_argument(
        "--min-bf",
        type=int,
        default=50,
        help="Minimum batters faced for pitchers (default: 50)"
    )
    return parser.parse_args()

def load_batter_features(season: int, min_pa: int) -> pd.DataFrame:
    """Load batter feature data from warehouse."""
    query = f"""
        SELECT
            player_id,
            player_name,
            pa AS plate_appearances,
            obp,
            slg,
            ops,
            woba,
            babip,
            iso,
            hr_per_pa,
            k_rate,
            bb_rate,
            -- Normalized z-scores for feature vector
            (obp - (SELECT AVG(obp) FROM features.batter_season WHERE season = {season})) /
            NULLIF((SELECT STDDEV(obp) FROM features.batter_season WHERE season = {season}), 0) AS z_obp,
            (slg - (SELECT AVG(slg) FROM features.batter_season WHERE season = {season})) /
            NULLIF((SELECT STDDEV(slg) FROM features.batter_season WHERE season = {season}), 0) AS z_slg,
            (woba - (SELECT AVG(woba) FROM features.batter_season WHERE season = {season})) /
            NULLIF((SELECT STDDEV(woba) FROM features.batter_season WHERE season = {season}), 0) AS z_woba
        FROM features.batter_season
        WHERE season = {season}
          AND pa >= {min_pa}
    """
    conn = get_db_connection()
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def load_pitcher_features(season: int, min_bf: int) -> pd.DataFrame:
    """Load pitcher feature data from warehouse."""
    query = f"""
        SELECT
            player_id,
            player_name,
            bf AS batters_faced,
            era,
            whip,
            fip,
            xfip,
            k_per_9,
            bb_per_9,
            hr_per_9,
            sw_strike_pct,
            -- Normalized z-scores
            (era - (SELECT AVG(era) FROM features.pitcher_season WHERE season = {season})) /
            NULLIF((SELECT STDDEV(era) FROM features.pitcher_season WHERE season = {season}), 0) AS z_era,
            (whip - (SELECT AVG(whip) FROM features.pitcher_season WHERE season = {season})) /
            NULLIF((SELECT STDDEV(whip) FROM features.pitcher_season WHERE season = {season}), 0) AS z_whip,
            (fip - (SELECT AVG(fip) FROM features.pitcher_season WHERE season = {season})) /
            NULLIF((SELECT STDDEV(fip) FROM features.pitcher_season WHERE season = {season}), 0) AS z_fip
        FROM features.pitcher_season
        WHERE season = {season}
          AND bf >= {min_bf}
    """
    conn = get_db_connection()
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def create_embedding_vector(df: pd.DataFrame, feature_cols: list, dim: int) -> np.ndarray:
    """Create embedding vectors from feature columns using PCA if needed."""
    # Extract features
    features = df[feature_cols].fillna(0).values

    # Normalize to unit vectors
    norms = np.linalg.norm(features, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = features / norms

    # If features dimension != desired dim, use PCA to reduce/increase
    if normalized.shape[1] != dim:
        from sklearn.decomposition import PCA
        pca = PCA(n_components=dim, random_state=42)
        normalized = pca.fit_transform(normalized)
        # Re-normalize after PCA
        norms = np.linalg.norm(normalized, axis=1, keepdims=True)
        norms[norms == 0] = 1
        normalized = normalized / norms

    return normalized.astype(np.float32)

def build_faiss_index(embeddings: np.ndarray) -> "faiss.Index":
    """Build a faiss index for similarity search."""
    import faiss

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # Inner product = cosine sim for normalized vectors
    index.add(embeddings)
    return index

def save_embeddings_postgres(player_ids: list, embeddings: np.ndarray, player_type: str, season: int):
    """Save embeddings to PostgreSQL using pgvector."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        # Create table if not exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS embeddings.player_embeddings (
                player_id TEXT NOT NULL,
                player_type TEXT NOT NULL CHECK (player_type IN ('batter', 'pitcher')),
                season INTEGER NOT NULL,
                embedding vector(%s),
                created_at TIMESTAMP DEFAULT now(),
                PRIMARY KEY (player_id, player_type, season)
            );
        """, (embeddings.shape[1],))

        # Upsert embeddings
        for i, pid in enumerate(player_ids):
            cur.execute("""
                INSERT INTO embeddings.player_embeddings
                (player_id, player_type, season, embedding)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (player_id, player_type, season)
                DO UPDATE SET embedding = EXCLUDED.embedding;
            """, (pid, player_type, season, embeddings[i].tolist()))

    conn.commit()
    conn.close()
    print(f"✅ Saved {len(player_ids)} {player_type} embeddings to PostgreSQL")

def main():
    args = parse_args()
    print(f"Building player embeddings for season {args.season}")
    print("-" * 50)

    # Load features
    print("📊 Loading batter features...")
    batters_df = load_batter_features(args.season, args.min_pa)
    print(f"   Loaded {len(batters_df)} batters")

    print("📊 Loading pitcher features...")
    pitchers_df = load_pitcher_features(args.season, args.min_bf)
    print(f"   Loaded {len(pitchers_df)} pitchers")

    # Define feature columns based on feature set
    batter_feature_cols = [
        'z_obp', 'z_slg', 'z_woba', 'pa', 'hr_per_pa', 'k_rate', 'bb_rate'
    ]
    pitcher_feature_cols = [
        'z_era', 'z_whip', 'z_fip', 'bf', 'k_per_9', 'bb_per_9', 'hr_per_9', 'sw_strike_pct'
    ]

    # Create embeddings
    print("\n🔧 Creating batter embeddings...")
    batter_embeddings = create_embedding_vector(batters_df, batter_feature_cols, args.dim)

    print("🔧 Creating pitcher embeddings...")
    pitcher_embeddings = create_embedding_vector(pitchers_df, pitcher_feature_cols, args.dim)

    all_embeddings = np.vstack([batter_embeddings, pitcher_embeddings])
    all_ids = batters_df['player_id'].tolist() + pitchers_df['player_id'].tolist()
    all_types = ['batter'] * len(batters_df) + ['pitcher'] * len(pitchers_df)

    print(f"\n📐 Embedding shape: {all_embeddings.shape}")
    print(f"   Mean norm: {np.mean(np.linalg.norm(all_embeddings, axis=1)):.4f}")

    # Save based on output format
    if args.output == "postgres":
        save_embeddings_postgres(
            batters_df['player_id'].tolist(),
            batter_embeddings,
            'batter',
            args.season
        )
        save_embeddings_postgres(
            pitchers_df['player_id'].tolist(),
            pitcher_embeddings,
            'pitcher',
            args.season
        )

    elif args.output == "faiss":
        import faiss
        print("\n💾 Building faiss index...")
        index = build_faiss_index(all_embeddings)
        faiss.write_index(index, f"player_embeddings_{args.season}.index")
        print(f"   Saved faiss index with {index.ntotal} vectors")

        # Save metadata
        metadata = pd.DataFrame({
            'player_id': all_ids,
            'player_type': all_types,
            'player_name': pd.concat([
                batters_df['player_name'],
                pitchers_df['player_name']
            ]).tolist()
        })
        metadata.to_csv(f"player_embeddings_{args.season}_metadata.csv", index=False)
        print(f"   Saved metadata to player_embeddings_{args.season}_metadata.csv")

    elif args.output == "numpy":
        np.save(f"player_embeddings_{args.season}.npy", all_embeddings)
        metadata = pd.DataFrame({
            'player_id': all_ids,
            'player_type': all_types
        })
        metadata.to_csv(f"player_embeddings_{args.season}_metadata.csv", index=False)
        print(f"   Saved embeddings and metadata for {len(all_embeddings)} players")

    # Demonstrate similarity search
    print("\n🔍 Similarity Search Example:")
    if len(batter_embeddings) > 0:
        from random import randrange
        query_idx = randrange(len(batter_embeddings))
        query_embedding = batter_embeddings[query_idx:query_idx+1]

        if args.output == "postgres":
            # Use pgvector similarity search
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT player_id, player_type, 1 - (embedding <=> %s) AS similarity
                    FROM embeddings.player_embeddings
                    WHERE player_type = 'batter'
                    ORDER BY embedding <=> %s
                    LIMIT 5;
                """, (query_embedding[0].tolist(), query_embedding[0].tolist()))
                results = cur.fetchall()
                print("   Top 5 similar batters (pgvector):")
                for pid, ptype, sim in results:
                    print(f"     {pid}: similarity={sim:.4f}")

        elif args.output in ("faiss", "numpy"):
            # Use numpy/fais for similarity
            similarities = np.dot(all_embeddings, query_embedding.T).flatten()
            top_k = 5
            top_indices = np.argsort(-similarities)[:top_k]
            print("   Top 5 similar players:")
            for idx in top_indices:
                print(f"     {all_ids[idx]} ({all_types[idx]}): similarity={similarities[idx]:.4f}")

    print("\n✅ Embeddings build complete.")

if __name__ == "__main__":
    sys.exit(main())
