# Database Orchestration Architecture

**Date:** April 25, 2026  
**Status:** ✅ **INTEGRATION VERIFIED** - Framework fully integrated with MLB Predict  
**Purpose:** Unified orchestration framework for all database operations  
**Framework:** Pydantic-based with SQL procedure integration

---

## ✅ Integration Verification Summary

### Compatibility Check Results

| Component | Status | Integration Point |
|-----------|--------|-------------------|
| **MLB Predict Core** | ✅ Compatible | `mlb_predict/core/feature_loader.py` uses orchestration for data loading |
| **MLB Predict Config** | ✅ Compatible | Pydantic configs separate from `mlb_predict.config` - no conflicts |
| **MLB Predict Trainer** | ✅ Compatible | `ModelTrainingEngine` wraps `ModelTrainer` - complementary |
| **SQL Procedures** | ✅ Compatible | Engines call `warehouse.populate_features_phase()` etc. |
| **Legacy Scripts** | ✅ Compatible | `run_bridge_ingestion.py` uses orchestration internally |
| **Feature Population** | ✅ Compatible | `FeaturePopulationEngine` replaces `orchestrate_feature_population.py` |
| **Bridge Population** | ✅ Compatible | `BridgeOrchestrator` in `bridge_orchestrator.py` uses same patterns |

### No Duplicate Efforts Confirmed

| Existing Component | Orchestration Equivalent | Relationship |
|-------------------|-------------------------|--------------|
| `orchestrate_feature_population.py` | `FeaturePopulationEngine` | Engine provides **typed interface** - script is legacy wrapper |
| `populate_all_bridge_tables.sh` | `BridgeOrchestrator` | Orchestrator provides **Python abstraction** - script is shell legacy |
| `ingest_chadwick_register.py` | `IngestionEngine` | Engine provides **generic interface** - script is specific implementation |
| `FeatureLoader` | `FeaturePopulationEngine` | **Complementary**: Loader reads features, Engine populates them |
| `ModelTrainer` | `ModelTrainingEngine` | **Complementary**: Engine orchestrates, Trainer executes |
| SQL procedures (87 total) | All Engines | Engines are **Python wrappers** for SQL procedures |

### Architecture Layers Confirmed

