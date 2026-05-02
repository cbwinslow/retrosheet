#!/usr/bin/env python3
"""Quick query script for code RAG index."""
import sys
import argparse
from pathlib import Path

import qdrant_client
from sentence_transformers import SentenceTransformer

QDRANT_HOST = "http://localhost:6333"

def query_code(query_text: str, collection: str, top_k: int = 5):
    print(f"Query: {query_text}")
    print(f"Collection: {collection}")
    print("-" * 50)
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    client = qdrant_client.QdrantClient(url=QDRANT_HOST)
    query_vector = model.encode([query_text])[0].tolist()
    results = client.query_points(
        collection_name=collection,
        query=query_vector,
        limit=top_k,
        with_payload=True,
    )
    print(f"\nResults:\n")
    for i, result in enumerate(results.points, 1):
        payload = result.payload
        print(f"Result {i} | Score: {result.score:.4f}")
        print(f"File: {payload.get('filepath', 'unknown')}")
        print(f"Lines: {payload.get('start_line', '?')}-{payload.get('end_line', '?')}")
        content = payload.get('content', '')
        preview = content[:400] + "..." if len(content) > 400 else content
        print(preview)
        print()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--collection", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    query_code(args.query, args.collection, args.top_k)

if __name__ == "__main__":
    main()
