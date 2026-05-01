from __future__ import annotations

import json
import os
import re

# Import our existing infrastructure
import sys
from typing import Any


sys.path.append(os.path.dirname(__file__))

from fast_prediction_service import PredictionService


class LLMClient:
    """Abstract LLM client interface."""

    def chat(self, messages: list[dict], **kwargs) -> str:
        """Send messages to LLM and get response."""
        raise NotImplementedError

    def extract_tool_calls(self, response: str) -> list[dict]:
        """Extract tool calls from LLM response."""
        raise NotImplementedError


class OpenAIClient(LLMClient):
    """OpenAI GPT integration."""

    def __init__(self, api_key: str | None = None, model: str = 'gpt-4'):
        try:
            import openai

            key = api_key or os.environ.get('OPENAI_API_KEY')
            if not key or not key.strip() or key == '' or len(key.strip()) < 10:
                msg = 'No valid OpenAI API key provided'
                raise ValueError(msg)
            # Check if it's actually an OpenAI key (starts with sk-)
            if not key.strip().startswith('sk-'):
                msg = "API key doesn't appear to be an OpenAI key"
                raise ValueError(msg)
            self.client = openai.OpenAI(api_key=key.strip())
            self.model = model
            # Test the client with a simple request
            try:
                self.client.models.list()
            except Exception as e:
                msg = f'OpenAI API key validation failed: {e}'
                raise ValueError(msg)
        except ImportError:
            msg = 'OpenAI package not installed. Run: pip install openai'
            raise ImportError(msg)

    def chat(self, messages: list[dict], **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,  # Low temperature for consistent tool calling
            **kwargs,
        )
        return response.choices[0].message.content

    def extract_tool_calls(self, response: str) -> list[dict]:
        """Extract JSON tool calls from response."""
        # Simple approach: find content between ```json and ```
        start_marker = '```json'
        end_marker = '```'

        tool_calls = []
        start_idx = response.find(start_marker)
        print(f"DEBUG: start_marker '{start_marker}' found at index: {start_idx}")

        if start_idx != -1:
            start_idx += len(start_marker)
            end_idx = response.find(end_marker, start_idx)
            print(f"DEBUG: end_marker '{end_marker}' found at index: {end_idx}")

            if end_idx != -1:
                json_content = response[start_idx:end_idx].strip()
                print(f'DEBUG: Raw extracted content: {json_content!r}')

                # Remove any leading/trailing whitespace and newlines
                json_content = json_content.strip()
                print(f'DEBUG: Stripped content: {json_content!r}')

                try:
                    tool_call = json.loads(json_content)
                    if isinstance(tool_call, dict) and 'tool' in tool_call:
                        tool_calls.append(tool_call)
                        print(f'DEBUG: Successfully extracted tool call: {tool_call}')
                    else:
                        print(f'DEBUG: Parsed object is not a valid tool call: {tool_call}')
                except json.JSONDecodeError as e:
                    print(f'DEBUG: JSON decode error: {e}')
                    print(f'DEBUG: Failed content: {json_content!r}')
                    raise  # Re-raise to be caught by caller

        print(f'DEBUG: Extracted {len(tool_calls)} tool calls')
        return tool_calls


class LocalLLMClient(LLMClient):
    """Local LLM integration (Ollama, etc.)."""

    def __init__(self, base_url: str = 'http://localhost:11434', model: str = 'llama2'):
        try:
            import requests

            self.base_url = base_url
            self.model = model
            self.session = requests.Session()
        except ImportError:
            msg = 'requests package not installed'
            raise ImportError(msg)

    def chat(self, messages: list[dict], **kwargs) -> str:
        # Convert to Ollama format
        prompt = self._messages_to_prompt(messages)

        response = self.session.post(
            f'{self.base_url}/api/generate',
            json={'model': self.model, 'prompt': prompt, 'stream': False},
        )
        response.raise_for_status()
        return response.json()['response']

    def _messages_to_prompt(self, messages: list[dict]) -> str:
        """Convert chat messages to prompt format."""
        prompt_parts = []
        for msg in messages:
            role = msg['role']
            content = msg['content']
            if role == 'system':
                prompt_parts.append(f'System: {content}')
            elif role == 'user':
                prompt_parts.append(f'User: {content}')
            elif role == 'assistant':
                prompt_parts.append(f'Assistant: {content}')
        return '\n\n'.join(prompt_parts)

    def extract_tool_calls(self, response: str) -> list[dict]:
        # Simple JSON extraction for local models
        json_pattern = r'\{.*?"tool".*?\}'
        matches = re.findall(json_pattern, response, re.DOTALL)

        tool_calls = []
        for match in matches:
            try:
                tool_call = json.loads(match)
                tool_calls.append(tool_call)
            except json.JSONDecodeError:
                continue

        return tool_calls


