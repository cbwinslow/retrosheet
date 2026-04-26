# Architecture

**Purpose**: This document defines the target architecture for the baseball data platform. It describes the data flow, component responsibilities, and integration patterns.

---

## Architectural Principles

1. **Layered Architecture**: Clear separation between raw, staging, core, bridge, features, models, serving, and interfaces
2. **Source Adapter Pattern**: Unified interface for all data sources (Retrosheet, MLB, ESPN, Statcast, etc.)
3. **Immutable Raw Layer**: Source data preserved exactly as received
4. **Idempotent Operations**: All ingestion safe to re-run
5. **Checkpoint-Driven**: Pipeline state tracked for resume capability
6. **CLI-First**: All operations exposed through unified `baseball` CLI
7. **ML-Ready**: Features and models designed for training and inference

---

## System Context

```
┌─────────────────────────────────────────────────────────────┐
│                        Interfaces                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │   CLI    │  │  Future  │  │  Future  │  │  Future  │     │
│  │ baseball │  │   API    │  │ WebSocket│  │ Chatbot  │     │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘     │
└───────┼─────────────┼─────────────┼─────────────┼─────────────┘
        │             │             │             │
        └─────────────┴─────────────┴─────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                         Serving                             │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │  Predictions     │  │  Read Models     │                 │
│  │  (low-latency)   │  │  (denormalized)  │                 │
│  └──────────────────┘  └──────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                         Models                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ Registry │  │ Training │  │Inference │  │ Backtest │     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                        Features                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │  Run Exp │  │  Win Exp │  │  Leverage│  │  Matchup │     │
│  │  State   │  │  State   │  │  Index   │  │  Features│     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                         Bridge                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │  Player  │  │   Team   │  │   Game   │  │ Confidence│    │
│  │  Xref    │  │   Xref   │  │   Xref   │  │  Scoring │     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                          Core                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │  Games   │  │  Events  │  │  Players │  │   Teams  │     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │   Parks  │  │  Umpires │  │   Live   │  │  Live    │     │
│  │          │  │          │  │  Games   │  │  Events  │     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                       Staging                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │Staging   │  │Staging   │  │Staging   │  │Staging   │     │
│  │Retro     │  │MLB       │  │ESPN      │  │Statcast  │     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                         Raw                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │  Retro   │  │   MLB    │  │   ESPN   │  │Statcast  │     │
│  │ Archives │  │ Live Feed│  │  Scores  │  │ Pitches  │     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Historical Ingestion Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Retrosheet │────▶│    Raw      │────▶│   Staging   │────▶│    Core     │
│   Website   │     │  Archives   │     │   Events    │     │  Canonical  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                                  │
                                                                  ▼
                                                           ┌─────────────┐
                                                           │   Bridge    │
                                                           │    Xref     │
                                                           └─────────────┘
```

### Live Ingestion Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   MLB API   │────▶│  Raw Live   │────▶│   Core      │────▶│  Features   │
│  Live Feed  │     │  Snapshots  │     │  Live State │     │  Live State │
└─────────────┘     └─────────────┘     └─────────────┘     └──────┬──────┘
                                                                     │
                                                                     ▼
                                                              ┌─────────────┐
                                                              │   Models    │
                                                              │  Predict    │
                                                              └──────┬──────┘
                                                                     │
                                                                     ▼
                                                              ┌─────────────┐
                                                              │   Serving   │
                                                              │ Predictions │
                                                              └─────────────┘
```

### Enrichment Flow

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│   ESPN      │   │  Statcast   │   │  FanGraphs  │   │   Weather   │
│  Scores     │   │  Pitches    │   │   Stats     │   │   Data      │
└──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
       │                 │                 │                 │
       └─────────────────┴─────────────────┴─────────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │    Core     │
                    │   Enriched  │
                    └─────────────┘
```

---

## Component Details

### 1. Raw Layer

**Responsibility**: Preserve source data exactly as received

**Tables**:
- `raw_retrosheet.event_files` — Chadwick CSV extracts
- `raw_retrosheet.game_files` — Chadwick game extracts
- `raw_mlb.live_feed_snapshots` — JSONB MLB API responses
- `raw_mlb.schedule_snapshots` — Schedule API responses
- `raw_espn.game_snapshots` — ESPN scoreboard JSON
- `raw_statcast.pitch_data` — Statcast pitch-level CSV

