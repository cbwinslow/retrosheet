#!/usr/bin/env python3
"""LangChain Baseball Agent (placeholder)

This module was moved from ``scripts/langchain_baseball_agent.py`` into the
``scripts.llm`` package and renamed ``agent.py``. The implementation is
unchanged – it provides a minimal stub that satisfies the ``BaseballAgent``
adapter and the unit tests.
"""

from typing import Any, Dict
import os

# Optional Prometheus metrics integration. The project already uses OpenTelemetry
# elsewhere; this addition provides a simple counter for the number of queries
# processed by the LangChain agent. If the ``prometheus_client`` package is not
# installed, the import is ignored and the metric becomes a no‑op.
try:
    from prometheus_client import Counter as PrometheusCounter
except Exception:  # pragma: no cover
    class _NoOpCounter:
        def __init__(self, *_, **__):
            pass

        def inc(self, *_, **__):
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
        # Initialise Prometheus counter if the real client is available; otherwise
        # use the no‑op fallback defined above.
        self._query_counter = PrometheusCounter(
            "langchain_agent_queries_total",
            "Total number of queries processed by the LangChain baseball agent",
        )

    def process_query(self, user_query: str) -> Dict[str, Any]:
        """Process a query using a minimal LlamaIndex‑backed LangChain agent.

        The implementation attempts to load the vector store built by
        ``scripts/llm/ingest_kb.py`` and runs a simple similarity query. If the
        index cannot be loaded (e.g., the build step has not run), the method
        falls back to the original placeholder response so that existing tests
        continue to pass.
        """
        # Increment Prometheus counter if metrics are enabled.
        if getattr(self, "_query_counter", None) is not None:
            self._query_counter.inc()

        try:
            from llama_index import VectorStoreIndex

            index_path = "data/llama_index"
            if os.path.isdir(index_path):
                index = VectorStoreIndex.load_from_disk(index_path)
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