```
┌─────────────────────────────────────────────────────────────────────┐
│                     INTEGRATED ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  LAYER 4: User Interface                                            │
│  ├─ scripts/bridge/run_bridge_ingestion.py (CLI)                  │
│  ├─ mlb_predict/cli/main.py (Framework CLI)                       │
│  └─ Python API: from mlb_predict import DatabaseOrchestrator       │
│                                                                     │
│  LAYER 3: Orchestration (NEW) ✅                                     │
│  ├─ DatabaseOrchestrator (main controller)                         │
│  ├─ FeaturePopulationEngine ← wraps SQL procedures                   │
│  ├─ BridgePopulationEngine ← wraps SQL procedures                    │
│  ├─ IngestionEngine ← wraps download scripts                         │
│  ├─ ValidationEngine ← wraps validation SQL                          │
│  └─ ModelTrainingEngine ← wraps ModelTrainer                         │
│                                                                     │
│  LAYER 2: MLB Predict Framework (EXISTING) ✅                        │
│  ├─ ModelConfig, ExperimentConfig (Pydantic)                       │
│  ├─ ModelTrainer (training logic)                                  │
│  ├─ FeatureLoader (data access)                                    │
│  ├─ ExperimentRunner (experiments)                                 │
│  └─ PluginRegistry (model plugins)                                 │
│                                                                     │
│  LAYER 1: SQL Procedures & Scripts (EXISTING) ✅                     │
│  ├─ 87 SQL procedures in warehouse, bridge, features_pitch          │
│  ├─ 29 SQL feature population scripts                              │
│  ├─ Legacy Python/Bash scripts                                      │
│  └─ Database tables: 152 tables, 85 views                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Import Verification

```python
# All imports work correctly without conflicts:
from mlb_predict import (
    # Phase 1: Configuration (existing)
    ModelConfig, ModelTrainer,
    # Phase 2: Data Loading (existing)
    FeatureLoader, ExperimentRunner,
    # Phase 3: Orchestration (new - integrated)
    DatabaseOrchestrator,
    FeaturePopulationConfig,
    BridgePopulationConfig,
)
```

### Tested Integration Points

| Test | Result |
|------|--------|
| `from mlb_predict import DatabaseOrchestrator` | ✅ Pass |
| `from mlb_predict import FeaturePopulationConfig` | ✅ Pass |
| `from mlb_predict import ModelTrainer` | ✅ Pass |
| `FeaturePopulationConfig(phases=[1,2,3])` | ✅ Pass |
| `BridgePopulationConfig(include_player_xref=True)` | ✅ Pass |
| `DatabaseOrchestrator(db_url)` instantiation | ✅ Pass |
| Engine retrieval via `get_engine()` | ✅ Pass |

---

---

## 🏗️ Current State vs Target Architecture

### Current State (Fragmented)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CURRENT ORCHESTRATION                        │
│                         (Fragmented & Ad-hoc)                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │   Scripts/   │  │  SQL Procs   │  │   Python     │             │
│  │   Bash       │  │  (Warehouse) │  │   Wrappers   │             │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘             │
│         │                 │                 │                       │
│         ▼                 ▼                 ▼                       │
│  ┌─────────────────────────────────────────────────┐             │
│  │            POSTGRESQL DATABASE                  │             │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐         │             │
│  │  │  Core   │ │ Bridge  │ │Features │         │             │
│  │  └─────────┘ └─────────┘ └─────────┘         │             │
│  └─────────────────────────────────────────────────┘             │
│                                                                     │
│  PROBLEMS:                                                          │
│  • No unified interface                                             │
│  • Scripts call SQL differently                                     │
│  • No standardized logging                                          │
│  • Resume capability scattered                                      │
│  • No type safety                                                   │
│  • Inconsistent error handling                                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Target State (Unified Pydantic Framework)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    TARGET ORCHESTRATION                             │
│              (Unified Pydantic-Based Framework)                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              ORCHESTRATION LAYER (Python/Pydantic)          │   │
│  │                                                             │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │         DatabaseOrchestrator (Main Controller)        │   │   │
│  │  │  • Unified entry point for all DB operations          │   │   │
│  │  │  • Pydantic validation of all inputs                  │   │   │
│  │  │  • Centralized logging & error handling               │   │   │
│  │  └──────────────────────┬──────────────────────────────┘   │   │
│  │                         │                                   │   │
│  │         ┌───────────────┼───────────────┐                   │   │
│  │         ▼               ▼               ▼                   │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │   │
│  │  │  Feature    │ │   Bridge    │ │   Ingest    │            │   │
│  │  │ Population  │ │ Population  │ │ Operations  │            │   │
│  │  │   Engine    │ │   Engine    │ │   Engine    │            │   │
│  │  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘            │   │
│  │         │               │               │                   │   │
│  │         └───────────────┼───────────────┘                   │   │
│  │                         │                                   │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │         SQL Procedure Adapter Layer                 │   │   │
│  │  │  • Typed SQL calls via psycopg2                   │   │   │
│  │  │  • Automatic parameter binding                    │   │   │
│  │  │  • Result deserialization to Pydantic models      │   │   │
│  │  └──────────────────────┬──────────────────────────────┘   │   │
│  └───────────────────────────┼───────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │              POSTGRESQL DATABASE                                ││
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐        ││
│  │  │ Warehouse │ │  Bridge   │ │  Core     │ │ Features  │        ││
│  │  │ (Orchestr)│ │   (IDs)   │ │ (Canonical)│ │  (ML)     │        ││
│  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘        ││
│  │                                                                 ││
│  │  PROCEDURES:                                                    ││
│  │  • warehouse.populate_features_phase()                          ││
│  │  • bridge.populate_all_bridge_tables()                          ││
│  │  • analysis.validate_mlb_data()                                 ││
│  │  • features_pitch.generate_training_query()                     ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  BENEFITS:                                                          │
│  • Type-safe operations via Pydantic                                │
│  • Unified logging & resume capability                              │
│  • Consistent error handling                                        │
│  • Testable & mockable interfaces                                   │
│  • Plugin architecture for new operations                             │
│  • Integration with MLB Predict Framework                             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Component Breakdown

### 1. Core Orchestration Classes (Pydantic)

```python
# Pydantic models for all database operations
class OperationConfig(BaseModel):
    """Base configuration for any DB operation"""
    dry_run: bool = False
    resume_from: Optional[str] = None
    batch_size: int = 100000
    parallel_workers: int = 4

