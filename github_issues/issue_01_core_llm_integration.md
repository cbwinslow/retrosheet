# GitHub Issues for AI Baseball Analytics Chatbot

## Issue #1: 🏗️ Core LLM Integration with Tool Calling

### Description
Implement the core LLM agent that can understand baseball queries, plan tool executions, and generate natural language responses. This is the brain of our AI chatbot.

### Technical Requirements
- **LLM Integration**: Support for GPT-4, Claude, or local models (Ollama/Llama)
- **Tool Calling**: Structured tool call extraction from LLM responses
- **Context Management**: Maintain conversation history and game state
- **Intent Classification**: Route queries to appropriate tools
- **Response Synthesis**: Combine tool results into coherent answers

### Implementation Details
```python
class BaseballQueryAgent:
    def __init__(self):
        self.llm_client = self._init_llm_client()
        self.tool_registry = self._load_available_tools()
        self.conversation_memory = ConversationMemory()

    def process_query(self, user_query: str) -> Dict:
        # 1. Analyze query intent
        # 2. Extract relevant context (game_id, player, etc.)
        # 3. Select appropriate tools
        # 4. Execute tools safely
        # 5. Synthesize response
        pass
```

### Tool Integration Points
- **Prediction Tools**: 18 ML models via PredictionService
- **Script Tools**: 21+ Python scripts for analysis
- **Database Tools**: Direct SQL queries with safety validation
- **Simulation Tools**: Monte Carlo engines

### Acceptance Criteria
- [ ] Can understand basic baseball queries ("What's the probability of a home run?")
- [ ] Correctly identifies and calls appropriate tools
- [ ] Maintains conversation context across turns
- [ ] Handles tool execution errors gracefully
- [ ] Generates coherent responses combining multiple data sources

### Dependencies
- None (core component)

### Estimated Effort
- **Frontend**: 2-3 days (LLM integration, tool calling)
- **Backend**: 2-3 days (context management, response synthesis)
- **Testing**: 1-2 days (conversation flows, error handling)

### Files to Create/Modify
- `scripts/baseball_chatbot.py` - Main agent class
- `scripts/llm_client.py` - LLM abstraction layer
- `scripts/tool_registry.py` - Tool discovery and validation
- `tests/test_chatbot_agent.py` - Unit tests

### Related Issues
- #2 (Tool Execution Engine)
- #3 (Model Orchestration)
- #7 (API Design)

**Labels**: enhancement, ai, llm, core, priority:high

### Documentation Links
- **AGENTS.md**: [`AGENTS.md`](../AGENTS.md)
- **Overall Strategy**: [`docs/OVERALL_STRATEGY.md`](../docs/OVERALL_STRATEGY.md)
- **Adaptation Map**: [`docs/agents/ADAPTATION_MAP.md`](../docs/agents/ADAPTATION_MAP.md)
