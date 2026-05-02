#!/usr/bin/env python3
"""
File: scripts/vector/index_codebase.py
Purpose: Build RAG index for code context using Qdrant + sentence-transformers
Usage: 
    # Index retrosheet (full)
    uv run python scripts/vector/index_codebase.py --repo retrosheet
    
    # Index current directory
    uv run python scripts/vector/index_codebase.py --repo . --name my-codebase
    
    # Query the index
    uv run python scripts/vector/index_codebase.py --query "How does the caching work?"
    
    # List available indexes
    uv run python scripts/vector/index_codebase.py --list
"""

import argparse
import hashlib
import os
import sys
import time
from pathlib import Path
from typing import Optional

import qdrant_client
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Qdrant configuration
QDRANT_HOST = "http://localhost:6333"
COLLECTION_PREFIX = "code-rag-"

# File extensions to index (core languages for code understanding)
CODE_EXTENSIONS = {
    ".py", ".sql", ".sh",
    ".md", ".yaml", ".yml", ".json", ".toml",
}

# Directories to exclude
EXCLUDE_DIRS = {
    ".git", ".venv", "node_modules", "__pycache__",
    ".pytest_cache", ".mypy_cache", "dist", "build",
    ".next", ".nuxt", "target", "vendor", ".tox",
    "venv", "env", ".env", ".cache", ".egg-info"
}


def get_file_hash(filepath: Path) -> str:
    """Get MD5 hash of file for change detection."""
    return hashlib.md5(str(filepath.stat().st_mtime).encode()).hexdigest()[:8]


def should_index_file(filepath: Path) -> bool:
    """Check if file should be indexed."""
    # Check extension
    if filepath.suffix not in CODE_EXTENSIONS:
        return False
    
    # Check excluded dirs
    parts = filepath.parts
    for excluded in EXCLUDE_DIRS:
        if excluded in parts:
            return False
    
    return True


def chunk_code(content: str, max_chars: int = 1000, overlap: int = 100) -> list[dict]:
    """Split code into chunks with context."""
    lines = content.split("\n")
    chunks = []
    current_chunk = []
    current_size = 0
    start_line = 1
    
    for i, line in enumerate(lines, 1):
        line_size = len(line) + 1
        
        if current_size + line_size > max_chars and current_chunk:
            # Save chunk
            chunk_content = "\n".join(current_chunk)
            chunks.append({
                "content": chunk_content,
                "start_line": start_line,
                "end_line": i - 1,
                "size": current_size
            })
            
            # Start new chunk with overlap
            overlap_lines = current_chunk[-3:] if len(current_chunk) > 3 else current_chunk
            current_chunk = overlap_lines + [line]
            current_size = sum(len(l) + 1 for l in current_chunk)
            start_line = i - len(overlap_lines)
        else:
            current_chunk.append(line)
            current_size += line_size
    
    # Don't forget last chunk
    if current_chunk:
        chunks.append({
            "content": "\n".join(current_chunk),
            "start_line": start_line,
            "end_line": len(lines),
            "size": current_size
        })
    
    return chunks


def get_repo_name(repo_path: str) -> str:
    """Get normalized collection name for repo."""
    path = Path(repo_path).resolve()
    # Use parent and folder name to create unique name
    parent = path.parent.name
    folder = path.name
    name = f"{parent}-{folder}".replace(".", "_").replace("-", "_")
    return COLLECTION_PREFIX + name


