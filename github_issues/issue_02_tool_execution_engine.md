## Issue #2: 🔧 Tool Execution Engine with Safety Validation

### Description
Build a secure tool execution engine that can safely run all 21+ Python scripts, execute database queries, and manage external API calls while maintaining strict security controls.

### Technical Requirements
- **Script Execution**: Safe execution of Python scripts with argument validation
- **Database Queries**: Parameterized SQL with row limits and execution timeouts
- **API Calls**: Controlled external API access (MLB Stats API)
- **Resource Limits**: CPU, memory, and execution time constraints
- **Audit Logging**: Complete logging of all tool executions

### Implementation Details
```python
class SafeToolExecutor:
    def __init__(self):
        self.script_allowlist = {
            'predict_plate_appearance.py': {
                'timeout': 10,
                'args_schema': {
                    'game_id': str,
                    'plate_appearance_id': int,
                    'targets': Optional[List[str]]
                }
            },
            'simulate_half_inning.py': {
                'timeout': 30,
                'args_schema': {
                    'game_id': str,
                    'inning': int,
                    'is_bottom': bool,
                    'simulations': int
                }
            },
            # ... all 21 scripts with safety configs
        }

    def execute_script(self, script_name: str, args: Dict) -> Any:
        # Validate script is allowed
        # Validate arguments against schema
        # Execute with timeout and resource limits
        # Return structured results
        pass
```

### Security Controls
- **Input Validation**: Strict argument validation using Pydantic schemas
- **Execution Sandbox**: Subprocess isolation with resource limits
- **Network Controls**: Whitelist of allowed external endpoints
- **Database Safety**: Read-only connections, parameterized queries
- **Rate Limiting**: Prevent abuse with request throttling

### Database Query Safety
```python
class SafeQueryExecutor:
    def __init__(self):
        self.allowed_patterns = {
            r'SELECT .* FROM core\.games WHERE game_id = %s': {'max_rows': 1},
            r'SELECT .* FROM features\.plate_appearance_examples LIMIT %s': {'max_rows': 1000},
            # Pre-approved query patterns
        }

    def execute_query(self, query: str, params: Dict) -> List[Dict]:
        # Validate query against allowlist
        # Check resource limits
        # Execute with connection pooling
        # Return results
        pass
```

### Acceptance Criteria
- [ ] Can safely execute all 21+ Python scripts
- [ ] Validates all input arguments against schemas
- [ ] Enforces execution timeouts and resource limits
- [ ] Provides structured error handling and logging
- [ ] Supports batch execution for performance
- [ ] Implements circuit breaker pattern for failures

### Dependencies
- #1 (Core LLM Integration) - provides tool call requests

### Estimated Effort
- **Script Executor**: 2-3 days (subprocess management, validation)
- **Database Layer**: 1-2 days (query validation, connection pooling)
- **Security Controls**: 1-2 days (rate limiting, audit logging)
- **Testing**: 1-2 days (security testing, edge cases)

### Files to Create/Modify
- `scripts/tool_executor.py` - Main execution engine
- `scripts/query_validator.py` - Database query safety
- `scripts/script_schemas.py` - Argument validation schemas
- `scripts/audit_logger.py` - Execution logging
- `tests/test_tool_executor.py` - Security and functionality tests

### Related Issues
- #1 (Core LLM Integration)
- #4 (Security Architecture)
- #8 (Testing Framework)

**Labels**: enhancement, security, infrastructure, tools, priority:high