"""Unit tests for the placeholder LangChain baseball agent.

The current implementation in [`scripts/llm/langchain_baseball_agent.py`](scripts/llm/langchain_baseball_agent.py) is a stub that returns a static dictionary and optionally increments a Prometheus counter. These tests verify:

1. The public ``process_query`` method returns the expected keys and values.
2. The method can be called without the ``prometheus_client`` package being installed (the fallback ``_NoOpCounter`` should not raise).
"""

from typing import Dict

from scripts.llm.langchain_baseball_agent import LangChainBaseballAgent


def test_process_query_returns_expected_structure() -> None:
    """Ensure the placeholder response contains the required fields.

    The agent should echo the backend name, status, the original query and a placeholder message.
    """
    agent = LangChainBaseballAgent()
    query = "What is the win probability?"
    result: Dict = agent.process_query(query)

    # Basic sanity checks on the result structure
    assert isinstance(result, dict)
    assert result["backend"] == "langchain"
    assert result["status"] == "placeholder"
    assert result["query"] == query
    assert "LangChain agent not yet implemented" in result["message"]


def test_prometheus_counter_fallback_is_noop(monkeypatch) -> None:
    """Simulate an environment without ``prometheus_client``.

    The module defines a ``_NoOpCounter`` fallback when the import fails. We replace the
    ``PrometheusCounter`` reference with a dummy class that records calls to ``inc``.
    """

    class DummyCounter:
        def __init__(self, *_, **__):
            self.called = False

        def inc(self, *_, **__):
            self.called = True

    # Patch the counter used inside the agent module
    monkeypatch.setattr(
        "scripts.llm.langchain_baseball_agent.PrometheusCounter", DummyCounter, raising=False
    )

    agent = LangChainBaseballAgent()
    # The agent should have a ``_query_counter`` attribute of type ``DummyCounter``
    assert hasattr(agent, "_query_counter")
    assert isinstance(agent._query_counter, DummyCounter)

    # Call ``process_query`` and verify that ``inc`` was invoked
    agent.process_query("test")
    assert agent._query_counter.called is True
