# LLM Integration Recommendation & Implementation Plan

## 1. Recommendation Summary
- **LangChain**: **Recommended** as the primary framework for the chatbot agent.
  - Provides a mature **tool‑calling** abstraction that matches the existing `ToolRegistry` design in [`scripts/baseball_chatbot.py`](scripts/baseball_chatbot.py).
  - Offers built‑in **memory**, **prompt templates**, and **callback** hooks for observability, which align with the project’s goal of industry‑standard AI‑programming constructs (MCP, agents, tools, audit logging).
  - Easy to wrap the current custom `BaseballQueryAgent` logic into a `ConversationalAgent` with minimal code changes.

- **LlamaIndex**: **Recommended** as a complementary retrieval layer.
  - Can index the **SQL warehouse** (`core`, `features`, `analysis` schemas) and the **documentation** (`docs/agents/*.md`) to provide **RAG** capabilities for factual Q&A and procedural assistance.
  - Works well with LangChain via the `langchain_community.vectorstores` adapters, allowing a single agent to call both **tool** functions and **retrieval** tools.

**Overall effort**: ~2‑3 weeks for a prototype (index build, LangChain agent wrapper, integration tests) followed by a review cycle.

## 2. Compliance with AI‑Programming Standards
The codebase already satisfies the core standards:
1. **MCP resources** – defined in `AGENTS.md` and used throughout scripts (e.g., `scripts/warehouse.py`).
2. **Agents** – `BaseballQueryAgent` implements the agent pattern with a pluggable LLM client.
3. **Tools** – `ToolRegistry` enumerates safe tool definitions; `scripts/baseball_chatbot.py` validates calls before execution.
4. **Safe Execution Engine** – described in [#50](https://github.com/cbwinslow/retrosheet/issues/50) and partially implemented in the `_execute_tool` method.
5. **Audit Logging** – Letta hook configuration in `AGENTS.md` ensures every prompt/response is logged.

**Gaps / enhancements**:
* **Unified callback system** – LangChain’s callback manager can replace ad‑hoc logging, providing richer traceability.
* **Vector store persistence** – currently no vector DB; adding one (FAISS/Chroma) will complete the retrieval pipeline.
* **Rate‑limiting & policy enforcement** – not yet present; see Section 4 for tool suggestions.

## 3. Additional Tooling Recommendations
| Tool | Purpose | Integration Point |
|------|---------|-------------------|
| **FAISS / ChromaDB** | Vector store for LlamaIndex embeddings | `scripts/` – index build script stores vectors on disk |
| **LangChain PromptTemplate** | Centralised prompt management (system prompt, few‑shot examples) | Replace hard‑coded system prompt in `BaseballQueryAgent._create_system_prompt` |
| **OpenTelemetry / LangChain Callbacks** | Observability of LLM calls, tool execution, latency metrics | Wrap agent with `CallbackManager` |
| **slowapi (Redis‑based) or starlette‑rate‑limit** | API rate limiting for the Next.js `/api/chat` endpoint | `baseball-chatbot-ui/app/api/chat/route.ts` |
| **OPA (Open Policy Agent)** | Fine‑grained access control for betting actions | Middleware in the FastAPI‑style API routes |
| **MLflow** | Experiment tracking for model training & calibration | `scripts/train_models.py` and `scripts/calibrate_pa_outcome_model.py` |
| **Feast** | Feature store to serve low‑latency features to the live prediction service | Replace direct DB reads in `PredictionService.get_features_from_state` |

## 4. Concrete Implementation Steps
### Phase A – Preparation (Days 1‑2)
1. **Create a prototype branch** `feature/llm‑langchain‑llamaindex`.
2. Add `langchain` and `llama-index` to `requirements.txt`.
3. Choose a vector store (FAISS for local dev, Chroma for production) and add the dependency.

### Phase B – Retrieval Layer (Days 3‑5)
1. Write `scripts/build_llamaindex.py`:
   - Connect to PostgreSQL via `psycopg2`.
   - Load tables `core.games`, `core.events`, `features.*` and documentation markdown files.
   - Create a `SQLDatabase` loader (`llama_index.readers.sql.SQLReader`).
   - Build an index with `GPTVectorStoreIndex` using the chosen vector store.
   - Persist the index to `data/llamaindex/warehouse_index.json`.
2. Verify retrieval with a simple script that queries “What is the definition of `win_probability`?” and prints the top‑k results.

### Phase C – Agent Refactor (Days 6‑10)
1. Implement `LangChainBaseballAgent` in `scripts/langchain_baseball_agent.py`:
   - Use `ChatOpenAI` (or `ChatOllama`) as the LLM client.
   - Load the persisted LlamaIndex index via `LLMChain` or `RetrieverQueryEngine`.
   - Define **Tool** objects that wrap the existing safe‑tool functions (`_query_database`, `_predict_plate_appearance`, etc.).
   - Set up `ConversationBufferMemory` to replace `ConversationMemory`.
   - Attach a `CallbackManager` that forwards events to the Letta logging hook.
2. Update `scripts/baseball_chatbot.py` to instantiate `LangChainBaseballAgent` when the `--use-langchain` flag is present (maintain backward compatibility).

### Phase D – Integration & Testing (Days 11‑13)
1. Update the Next.js API route `app/api/chat/route.ts` to call the new agent when the flag is enabled.
2. Write end‑to‑end tests in `scripts/test_chatbot_integration.py` that:
   - Send a query requiring a tool call (e.g., “What is the live odds for the Yankees vs Red Sox?”).
   - Send a retrieval‑only query (e.g., “Explain the purpose of the `bridge.player_xref` table.”).
   - Assert correct JSON structure and that no unsafe SQL is executed.
3. Run existing unit tests to ensure no regressions.

### Phase E – Observability & Ops (Days 14‑15)
1. Enable OpenTelemetry exporter in `scripts/langchain_baseball_agent.py`.
2. Deploy the updated container to a staging environment and monitor latency via the existing Letta logs.
3. Document the new workflow in `docs/agents/PROJECT_OBJECTIVES.md` and update `FILE_INVENTORY.md` with the new scripts.

## 5. Verification Plan
* **Unit tests** – all existing tests must pass (`npm test` for UI, `pytest` for Python scripts).
* **Integration test** – the chatbot returns correct tool results and retrieval answers.
* **Performance benchmark** – compare response latency before and after integration (target < 1 s for tool calls, < 500 ms for pure retrieval).
* **Safety audit** – run the static analysis script `scripts/benchmark_queries.py` to ensure no new unsafe SQL patterns are introduced.

## 6. Acceptance Criteria
- ✅ LangChain agent can handle both tool calls and RAG queries.
- ✅ LlamaIndex index is built and persisted without errors.
- ✅ All existing CI pipelines pass.
- ✅ Documentation updated and reviewed.
- ✅ Stakeholder demo shows real‑time betting‑assistant interaction.

---
*Prepared by the planning sub‑agent. Execute the steps in order and update the plan file as progress is made.*

