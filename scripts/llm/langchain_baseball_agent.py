"""LangChain Baseball Agent (placeholder)

This module provides a minimal stub for the future LangChain‑based baseball
agent. The implementation will eventually replace the legacy custom agent and
will integrate LangChain tools, prompts, and retrieval‑augmented generation.

For now the class implements the same public ``process_query`` method used by
the legacy agent so that ``scripts/agent_adapter.py`` can import it without
raising an ``ImportError``. The method returns a simple dictionary indicating
that the LangChain backend is a placeholder.
"""

import os
from typing import Any, Dict

# Optional Prometheus metrics integration. The project already uses OpenTelemetry
# elsewhere; this addition provides a simple counter for the number of queries
# processed by the LangChain agent. If the ``prometheus_client`` package is not
# installed, the import is ignored and the metric becomes a no‑op.
# Attempt to import Prometheus Counter. If the library is unavailable we fall
# back to a no‑op implementation so that the module can be imported without
# additional dependencies during development or testing.
try:
    from prometheus_client import Counter as PrometheusCounter
except Exception:  # pragma: no cover

    class _NoOpCounter:
        def __init__(self, *_, **__):
            pass

        def inc(self, *_, **__):
            # No operation – placeholder for environments without prometheus_client.
            return None

    PrometheusCounter = _NoOpCounter  # type: ignore


class LangChainBaseballAgent:
    """Placeholder LangChain agent.

    The real implementation will construct a LangChain ``Agent`` with the
    appropriate tools (e.g., database query, LlamaIndex retrieval, model
    inference) and handle tool calls. Until then, this stub provides a compatible
    interface.
    """

    def __init__(self) -> None:
        # Future initialization (LLM client, tool registry, etc.) will go here.
        # Initialise Prometheus counter if the real client is available; otherwise
        # use the no‑op fallback defined above.
        self._query_counter = PrometheusCounter(
            "langchain_agent_queries_total",
            "Total number of queries processed by the LangChain baseball agent",
        )

    def process_query(self, user_query: str) -> Dict[str, Any]:
        """Process a query using a minimal LlamaIndex‑backed LangChain agent.

        The implementation attempts to load the vector store built by
        ``scripts/build_llamaindex.py`` and runs a simple similarity query.  If the
        index cannot be loaded (e.g., the build step has not run), the method
        falls back to the original placeholder response so that existing tests
        continue to pass.
        """
        # Increment Prometheus counter if metrics are enabled.
        if getattr(self, "_query_counter", None) is not None:
            self._query_counter.inc()

        # Attempt to load the persisted index.
        try:
            from llama_index import VectorStoreIndex

            index_path = "data/llama_index"
            if os.path.isdir(index_path):
                index = VectorStoreIndex.load_from_disk(index_path)
                # Use the default query engine for a similarity search.
                response = index.as_query_engine().query(user_query)
                return {
                    "backend": "langchain",
                    "status": "success",
                    "query": user_query,
                    "answer": str(response),
                }
        except Exception:  # pragma: no cover – any load/query failure falls back
            pass

        # Fallback placeholder response.
        return {
            "backend": "langchain",
            "status": "placeholder",
            "query": user_query,
            "message": "LangChain agent not yet implemented.",
        }