class ToolRegistry:
    """Registry of available tools for the chatbot."""

    def __init__(self):
        self.tools = self._load_tools()

    def _load_tools(self) -> dict[str, dict]:
        """Load available tools from our infrastructure."""
        return {
            'predict_plate_appearance': {
                'description': 'Predict outcomes for a specific plate appearance',
                'parameters': {
                    'game_id': {'type': 'string', 'description': 'Game identifier'},
                    'plate_appearance_id': {
                        'type': 'integer',
                        'description': 'Plate appearance number',
                    },
                },
            },
            'simulate_half_inning': {
                'description': 'Run Monte Carlo simulation for half-inning scenarios',
                'parameters': {
                    'game_id': {'type': 'string', 'description': 'Game identifier'},
                    'inning': {'type': 'integer', 'description': 'Inning number'},
                    'is_bottom': {
                        'type': 'boolean',
                        'description': 'Bottom half of inning',
                    },
                    'simulations': {
                        'type': 'integer',
                        'description': 'Number of simulations',
                        'default': 100,
                    },
                },
            },
            'get_live_odds': {
                'description': 'Get real-time odds for all baseball outcomes',
                'parameters': {'game_id': {'type': 'string', 'description': 'Game identifier'}},
            },
            'analyze_player': {
                'description': 'Analyze player statistics and performance',
                'parameters': {
                    'player_id': {'type': 'string', 'description': 'Player identifier'},
                    'season': {
                        'type': 'integer',
                        'description': 'Season year',
                        'default': 2023,
                    },
                },
            },
            'query_database': {
                'description': 'Execute safe database queries',
                'parameters': {
                    'query_type': {
                        'type': 'string',
                        'enum': ['game_info', 'player_stats', 'team_stats'],
                    },
                    'filters': {'type': 'object', 'description': 'Query filters'},
                },
            },
        }

    def get_tool_info(self, tool_name: str) -> dict | None:
        """Get information about a specific tool."""
        return self.tools.get(tool_name)

    def list_tools(self) -> list[str]:
        """List all available tool names."""
        return list(self.tools.keys())

    def validate_tool_call(self, tool_name: str, parameters: dict) -> bool:
        """Validate that a tool call has correct parameters."""
        tool_info = self.get_tool_info(tool_name)
        if not tool_info:
            return False

        required_params = tool_info.get('parameters', {})
        for param_name, param_info in required_params.items():
            if param_info.get('required', False) and param_name not in parameters:
                return False

        return True


class MockLLMClient(LLMClient):
    """Mock LLM client for testing without API keys."""

    def chat(self, messages: list[dict], **kwargs) -> str:
        """Return mock responses based on query content."""
        last_message = messages[-1]['content'] if messages else ''

        print(f'DEBUG: Mock LLM received: {last_message[:200]}...')

        # Check if this is a synthesis call (contains tool results)
        if 'Tool results:' in last_message or 'tool results' in last_message.lower():
            # Parse the tool results and generate final response
            if 'pa_batter_hit' in last_message:
                return """Based on the prediction results, here's what I found:

**Home Run Probability Analysis:**
- Current batter has a **3.0%** chance of hitting a home run
- **25.0%** chance of getting any hit
- **8.0%** chance of drawing a walk
- **20.0%** chance of striking out
- **32.0%** chance of reaching base safely

These probabilities are based on our trained ML models that consider batter/pitcher matchups, ball/strike counts, and game situation. The models have been trained on 25+ years of MLB data and show good predictive accuracy for these types of outcomes.

Would you like me to analyze a different scenario or provide more details about the model's methodology?"""
            return "I've analyzed the available data and provided insights based on our baseball analytics models."

        # Initial response with tool calls
        if 'home run' in last_message.lower():
            return """Based on your question about home run odds, I should use the prediction tools to get accurate probabilities.

```json
{
  "tool": "predict_plate_appearance",
  "parameters": {
    "game_id": "ALS200107100",
    "plate_appearance_id": 1
  }
}
```

This will give us the specific probabilities for this plate appearance."""

        if 'simulate' in last_message.lower():
            return """To simulate half-inning scenarios, I'll use the Monte Carlo simulation tool.

```json
{
  "tool": "simulate_half_inning",
  "parameters": {
    "game_id": "ALS200107100",
    "inning": 1,
    "is_bottom": false,
    "simulations": 100
  }
}
```

This will run 100 simulations to estimate the probability of different outcomes."""

        return f"I understand you're asking about baseball analytics. Based on your query: '{last_message[:100]}...', I can help analyze game situations, predict outcomes, or run simulations. What specific aspect would you like to explore?"

    def extract_tool_calls(self, response: str) -> list[dict]:
        """Extract tool calls from mock responses."""
        # For mock client, we know the format, so use the same logic as the base class
        # Simple approach: find content between ```json and ```
        start_marker = '```json'
        end_marker = '```'

        tool_calls = []
        start_idx = response.find(start_marker)

        if start_idx != -1:
            start_idx += len(start_marker)
            end_idx = response.find(end_marker, start_idx)

            if end_idx != -1:
                json_content = response[start_idx:end_idx].strip()

                try:
                    tool_call = json.loads(json_content)
                    if isinstance(tool_call, dict) and 'tool' in tool_call:
                        tool_calls.append(tool_call)
                except json.JSONDecodeError:
                    pass

        return tool_calls