**Key Patterns**:
- Checksum-based deduplication
- Source-preserved payloads
- Immutable (no updates, only inserts)
- Timestamped with ingest time

### 2. Staging Layer

**Responsibility**: Source-specific cleaned tables for deterministic transformation

**Tables**:
- `stg_retrosheet.events` — Parsed Retrosheet events
- `stg_retrosheet.games` — Parsed Retrosheet games
- `stg_mlb.live_events` — Flattened MLB live events
- `stg_mlb.live_games` — Flattened MLB live games

**Key Patterns**:
- Type-casted columns
- Standardized naming (snake_case)
- Null handling
- Source-specific business rules applied

### 3. Core Layer

**Responsibility**: Canonical baseball entities and event-state representations

**Historical Tables**:
- `core.teams` — Team entities (one row per team-season)
- `core.parks` — Ballpark entities
- `core.players` — Player entities
- `core.games` — Game entities
- `core.events` — Play-by-play events
- `core.plate_appearances` — PA-level aggregations

**Live Tables**:
- `core.live_games` — Current game state
- `core.live_events` — Live event stream

**Key Patterns**:
- Surrogate keys (team_id, player_id, game_id)
- Natural keys preserved (retrosheet_id, mlb_id)
- Temporal validity (valid_from/valid_to)
- Foreign key constraints
- CHECK constraints for data quality

### 4. Bridge Layer

**Responsibility**: Cross-source entity resolution and xref logic

**Tables**:
- `bridge.player_xref` — Player ID mappings
- `bridge.team_xref` — Team ID mappings
- `bridge.game_xref` — Game ID mappings
- `bridge.park_xref` — Park ID mappings

**Columns**:
- `source_system` — e.g., 'retrosheet', 'mlb', 'espn', 'statcast'
- `source_id` — ID in source system
- `canonical_id` — ID in core layer
- `confidence_score` — 0.0 to 1.0
- `match_type` — 'exact', 'fuzzy', 'manual'
- `last_verified_at` — Timestamp

**Key Patterns**:
- Confidence scoring
- Manual override capability
- Audit trail of matches
- Many-to-many relationships supported

### 5. Features Layer

**Responsibility**: Sabermetric and ML-ready feature tables

**Tables**:
- `features.run_expectancy_state` — RE by base-out state
- `features.win_expectancy_state` — WE by inning/score/differential
- `features.leverage_index_state` — LI by base-out/inning/score
- `features.matchup_features` — Batter-pitcher matchup
- `features.rolling_form` — 7/14/30 day rolling stats
- `features.bullpen_usage` — Bullpen fatigue metrics
- `features.live_game_state` — Current game state features

**Key Patterns**:
- Pre-computed for fast inference
- Versioned feature definitions
- Feature lineage tracking
- Online vs offline feature distinction

### 6. Models Layer

**Responsibility**: Model registry, training metadata, training data definitions

**Tables**:
- `models.registry` — Model definitions
- `models.training_runs` — Training run history
- `models.artifacts` — Model binaries metadata
- `models.features_used` — Feature lineage per model

**Key Patterns**:
- Semantic versioning for models
- Training configuration stored as JSONB
- Artifact storage references (S3/local path)
- Training metrics captured

### 7. Serving Layer

**Responsibility**: Low-latency outputs, denormalized read models, predictions

**Tables**:
- `serving.game_predictions` — Game-level predictions
- `serving.pa_predictions` — PA-level predictions
- `serving.pitch_predictions` — Pitch-level predictions
- `serving.current_standings` — Denormalized standings
- `serving.player_leaderboards` — Pre-computed leaderboards

**Key Patterns**:
- Optimized for read performance
- Minimal joins required
- Caching-friendly structure
- TTL for transient predictions

### 8. Interfaces Layer

**Responsibility**: CLI, API, WebSocket, Chatbot interfaces

**Components**:
- `baseball.cli` — Typer-based CLI
- `baseball.app` — FastAPI app (future)
- `baseball.ws` — WebSocket handler (future)
- `baseball.chatbot` — NL interface (future)