def index_repository(
    repo_path: str,
    collection_name: Optional[str] = None,
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
) -> None:
    """Index all code files in a repository."""
    repo_path = Path(repo_path).resolve()
    
    if collection_name is None:
        collection_name = get_repo_name(repo_path)
    
    print(f"📚 Indexing: {repo_path}")
    print(f"   Collection: {collection_name}")
    print(f"   Model: {model_name}")
    print("-" * 50)
    
    # Load embedding model
    print("🧠 Loading embedding model...")
    model = SentenceTransformer(model_name)
    embedding_dim = model.get_embedding_dimension()
    print(f"   Embedding dimension: {embedding_dim}")
    
    # Initialize Qdrant client
    print("🔌 Connecting to Qdrant...")
    client = qdrant_client.QdrantClient(url=QDRANT_HOST)
    
    # Create or get collection
    collection_exists = False
    try:
        client.get_collection(collection_name)
        collection_exists = True
    except Exception:
        pass
    
    if collection_exists:
        print(f"   Collection exists, recreating...")
        client.delete_collection(collection_name)
        time.sleep(1)  # Wait for deletion to complete
    
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=embedding_dim,
            distance=models.Distance.COSINE
        )
    )
    print(f"   Created collection: {collection_name}")
    
    # Collect all files and chunks
    all_chunks = []
    file_count = 0
    
    print("\n📂 Scanning files...")
    for filepath in repo_path.rglob("*"):
        if not filepath.is_file() or not should_index_file(filepath):
            continue
        
        try:
            content = filepath.read_text(errors="ignore")
            if not content.strip():
                continue
            
            chunks = chunk_code(content)
            relative_path = str(filepath.relative_to(repo_path))
            
            for chunk in chunks:
                all_chunks.append({
                    "content": chunk["content"],
                    "metadata": {
                        "filepath": relative_path,
                        "repo": str(repo_path),
                        "extension": filepath.suffix,
                        "start_line": chunk["start_line"],
                        "end_line": chunk["end_line"],
                    }
                })
            
            file_count += 1
            if file_count % 100 == 0:
                print(f"   Found {file_count} files, {len(all_chunks)} chunks...")
                
        except Exception as e:
            continue
    
    print(f"\n📊 Found {file_count} files, {len(all_chunks)} chunks")
    
    # Generate embeddings and upload in streaming fashion
    print("\n🔢 Generating embeddings and uploading...")
    batch_size = 64
    total_uploaded = 0
    
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i + batch_size]
        texts = [chunk["content"] for chunk in batch]
        embeddings = model.encode(texts, show_progress_bar=False)
        
        points = [
            models.PointStruct(
                id=f"{i + j}",
                vector=embedding.tolist(),
                payload={
                    "content": chunk["content"],
                    **chunk["metadata"]
                }
            )
            for j, (chunk, embedding) in enumerate(zip(batch, embeddings))
        ]
        
        # Upload batch immediately
        client.upsert_points(
            collection_name=collection_name,
            points=points,
        )
        total_uploaded += len(points)
        
        if (i // batch_size) % 5 == 0:
            print(f"   Uploaded {total_uploaded}/{len(all_chunks)} chunks...")
    
    print(f"\n✅ Indexed {len(all_chunks)} chunks from {file_count} files")
    print(f"   Collection: {collection_name}")
    print(f"   Query with: --collection {collection_name}")


def query_index(
    query: str,
    collection_name: str,
    top_k: int = 5,
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
) -> None:
    """Query the RAG index."""
    print(f"🔍 Query: {query}")
    print(f"   Collection: {collection_name}")
    print(f"   Top k: {top_k}")
    print("-" * 50)
    
    # Load model
    model = SentenceTransformer(model_name)
    
    # Connect to Qdrant
    client = qdrant_client.QdrantClient(url=QDRANT_HOST)
    
    # Generate query embedding
    query_vector = model.encode([query])[0].tolist()
    
    # Search
    results = client.search(
        collection_name=collection_name,
        query_vector=query_vector,
        limit=top_k,
        with_payload=True
    )
    
    # Display results
    print(f"\n📋 Top {len(results)} Results:\n")
    for i, result in enumerate(results, 1):
        payload = result.payload
        print(f"{'='*60}")
        print(f"Result {i} (score: {result.score:.4f})")
        print(f"📄 File: {payload['filepath']}")
        print(f"📍 Lines: {payload['start_line']}-{payload['end_line']}")
        print(f"{'-'*60}")
        
        # Show snippet
        content = payload["content"]
        preview = content[:500] + "..." if len(content) > 500 else content
        print(preview)
        print()


def list_collections() -> None:
    """List all indexed collections."""
    client = qdrant_client.QdrantClient(url=QDRANT_HOST)
    collections = client.get_collections().collections
    
    print("📚 Available Code RAG Collections:\n")
    for col in collections:
        if col.name.startswith(COLLECTION_PREFIX):
            info = client.get_collection(col.name)
            vec_count = info.vectors_count
            print(f"  • {col.name}")
            print(f"    Vectors: {vec_count:,}")
            print()


def delete_collection(collection_name: str) -> None:
    """Delete a collection."""
    client = qdrant_client.QdrantClient(url=QDRANT_HOST)
    client.delete_collection(collection_name)
    print(f"✅ Deleted collection: {collection_name}")


def main():
    parser = argparse.ArgumentParser(description="Code RAG indexing and search")
    
    # Index options
    parser.add_argument("--repo", type=str, help="Repository path to index")
    parser.add_argument("--name", type=str, help="Custom collection name")
    parser.add_argument("--model", type=str, 
                       default="sentence-transformers/all-MiniLM-L6-v2",
                       help="Embedding model")
    
    # Query options
    parser.add_argument("--query", type=str, help="Query string")
    parser.add_argument("--collection", type=str, help="Collection to query")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results")
    
    # List/delete options
    parser.add_argument("--list", action="store_true", help="List all collections")
    parser.add_argument("--delete", type=str, help="Delete a collection")
    
    args = parser.parse_args()
    
    if args.list:
        list_collections()
    elif args.delete:
        delete_collection(args.delete)
    elif args.repo:
        index_repository(
            repo_path=args.repo,
            collection_name=args.name,
            model_name=args.model
        )
    elif args.query and args.collection:
        query_index(
            query=args.query,
            collection_name=args.collection,
            top_k=args.top_k,
            model_name=args.model
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