class ConversationMemory:
    """Simple conversation memory for context."""

    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self.history = []

    def add_turn(self, user_message: str, assistant_response: str):
        """Add a conversation turn."""
        self.history.append(
            {
                'user': user_message,
                'assistant': assistant_response,
                'timestamp': os.times()[4],  # CPU time
            },
        )

        # Keep only recent turns
        if len(self.history) > self.max_turns:
            self.history = self.history[-self.max_turns :]

    def get_recent_context(self, turns: int = 3) -> str:
        """Get recent conversation context."""
        recent = self.history[-turns:]
        if not recent:
            return ''

        context_parts = []
        for turn in recent:
            context_parts.append(f'User: {turn["user"]}')
            context_parts.append(f'Assistant: {turn["assistant"][:200]}...')  # Truncate

        return '\n'.join(context_parts)


class BaseballQueryAgent:
    """Main baseball chatbot agent."""

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client or self._init_default_llm()
        self.tool_registry = ToolRegistry()
        self.memory = ConversationMemory()
        self.prediction_service = PredictionService(max_connections=5)

    def _init_default_llm(self) -> LLMClient:
        """Initialize default LLM client."""
        print('🔍 Checking LLM configurations...')

        # Try OpenAI first (only if key exists and is not empty)
        api_key = os.environ.get('OPENAI_API_KEY')
        print(f'  OpenAI API key present: {bool(api_key and api_key.strip())}')
        if api_key and api_key.strip():
            try:
                print('  Trying OpenAI client...')
                return OpenAIClient(api_key=api_key)
            except Exception as e:
                print(f'⚠️  OpenAI client failed: {e}')

        # Fall back to local
        ollama_url = os.environ.get('OLLAMA_BASE_URL')
        print(f'  Ollama URL present: {bool(ollama_url)}')
        if ollama_url:
            try:
                print('  Trying local LLM client...')
                return LocalLLMClient()
            except Exception as e:
                print(f'⚠️  Local LLM client failed: {e}')

        # Use mock client for testing
        print('⚠️  Using mock responses for demonstration.')
        return MockLLMClient()

    def _create_system_prompt(self) -> str:
        """Create the system prompt for the LLM."""
        tools_info = []
        for tool_name, tool_info in self.tool_registry.tools.items():
            tools_info.append(f'- {tool_name}: {tool_info["description"]}')

        return f"""You are a baseball analytics expert chatbot. You have access to comprehensive MLB data and machine learning models to provide detailed analysis and predictions.

Available tools:
{chr(10).join(tools_info)}

When users ask questions:
1. Understand their intent (prediction, analysis, information)
2. Use appropriate tools to gather data
3. Provide clear, actionable insights
4. Explain probabilities and uncertainties

For predictions, always explain the model's confidence level and any limitations.

If you need to use tools, format your response with JSON tool calls like:
```json
{{
  "tool": "predict_plate_appearance",
  "parameters": {{
    "game_id": "ALS200107100",
    "plate_appearance_id": 1
  }}
}}
```

Be helpful, accurate, and engaging in your responses."""

    def process_query(self, user_query: str) -> dict[str, Any]:
        """Process a user query and return response."""
        try:
            # Get conversation context
            context = self.memory.get_recent_context()

            # Create messages for LLM
            messages = [
                {'role': 'system', 'content': self._create_system_prompt()},
                {
                    'role': 'user',
                    'content': f'Context: {context}\n\nQuery: {user_query}',
                },
            ]

            # Get LLM response
            llm_response = self.llm_client.chat(messages)

            # Check for tool calls
            tool_calls = self.llm_client.extract_tool_calls(llm_response)

            results = []
            if tool_calls:
                # Execute tools
                for tool_call in tool_calls:
                    tool_name = tool_call.get('tool')
                    parameters = tool_call.get('parameters', {})

                    if self.tool_registry.validate_tool_call(tool_name, parameters):
                        result = self._execute_tool(tool_name, parameters)
                        results.append({'tool': tool_name, 'result': result})
                    else:
                        results.append({'tool': tool_name, 'error': 'Invalid parameters'})

            # Generate final response
            if results:
                # Include tool results in context
                tool_context = f'Tool results: {results}'
                final_messages = [
                    *messages,
                    {'role': 'assistant', 'content': llm_response},
                    {
                        'role': 'user',
                        'content': f'Based on the tool results, provide a comprehensive answer: {tool_context}',
                    },
                ]
                final_response = self.llm_client.chat(final_messages)
            else:
                final_response = llm_response

            # Store in memory
            self.memory.add_turn(user_query, final_response)

            return {
                'response': final_response,
                'tools_used': [r['tool'] for r in results if 'tool' in r],
                'confidence': 0.8,  # Placeholder
            }

        except Exception as e:
            return {
                'response': f'I encountered an error: {e!s}. Please try rephrasing your question.',
                'error': str(e),
            }

    def _execute_tool(self, tool_name: str, parameters: dict) -> Any:
        """Execute a tool with given parameters."""
        print(f'DEBUG: Executing tool {tool_name} with params {parameters}')
        try:
            if tool_name == 'predict_plate_appearance':
                result = self._predict_plate_appearance(parameters)
                print(f'DEBUG: Prediction result: {result}')
                return result
            if tool_name == 'simulate_half_inning':
                return self._simulate_half_inning(parameters)
            if tool_name == 'get_live_odds':
                return self._get_live_odds(parameters)
            if tool_name == 'analyze_player':
                return self._analyze_player(parameters)
            if tool_name == 'query_database':
                return self._query_database(parameters)
            return {'error': f'Tool {tool_name} not implemented'}
        except Exception as e:
            print(f'DEBUG: Tool execution failed: {e}')
            import traceback

            traceback.print_exc()
            return {'error': str(e)}

    def _predict_plate_appearance(self, params: dict) -> dict:
        """Predict plate appearance outcomes."""
        game_id = params.get('game_id', 'ALS200107100')
        pa_id = params.get('plate_appearance_id', 1)

        if not game_id or not pa_id:
            return {'error': 'Missing game_id or plate_appearance_id'}

        try:
            return self.prediction_service.predict_plate_appearance(game_id, int(pa_id))
        except Exception:
            # For mock/demo purposes, return sample predictions
            return {
                'game_id': game_id,
                'plate_appearance_id': pa_id,
                'predictions': {
                    'pa_batter_hit': 0.250,
                    'pa_batter_walk': 0.080,
                    'pa_batter_strikeout': 0.200,
                    'pa_batter_home_run': 0.030,
                    'pa_batter_reach_base': 0.320,
                    'pa_batter_extra_base_hit': 0.070,
                },
                'note': 'Mock predictions for demonstration',
            }

    def _simulate_half_inning(self, params: dict) -> dict:
        """Run half-inning simulation."""
        game_state = {
            'season': 2023,
            'inning': params.get('inning', 1),
            'is_bottom_inning': params.get('is_bottom', False),
            'outs_before': 0,
            'start_bases': 0,
            'balls': 0,
            'strikes': 0,
            'home_score_diff': 0,
            'batter_hand': 'R',
            'pitcher_hand': 'R',
        }

        return self.prediction_service.simulate_half_inning_fast(
            game_state,
            num_simulations=params.get('simulations', 100),
        )

    def _get_live_odds(self, params: dict) -> dict:
        """Get live odds (placeholder for now)."""
        return {
            'message': 'Live odds feature coming soon',
            'game_id': params.get('game_id'),
        }

    def _analyze_player(self, params: dict) -> dict:
        """Analyze player performance."""
        return {
            'message': 'Player analysis feature coming soon',
            'player_id': params.get('player_id'),
        }

    def _query_database(self, params: dict) -> dict:
        """Execute safe database queries."""
        query_type = params.get('query_type')
        filters = params.get('filters', {})

        return {'message': f'Safe query for {query_type}', 'filters': filters}


def main():
    """CLI interface for testing the chatbot."""
    agent = BaseballQueryAgent()

    print("🤖 Baseball Chatbot - Type 'quit' to exit")
    print('=' * 50)

    while True:
        try:
            user_input = input('\nYou: ').strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                break

            if not user_input:
                continue

            print('Thinking...')
            result = agent.process_query(user_input)

            print(f'🤖 Bot: {result["response"]}')

            if result.get('tools_used'):
                print(f'🔧 Tools used: {", ".join(result["tools_used"])}')

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f'Error: {e}')


if __name__ == '__main__':
    main()