**CLI Command Groups**:
- `baseball doctor` — Health checks
- `baseball status` — Pipeline status
- `baseball retrosheet` — Historical ingestion
- `baseball mlb` — Live ingestion
- `baseball espn` — ESPN enrichment
- `baseball statcast` — Statcast enrichment
- `baseball bridge` — Xref management
- `baseball features` — Feature building
- `baseball models` — Model training/inference
- `baseball pipeline` — Pipeline orchestration

---

## Integration Patterns

### Source Adapter Pattern

All data sources implement `BaseSource`:

```python
class BaseSource(ABC):
    @abstractmethod
    def download(self, config: DownloadConfig) -> SourceResult:
        """Download data from source to local storage."""
        pass
    
    @abstractmethod
    def ingest(self, source_path: Path) -> IngestResult:
        """Transform and load to database."""
        pass
    
    @abstractmethod
    def validate(self, ingest_result: IngestResult) -> ValidationResult:
        """Validate ingested data."""
        pass
```

### Pipeline Checkpoint Pattern

All long-running operations support checkpoints:

```python
@checkpointed(table="pipeline_checkpoints")
def ingest_mlb_games(date: str, resume: bool = True):
    checkpoint = load_checkpoint("mlb_ingest", date)
    for game in get_games(date, after=checkpoint.last_game_pk):
        ingest_game(game)
        save_checkpoint("mlb_ingest", date, game.game_pk)
```

### Feature Store Pattern

Features support both online (live) and offline (historical) contexts:

```python
class FeatureView:
    def get_online_features(self, game_pk: int) -> Dict[str, float]:
        """Low-latency fetch for live inference."""
        pass
    
    def get_offline_features(self, date_range: DateRange) -> DataFrame:
        """Batch fetch for training."""
        pass
```

---

## Database Design

### Schema Organization

```sql
-- Admin schema for pipeline control
CREATE SCHEMA admin;

-- Raw schemas (one per source)
CREATE SCHEMA raw_retrosheet;
CREATE SCHEMA raw_mlb;
CREATE SCHEMA raw_espn;
CREATE SCHEMA raw_statcast;

-- Processing schemas
CREATE SCHEMA staging;
CREATE SCHEMA core;
CREATE SCHEMA bridge;
CREATE SCHEMA features;
CREATE SCHEMA models;
CREATE SCHEMA serving;

-- Quality schema
CREATE SCHEMA quality;
```

### Key Conventions

- **Primary Keys**: Surrogate UUIDs or SERIAL, never source IDs
- **Natural Keys**: Preserved as columns (e.g., `retrosheet_id`, `mlb_id`)
- **Foreign Keys**: Enforced at database level
- **Timestamps**: All tables have `created_at`, `updated_at`
- **Soft Deletes**: `deleted_at` timestamp for logical deletes
- **Audit**: `ingested_by`, `ingested_at` for tracking

### Indexing Strategy

- **Primary keys**: B-tree unique
- **Foreign keys**: B-tree for join performance
- **Date ranges**: B-tree for time-series queries
- **Text search**: GIN indexes for JSONB/text
- **Geographic**: PostGIS indexes for park locations

---

## Performance Considerations

### Ingestion Performance

- Batch inserts (1000+ rows per transaction)
- COPY for bulk loads
- Parallel processing per source
- Connection pooling

### Query Performance

- Materialized views for read-heavy workloads
- Denormalized serving tables
- Partitioning by date (live tables)
- Columnar storage for analytics (optional TimescaleDB)

### Real-Time Considerations

- WebSocket for sub-second updates
- In-memory caching for hot data
- Incremental feature computation
- Async processing pipeline

---

## Security Considerations

### Data Protection

- No PII in baseball data (generally)
- API keys in environment variables
- Database credentials in secrets manager
- Audit logging for all data modifications

### Access Control

- Read-only role for analytics
- Write role for ingestion
- Admin role for DDL
- Row-level security for multi-tenant (future)

---

## Deployment Architecture

### Development

```
Local Machine
├── PostgreSQL (Docker)
├── Python venv
└── Local data cache
```

### Production (Future)

```
Cloud Infrastructure
├── PostgreSQL (managed)
├── API servers (auto-scaled)
├── Ingestion workers (scheduled)
├── Model training (GPU instances)
└── Object storage (artifacts)
```

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-26 | Migration Agent | Initial architecture specification |
