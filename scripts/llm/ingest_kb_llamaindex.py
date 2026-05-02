#!/usr/bin/env python3
"""Ingest the knowledge-base (kb) into a LlamaIndex vector store.

The script walks the ``kb`` directory, reads PDFs and plain-text files, splits
them into manageable chunks, and builds a persistent index under ``kb/index``.

Prerequisites (install once):
    pip install llama-index openai pymupdf tqdm

You must have an OpenAI (or compatible) API key in the environment variable
``OPENAI_API_KEY`` for the default LLM predictor.  If you prefer another LLM,
adjust the ``LLMPredictor`` construction accordingly.
"""

import sys
from pathlib import Path

from langchain.llms import OpenAI
from llama_index import (
    LLMPredictor,
    ServiceContext,
    SimpleDirectoryReader,
    VectorStoreIndex,
)
from tqdm import tqdm


KB_ROOT = Path(__file__).resolve().parents[1] / 'kb'
INDEX_DIR = KB_ROOT / 'index'


def build_index():
    # Load all supported documents from the kb folder (PDF, txt, md, html)
    reader = SimpleDirectoryReader(input_dir=str(KB_ROOT), recursive=True)
    documents = []
    for doc in tqdm(reader.load_data(), desc='Loading documents'):
        documents.append(doc)

    # Configure the LLM predictor. The original implementation required an
    # OpenAI API key and used the `OpenAI` wrapper. To make the script usable
    # without OpenAI credentials (e.g., when a Gemini API key is provided), we
    # fall back to a minimal `ServiceContext` that does **not** require an LLM.
    # This still allows the vector store to be built using the default
    # embedding model bundled with LlamaIndex.
    if "OPENAI_API_KEY" in os.environ and os.environ["OPENAI_API_KEY"]:
        # Use OpenAI if the key is present – retains original behaviour.
        llm = OpenAI(model='gpt-4', temperature=0.0)
        predictor = LLMPredictor(llm=llm)
        service_context = ServiceContext.from_defaults(llm_predictor=predictor)
    else:
        # No OpenAI key; create a context without an LLM predictor.
        # LlamaIndex will use its default embedding model for indexing.
        service_context = ServiceContext.from_defaults()

    index = VectorStoreIndex.from_documents(documents, service_context=service_context)
    index.storage_context.persist(persist_dir=str(INDEX_DIR))
    print(f'✅ Index persisted to {INDEX_DIR}')


def query_index(query: str, top_k: int = 5):
    from llama_index import StorageContext, load_index_from_storage

    storage_context = StorageContext.from_defaults(persist_dir=str(INDEX_DIR))
    index = load_index_from_storage(storage_context)
    response = index.as_query_engine().query(query)
    print('--- Query Result ---')
    print(response)


def main():
    if len(sys.argv) == 1:
        # No arguments - build the index
        build_index()
    else:
        # Treat the rest of the command line as a query
        query = ' '.join(sys.argv[1:])
        query_index(query)


if __name__ == '__main__':
    main()
