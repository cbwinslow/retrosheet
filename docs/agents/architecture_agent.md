# Architecture Agent Guidance

**Role**: System design, data flow, integration patterns, and high-level architecture decisions.

---

## Scope

You are responsible for:
- Overall system architecture and component design
- Data flow patterns between layers (raw → core → features → models → serving)
- Source adapter interface design
- Integration patterns (bridge, xref, enrichment)
- Performance architecture (caching, materialized views, partitioning)
- Future extensibility (WebSocket, API, chatbot interfaces)

---

## Key Documents

| Document | When to Use |
|----------|-------------|
| `docs/architecture.md` | Reference for target architecture |
| `docs/migration_plan.md` | Migration phases and goals |
| `docs/keys_and_grains.md` | Entity relationships and keys |

---

## Architecture Principles

1. **Layer Isolation**: Each layer has clear responsibilities; no cross-layer dependencies
2. **Adapter Pattern**: All sources implement `BaseSource` interface
3. **Immutable Raw**: Source data never modified, only appended
4. **Idempotent Operations**: All transforms safe to re-run
5. **Checkpoint-Driven**: Long operations support resume
6. **CLI-First**: All functionality exposed through `baseball` CLI

---

## Data Flow Patterns

### Historical Ingestion

```
Source → Raw (immutable) → Staging (cleaned) → Core (canonical) → Bridge (xref) → Features
```

### Live Ingestion

```
MLB API → Raw Snapshots → Core Live → Features Live → Models → Serving Predictions
```

### Enrichment

```
ESPN/Statcast → Raw → Staging → Join to Core via Bridge → Enriched Core
```

---

## Component Design Guidelines

### Source Adapters

All adapters must implement:

```python
class BaseSource(ABC):
    @abstractmethod
    def download(self, config: DownloadConfig) -> SourceResult: ...
    
    @abstractmethod  
    def ingest(self, source_path: Path) -> IngestResult: ...
    
    @abstractmethod
    def validate(self, ingest_result: IngestResult) -> ValidationResult: ...
```

### Service Layer

Services encapsulate business logic:

```python
class BridgeService:
    def resolve_player(self, source_system: str, source_id: str) -> UUID: ...
    def validate_xref(self, xref_id: UUID) -> ValidationResult: ...
```

---

## Integration Patterns

### Bridge/Xref Resolution

- Always use `bridge.player_xref` for cross-source joins
- Include confidence scores for fuzzy matches
- Support manual overrides with audit trail

### Feature Store

- Pre-compute features for training (offline)
- Incrementally update features for live (online)
- Version feature definitions with models

### Model Registry

- Semantic versioning: `win_probability:v1.2.3`
- Store training config as JSONB
- Track artifact location (S3/local path)

---

## Performance Patterns

### Read Optimization

- Materialized views for read-heavy workloads
- Denormalized serving tables
- Proper indexing on foreign keys
- Partitioning by date for time-series

### Write Optimization

- Batch inserts (1000+ rows)
- COPY for bulk loads
- Parallel processing per source
- Connection pooling

---

## Decision Log

When making architectural decisions, update this section:

| Date | Decision | Rationale | Status |
|------|----------|-----------|--------|
| 2026-04-26 | Typer for CLI | Type-safe, modern, testable | Decided |
| 2026-04-26 | Layered SQL folders | Clear separation, migration path | Decided |
| 2026-04-26 | Pydantic for settings | Validation, env var support | Decided |

---

## Review Checklist

Before submitting architecture changes:

- [ ] Does the design follow the layered architecture?
- [ ] Are all sources using the adapter pattern?
- [ ] Is the raw layer immutable?
- [ ] Are operations idempotent?
- [ ] Is there a clear upgrade/migration path?
- [ ] Have performance implications been considered?
- [ ] Is the design documented in `docs/architecture.md`?

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-26 | Migration Agent | Initial architecture agent guidance |
