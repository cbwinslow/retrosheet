"""Agent Adapter

This module provides a thin wrapper that allows the codebase to switch between
the legacy custom baseball agent (`scripts/baseball_chatbot.py`) and a new
LangChain‑based agent implementation. The decision is driven by an environment
variable ``AGENT_BACKEND`` which can be set to ``legacy`` or ``langchain``.

The adapter exposes a single public class ``BaseballAgent`` with the same
interface used throughout the project (currently ``process_query``). Internally
it lazily imports the appropriate implementation to avoid unnecessary heavy
imports when the alternative backend is not used.

Future work will flesh out the LangChain implementation in
``scripts/langchain_baseball_agent.py`` and add proper type hints, logging, and
error handling.
"""

import os
from typing import Any, Dict

# Lazy import placeholders – the actual modules are imported only when needed.
_legacy_agent = None
_langchain_agent = None


def _load_legacy_agent():
    global _legacy_agent
    if _legacy_agent is None:
        from scripts.baseball_chatbot import BaseballQueryAgent as LegacyAgent

        _legacy_agent = LegacyAgent()
    return _legacy_agent


def _load_langchain_agent():
    global _langchain_agent
    if _langchain_agent is None:
        # The LangChain implementation is expected to live in this module.
        # Import lazily to avoid import errors if the file does not yet exist.
        try:
            from scripts.langchain_baseball_agent import LangChainBaseballAgent as LCAgent
        except ImportError as exc:
            raise RuntimeError(
                "LangChain agent module not found. Ensure 'scripts/langchain_baseball_agent.py' exists."
            ) from exc
        _langchain_agent = LCAgent()
    return _langchain_agent


class BaseballAgent:
    """Unified interface for the baseball query agent.

    The class forwards ``process_query`` calls to the selected backend based on
    the ``AGENT_BACKEND`` environment variable. If the variable is unset or set
    to an unknown value, the legacy implementation is used as a safe default.
    """

    def __init__(self) -> None:
        backend = os.getenv("AGENT_BACKEND", "legacy").lower()
        if backend == "langchain":
            self._agent = _load_langchain_agent()
        else:
            # Fallback to legacy implementation.
            self._agent = _load_legacy_agent()

    def process_query(self, user_query: str) -> Dict[str, Any]:
        """Process a user query using the selected backend.

        Parameters
        ----------
        user_query: str
            The natural‑language query from the user.

        Returns
        -------
        dict
            A dictionary containing the agent's response, tool calls, and any
            additional metadata.
        """
        return self._agent.process_query(user_query)


# When executed as a script, demonstrate a simple interactive loop.
if __name__ == "__main__":
    import sys

    agent = BaseballAgent()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        response = agent.process_query(line)
        print(response)
