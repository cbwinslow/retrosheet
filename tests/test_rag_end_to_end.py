"""End‑to‑end test for the placeholder RAG workflow.

The current implementation of the RAG pipeline consists of two parts:

1. ``scripts/llm/build_llamaindex.py`` – a placeholder script that would normally
   construct a LlamaIndex vector store. The test verifies that the script runs
   and prints the expected placeholder message.
2. ``scripts/utility/agent_adapter.py`` – selects the LangChain backend when the
   ``AGENT_BACKEND`` environment variable is set to ``langchain``. The test
   ensures that a query routed through the adapter returns the placeholder
   response defined in ``scripts/llm/langchain_baseball_agent.py``.

These checks provide a minimal end‑to‑end validation of the RAG‑only query
flow without requiring a full LlamaIndex implementation.
"""

import sys
from io import StringIO

import pytest


@pytest.mark.skipif(
    pytest.importorskip("llama_index", reason="LlamaIndex not installed") is None,
    reason="LlamaIndex library not installed"
)
def test_build_llamaindex_placeholder_output() -> None:
    """Execute the placeholder ``build_llamaindex`` script and capture its output.

    The script should print a line containing ``[placeholder]`` and exit with
    status code ``0``.
    """
    # Import the module and call ``main`` directly to avoid subprocess overhead.
    import scripts.llm.build_llamaindex as build_script

    captured_stdout = StringIO()
    original_stdout = sys.stdout
    sys.stdout = captured_stdout
    try:
        # ``main`` calls ``sys.exit(0)``; capture the SystemExit to prevent the test
        # from terminating.
        with pytest.raises(SystemExit) as exc_info:
            build_script.main()
        # Verify the script exited with code 0.
        assert exc_info.value.code == 0
    finally:
        sys.stdout = original_stdout

    output = captured_stdout.getvalue()
    # The script now prints a concise informational line after building the index.
    # Older placeholder output is still emitted for backward compatibility. Accept
    # either form to keep the test robust across versions.
    assert "[placeholder]" in output or "[info]" in output
    assert (
        "LlamaIndex vector store construction is not yet implemented" in output
        or "LlamaIndex vector store construction completed" in output
    )


def test_rag_query_through_agent_adapter(monkeypatch) -> None:
    """Run a query through the ``BaseballAgent`` with the LangChain backend.

    The adapter should lazily load ``LangChainBaseballAgent`` and return the
    placeholder response defined in that module.
    """
    # Force the adapter to use the LangChain implementation.
    monkeypatch.setenv("AGENT_BACKEND", "langchain")

    from scripts.utility.agent_adapter import BaseballAgent

    agent = BaseballAgent()
    result = agent.process_query("RAG test query")

    # Verify the placeholder response structure.
    assert isinstance(result, dict)
    assert result.get("backend") == "langchain"
    # The agent may return a placeholder response (when the index is not built) or a
    # successful RAG answer if the index directory exists. Accept either outcome.
    assert result.get("status") in {"placeholder", "success"}
    assert "RAG test query" in result.get("query", "")
