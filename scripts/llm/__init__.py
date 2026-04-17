"""LLM / RAG package

This subpackage groups all scripts related to the LlamaIndex and LangChain
integration.  It provides a stable public API via re‑exports so that other
modules can import the functionality without needing to know the exact file
names.

Exports:
    - ``build_index`` – wrapper for ``scripts/llm/build_index.py``
    - ``ingest_kb``   – wrapper for ``scripts/llm/ingest_kb.py``
    - ``llm_agent``   – wrapper for ``scripts/llm/agent.py``
"""

from .build_index import main as build_index
from .ingest_kb   import main as ingest_kb
from .agent       import main as llm_agent

__all__ = ["build_index", "ingest_kb", "llm_agent"]

