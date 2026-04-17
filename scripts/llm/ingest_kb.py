#!/usr/bin/env python3
"""Ingest the knowledge‑base (kb) into a LlamaIndex vector store.

This file was moved from the top‑level ``scripts`` directory and renamed to
``ingest_kb.py`` within the ``scripts.llm`` package. The implementation is
identical to the original ``ingest_kb_llamaindex.py``.
"""

import sys
from pathlib import Path
from tqdm import tqdm

from llama_index import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    ServiceContext,
    LLMPredictor,
)
from langchain.llms import OpenAI

KB_ROOT = Path(__file__).resolve().parents[1] / "kb"
INDEX_DIR = KB_ROOT / "index"


def build_index():
    """Build and persist a LlamaIndex vector store from the ``kb`` directory."""
    reader = SimpleDirectoryReader(input_dir=str(KB_ROOT), recursive=True)
    documents = []
    for doc in tqdm(reader.load_data(), desc="Loading documents"):
        documents.append(doc)

    llm = OpenAI(model="gpt-4", temperature=0.0)
    predictor = LLMPredictor(llm=llm)
    service_context = ServiceContext.from_defaults(llm_predictor=predictor)

    index = VectorStoreIndex.from_documents(documents, service_context=service_context)
    index.storage_context.persist(persist_dir=str(INDEX_DIR))
    print(f"✅ Index persisted to {INDEX_DIR}")


def query_index(query: str, top_k: int = 5):
    """Run a similarity query against the persisted index."""
    from llama_index import StorageContext, load_index_from_storage

    storage_context = StorageContext.from_defaults(persist_dir=str(INDEX_DIR))
    index = load_index_from_storage(storage_context)
    response = index.as_query_engine().query(query)
    print("--- Query Result ---")
    print(response)


def main():
    if len(sys.argv) == 1:
        build_index()
    else:
        query = " ".join(sys.argv[1:])
        query_index(query)


if __name__ == "__main__":
    main()