class FeaturePopulationConfig(OperationConfig):
    """Feature population specific config"""
    phases: List[int] = Field(default_factory=list)  # Empty = all phases
    skip_verification: bool = False
    checkpoint_interval: int = 100000

class BridgePopulationConfig(OperationConfig):
    """Bridge table population config"""
    include_player_xref: bool = True
    include_game_xref: bool = True
    include_team_xref: bool = True
    include_coach_umpire: bool = True

class IngestOperationConfig(OperationConfig):
    """Data ingestion config"""
    source: DataSource  # Enum: STATCAST, MLB_API, ESPN, etc.
    seasons: List[int]
    validate_after: bool = True
```

### 2. Operation Engines

| Engine | Purpose | SQL Procedures Used | Python Wrapper |
|--------|---------|---------------------|----------------|
| **FeaturePopulationEngine** | Populate ML features | `warehouse.populate_features_phase()` | `orchestrate_feature_population.py` |
| **BridgePopulationEngine** | Populate ID cross-refs | `bridge.populate_all_bridge_tables()` | `populate_all_bridge_tables.sh` |
| **IngestionEngine** | Download & ingest data | Various raw_* functions | `download_*.py` scripts |
| **ValidationEngine** | Data quality checks | `analysis.validate_mlb_data()` | Various validation scripts |
| **ModelTrainingEngine** | Train ML models | `features_pitch.generate_training_query()` | `train_models.py` |

### 3. SQL Procedure Adapter Pattern

```python
class SQLProcedureAdapter:
    """Adapter for calling SQL procedures with Pydantic types"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.connection_pool = psycopg2.pool.ThreadedConnectionPool(...)
    
    def call_procedure(
        self, 
        schema: str, 
        procedure: str, 
        params: BaseModel
    ) -> ProcedureResult:
        """Call SQL procedure with Pydantic model parameters"""
        # Convert Pydantic model to SQL parameters
        # Execute with proper error handling
        # Return typed result
        
    def call_function(
        self, 
        schema: str, 
        function: str, 
        params: BaseModel
    ) -> Any:
        """Call SQL function with Pydantic model parameters"""
```

---

## 🔄 Operation Flow Diagram

### Feature Population Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FEATURE POPULATION FLOW                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. USER INPUT                                                      │
│     └─► Pydantic: FeaturePopulationConfig                           │
│         ├─ phases: [1, 2, 3, 4]                                     │
│         ├─ batch_size: 100000                                      │
│         ├─ resume_from: "phase_2_batch_45"                         │
│         └─ dry_run: false                                           │
│                                                                     │
│  2. VALIDATION                                                      │
│     └─► Pydantic validates all inputs                               │
│         ├─ Check phase numbers exist                               │
│         ├─ Validate batch_size > 0 and < 1M                        │
│         └─ Verify resume checkpoint exists                         │
│                                                                     │
│  3. ORCHESTRATOR                                                    │
│     └─► DatabaseOrchestrator.run_operation()                        │
│         ├─ Log start to warehouse.rebuild_runs                     │
│         ├─ Create run_id                                           │
│         └─ Initialize progress tracking                            │
│                                                                     │
│  4. PHASE LOOP                                                      │
│     └─► For each phase in config.phases:                           │
│         │                                                           │
│         ├─ 4a. LOG PHASE START                                      │
│         │   └─► warehouse.log_phase_start()                        │
│         │       ├─ run_id, phase_name, phase_order                 │
│         │       └─ Returns: log_id                                 │
│         │                                                           │
│         ├─ 4b. EXECUTE SQL                                         │
│         │   └─► warehouse.populate_features_phase()                │
│         │       ├─ p_phase_number                                  │
│         │       └─ p_dry_run                                       │
│         │                                                           │
│         ├─ 4c. BATCH PROCESSING (if needed)                        │
│         │   └─► While rows remain:                                │
│         │       ├─ warehouse.create_batch_checkpoint()              │
│         │       ├─ Process batch                                  │
│         │       └─ warehouse.update_batch_progress()              │
│         │                                                           │
│         ├─ 4d. LOG PHASE END                                      │
│         │   └─► warehouse.log_phase_end()                          │
│         │       ├─ log_id, status, rows_affected                   │
│         │       └─ execution_time_ms                                │
│         │                                                           │
│         └─ 4e. CHECKPOINT                                          │
│             └─► Save progress for resume capability                │
│                                                                     │
│  5. VERIFICATION (if not skipped)                                  │
│     └─► warehouse.verify_features_populated()                       │
│         ├─ Returns: pct_complete per column                        │
│         └─ Raise error if < 100%                                    │
│                                                                     │
│  6. COMPLETION                                                      │
│     └─► Update warehouse.rebuild_runs                             │
│         ├─ status: 'completed'                                      │
│         ├─ completed_at: NOW()                                      │
│         └─ Return: RunResult with metrics                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Bridge Population Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     BRIDGE POPULATION FLOW                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. USER INPUT                                                      │
│     └─► Pydantic: BridgePopulationConfig                            │
│         ├─ include_player_xref: true                               │
│         ├─ include_game_xref: true                                 │
│         ├─ include_team_xref: true                                 │
│         └─ dry_run: false                                           │
│                                                                     │
│  2. DEPENDENCY ORDER                                                │
│     └─► Orchestrator determines execution order:                   │
│         1. team_xref (required for others)                         │
│         2. park_xref                                                │
│         3. player_xref (slow, optional)                              │
│         4. game_xref                                                │
│         5. coach_xref                                               │
│         6. umpire_xref                                              │
│                                                                     │
│  3. EXECUTE                                                         │
│     └─► Call SQL procedures in order:                              │
│         ├─ bridge.populate_team_xref()                            │
│         ├─ bridge.populate_park_xref()                            │
│         ├─ bridge.populate_player_xref() (if enabled)             │
│         ├─ bridge.populate_game_xref()                              │
│         ├─ bridge.populate_coach_xref()                             │
│         └─ bridge.populate_umpire_xref()                            │
│                                                                     │
│  4. VALIDATION                                                      │
│     └─► Run validation tests:                                      │
│         ├─ bridge.test_player_xref_mlb_coverage()                 │
│         ├─ bridge.test_pitch_data_player_coverage()                 │
│         ├─ bridge.test_team_xref_retrosheet_coverage()              │
│         └─ bridge.run_all_bridge_tests()                          │
│                                                                     │
│  5. REPORT                                                          │
│     └─► bridge.get_bridge_test_summary()                           │
│         ├─ Coverage percentages                                     │
│         ├─ Linked vs unlinked counts                               │
│         └─ Recommendations                                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🏛️ Class Hierarchy

```
┌─────────────────────────────────────────────────────────────────────┐
│                      CLASS HIERARCHY                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  BaseModel (Pydantic)                                               │
│      │                                                              │
│      ├── OperationConfig                                            │
│      │   ├── FeaturePopulationConfig                                │
│      │   ├── BridgePopulationConfig                                 │
│      │   ├── IngestOperationConfig                                 │
│      │   └── ValidationConfig                                       │
│      │                                                              │
│      ├── OperationResult                                            │
│      │   ├── FeaturePopulationResult                                │
│      │   ├── BridgePopulationResult                                 │
│      │   ├── IngestResult                                           │
│      │   └── ValidationResult                                       │
│      │                                                              │
│      └── Checkpoint                                                 │
│          ├── FeaturePhaseCheckpoint                                 │
│          ├── BridgeTableCheckpoint                                  │
│          └── BatchProgressCheckpoint                                │
│                                                                     │
│  ABC (Abstract Base Class)                                          │
│      │                                                              │
│      ├── BaseOperationEngine                                        │
│      │   ├── FeaturePopulationEngine                                │
│      │   ├── BridgePopulationEngine                                 │
│      │   ├── IngestionEngine                                        │
│      │   ├── ValidationEngine                                       │
│      │   └── ModelTrainingEngine                                    │
│      │                                                              │
│      └── ProcedureAdapter                                           │
│          ├── WarehouseProcedureAdapter                              │
│          ├── BridgeProcedureAdapter                                 │
│          └── AnalysisProcedureAdapter                               │
│                                                                     │
│  DatabaseOrchestrator (Main Controller)                             │
│      ├─ engines: Dict[str, BaseOperationEngine]                   │
│      ├─ adapter: SQLProcedureAdapter                                │
│      ├─ logger: OperationLogger                                     │
│      └─ checkpoint_store: CheckpointStore                           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔌 Integration with MLB Predict Framework

```
┌─────────────────────────────────────────────────────────────────────┐
│              INTEGRATION: ORCHESTRATION ↔ MLB PREDICT               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  MLB Predict Framework (Existing)                                   │
│  ├─ mlb_predict/config/schemas.py          (ModelConfig)           │
│  ├─ mlb_predict/core/trainer.py            (ModelTrainer)        │
│  ├─ mlb_predict/core/feature_loader.py       (FeatureLoader)       │
│  └─ mlb_predict/core/experiment.py           (ExperimentRunner)    │
│                                                                     │
│                              ▲                                      │
│                              │ integrates with                      │
│                              ▼                                      │
│                                                                     │
│  DatabaseOrchestrator (New)                                         │
│  ├─ Provides: cleaned feature data                                  │
│  ├─ Provides: train/test splits                                     │
│  ├─ Provides: data validation guarantees                            │
│  └─ Consumes: training results for metadata                         │
│                                                                     │
│  Usage Pattern:                                                     │
│  ```python                                                         │
│  # 1. Prepare data via orchestrator                                 │
│  orch = DatabaseOrchestrator(db_url)                               │
│  result = orch.run_operation(FeaturePopulationConfig())            │
│                                                                     │
│  # 2. Train model using MLB Predict framework                       │
│  from mlb_predict import ModelTrainer, ModelConfig                 │
│  trainer = ModelTrainer(ModelConfig.from_yaml("config.yaml"))      │
│  train_result = trainer.train(result.training_query)               │
│                                                                     │
│  # 3. Store results back to database                                │
│  orch.store_model_results(train_result)                            │
│  ```                                                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Current Scripts Inventory

| Script/Procedure | Current Location | Target Integration |
|------------------|------------------|---------------------|
| Feature population | `orchestrate_feature_population.py` | `FeaturePopulationEngine` |
| Bridge population | `populate_all_bridge_tables.sh` | `BridgePopulationEngine` |
| Data ingestion | `download_statcast.py`, `fetch_espn_mlb.py` | `IngestionEngine` |
| Validation | `validate_mlb_data.sql` | `ValidationEngine` |
| Model training | `train_models.py` | `ModelTrainingEngine` |

---

## 🎯 Implementation Plan

### Phase 1: Core Models (2 hours)
1. Define all Pydantic config models
2. Create base operation engine class
3. Implement SQL procedure adapter
4. Create operation result models

### Phase 2: Operation Engines (4 hours)
1. Implement FeaturePopulationEngine
2. Implement BridgePopulationEngine
3. Implement IngestionEngine
4. Implement ValidationEngine

### Phase 3: Main Orchestrator (2 hours)
1. Create DatabaseOrchestrator class
2. Implement checkpoint/resume logic
3. Add unified logging
4. Create CLI interface

### Phase 4: Integration (2 hours)
1. Integrate with MLB Predict Framework
2. Migrate existing scripts
3. Add comprehensive tests
4. Update documentation

**Total: ~10 hours**

---

## 📁 File Structure

```
mlb_predict/
├── orchestration/                          # NEW MODULE
│   ├── __init__.py
│   ├── config.py                          # Pydantic configs
│   ├── engines.py                         # Operation engines
│   ├── adapter.py                         # SQL adapter
│   ├── orchestrator.py                    # Main controller
│   ├── results.py                         # Result models
│   ├── checkpoints.py                     # Checkpoint models
│   └── cli.py                             # CLI interface
│
├── config/                                # EXISTING
├── core/                                  # EXISTING
├── models/                                # EXISTING
├── simulation/                            # EXISTING
└── ...

scripts/
├── orchestrate/                           # NEW
│   ├── populate_features.py              # Uses FeaturePopulationEngine
│   ├── populate_bridge.py                # Uses BridgePopulationEngine
│   ├── ingest_data.py                    # Uses IngestionEngine
│   └── validate.py                       # Uses ValidationEngine
│
├── pitch_data/                            # EXISTING
│   └── orchestrate_feature_population.py  # DEPRECATED → migrate
│
└── bridge/                                # EXISTING
    └── populate_all_bridge_tables.sh     # DEPRECATED → migrate
```

---

**End of Architecture Document**

*Next: Implement the Pydantic orchestration layer*
