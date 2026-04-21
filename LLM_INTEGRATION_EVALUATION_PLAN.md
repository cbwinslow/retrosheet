# Evaluation Report: Adding LlamaIndex & LangChain

## 1. Goal
Provide a concise, actionable assessment of where **LlamaIndex** and **LangChain** could be integrated into the retrosheet prediction platform, and outline a plan for a lightweight prototype that can be reviewed before any code changes are made.

## 2. Context
The project is documented in several core files:
* [`AGENTS.md`](AGENTS.md:1‑21) – overall mission, non‑negotiables, data layers.
* [`docs/agents/CURRENT_SNAPSHOT.md`](docs/agents/CURRENT_SNAPSHOT.md:7‑15) – current focus on the historical PA outcome model and live‑bridge work.
* [`docs/agents/PROCEDURES.md`](docs/agents/PROCEDURES.md:1‑30) – canonical workflows for warehouse rebuild, live ingestion, and adding new features.
* [`scripts/baseball_chatbot.py`](scripts/baseball_chatbot.py:1‑200) – skeleton of the core LLM agent (still a work‑in‑progress, see [#49](https://github.com/cbwinslow/retrosheet/issues/49)).
* [#49](https://github.com/cbwinslow/retrosheet/issues/49) – outlines the intended LLM integration with tool‑calling.

These files show that the system already plans to use an LLM for query handling, but the **tool‑calling orchestration** and **knowledge‑base retrieval** are still being built.

## 3. Why LlamaIndex & LangChain?
| Library | Primary Strength | How it maps to current gaps |
|---------|------------------|------------------------------|
| **LlamaIndex** | Structured data ingestion, index building, retrieval‑augmented generation (RAG) over arbitrary data sources (SQL, CSV, JSON). | The platform stores a rich PostgreSQL warehouse (`core`, `features`, `analysis`). LlamaIndex can create a **SQL‑index** that lets the LLM retrieve relevant rows (e.g., recent plate‑appearance stats) without writing custom SQL prompts.
| **LangChain** | Chains, agents, tool‑calling wrappers, memory, callbacks. | The project already defines a **tool execution engine** ([#50](https://github.com/cbwinslow/retrosheet/issues/50)) and an **LLM agent** ([#49](https://github.com/cbwinslow/retrosheet/issues/49)). LangChain provides a battle‑tested **AgentExecutor** that can route user intents to the existing scripts, and a **ConversationBufferMemory** that can keep context across turns.

## 4. Candidate Integration Points
1. **LLM Query Layer** – Replace the custom `BaseballQueryAgent` stub with a LangChain `ConversationalAgent` that uses a **tool‑calling** wrapper around the safe executor ([#50](https://github.com/cbwinslow/retrosheet/issues/50)). This gives us:
   * Automatic parsing of user intent.
   * Built‑in retry / fallback handling.
   * Easy addition of new tools (e.g., `predict_pa_outcome_distribution`).
2. **RAG over Warehouse** – Use LlamaIndex to build a **SQL index** on the `features` and `core` tables that the LLM can query directly. Example use‑cases:
   * “Show the last 5 plate‑appearance outcomes for player X in 2023.”
   * “What is the average park‑run rate for Yankee Stadium?”
   The index can be refreshed after each warehouse rebuild (`scripts/rebuild_warehouse.sh`).
3. **Live‑Bridge Debugging** – When a live game is ingested, we could store the raw JSON payload in a **document store** (LlamaIndex) and let the LLM answer questions like “Why did the bridge mapping fall back to `MLB###` for this game?” without writing ad‑hoc SQL.
4. **Documentation & Knowledge Base** – Index the `docs/agents/*.md` files with LlamaIndex so the LLM can answer procedural questions (e.g., “What is the recommended workflow for adding a new feature mart?”) without hard‑coding the answers.
5. **Prompt Engineering / Few‑Shot Templates** – LangChain’s `PromptTemplate` can centralise the prompts used for model orchestration ([#51](https://github.com/cbwinslow/retrosheet/issues/51)) and ensure consistent formatting for calibration or odds conversion.

## 5. Risks & Mitigations
* **Performance** – RAG queries add latency. Mitigate by caching LlamaIndex query results (LangChain `Cache` wrapper) and limiting index size to the most‑used tables.
* **Security** – Allow‑list only safe SQL queries in the LlamaIndex index. Combine with the existing **Tool Execution Engine** validation ([#50](https://github.com/cbwinslow/retrosheet/issues/50)).
* **Complexity** – Adding two new libraries increases the dependency surface. Keep them optional: wrap imports in try/except and provide a fallback to the current handcrafted agent.

## 6. Recommended Prototype Steps
1. **Add dependencies** (`pip install llama-index langchain`).
2. **Create a small LlamaIndex SQL index** on `features.plate_appearance_outcome_examples` (only a subset of columns needed for RAG). Write a script `scripts/build_llamaindex_sql.py` that can be run after a warehouse rebuild.
3. **Wrap the safe tool executor** (`scripts/tool_executor.py`) with a LangChain `Tool` class.
4. **Instantiate a LangChain `AgentExecutor`** in `scripts/baseball_chatbot.py` that:
   * First attempts a LlamaIndex retrieval for factual questions.
   * Falls back to the tool‑calling agent for actions.
5. **Add a simple test** in `tests/test_llamaindex_integration.py` that queries a known player and asserts the retrieved row matches the database.
6. **Document the prototype** in `docs/agents/PROCEDURES.md` under a new section “LLM‑RAG Integration”.

## 7. Verification Plan
* **Unit tests** – Ensure the LlamaIndex query returns expected rows for a deterministic seed.
* **End‑to‑end test** – Run the chatbot locally, ask a factual question (e.g., “What is the average strikeout rate for 2022?”) and verify the answer matches a direct SQL query.
* **Performance benchmark** – Measure latency of a RAG query vs a raw SQL query; target < 200 ms overhead.
* **Security audit** – Run the existing tool‑execution safety tests to confirm no new injection vectors are introduced.

## 8. Next Steps (Post‑Review)
* Review this report with the team.
* If approved, create a feature branch `llamaindex-langchain-prototype`.
* Implement the prototype following the steps above.
* Iterate based on test results and stakeholder feedback.

---
*Prepared by the planning sub‑agent. No code changes have been made yet.*

