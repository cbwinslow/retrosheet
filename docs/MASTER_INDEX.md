# MLB Prediction Warehouse - Master Documentation Index

**Version**: 2.0  
**Last Updated**: April 24, 2026  
**Purpose**: Complete guide to all documentation and how to use it

---

## Start Here

### New Users
1. **README.md** - Project overview and quick setup
2. **docs/USER_MANUAL.md** - Complete user guide with examples
3. **docs/agents/AGENTS.md** - Project conventions and rules

### Developers/Researchers
1. **docs/PROCEDURES_DETAILED.md** - Step-by-step procedures for everything
2. **docs/agents/FILE_INVENTORY.md** - Reference for all files
3. **docs/WORKFLOW_VALIDATION_REPORT.md** - Architecture understanding

### AI Agents
1. **docs/agents/AGENTS.md** - Operating guide (MUST READ)
2. **docs/agents/PROCEDURES.md** - Canonical workflows
3. **docs/agents/FILE_INVENTORY.md** - File reference
4. **docs/agents/REPRODUCIBILITY_AUDIT_PROMPT.md** - Audit procedures

---

## Documentation Map

### Core Documentation

| Document | Purpose | Audience | Priority |
|----------|---------|----------|----------|
| **README.md** | Project overview, setup instructions | Everyone | ⭐⭐⭐⭐⭐ |
| **docs/USER_MANUAL.md** | Complete user guide with examples | Researchers | ⭐⭐⭐⭐⭐ |
| **docs/PROCEDURES_DETAILED.md** | Step-by-step procedures (25 procedures) | Developers | ⭐⭐⭐⭐⭐ |
| **docs/PROJECT_LOG.md** | Chronological project history | Everyone | ⭐⭐⭐⭐ |

### Agent Documentation (for AI Assistants)

| Document | Purpose | When to Use |
|----------|---------|-------------|
| **docs/agents/AGENTS.md** | Operating guide and conventions | Before any work |
| **docs/agents/PROCEDURES.md** | Canonical workflows | When implementing |
| **docs/agents/FILE_INVENTORY.md** | File reference | When creating files |
| **docs/agents/CURRENT_SNAPSHOT.md** | Current state summary | For context |
| **docs/agents/REPRODUCIBILITY_AUDIT_PROMPT.md** | Audit procedures | When auditing |

### Technical Reference

| Document | Purpose | Content |
|----------|---------|---------|
| **docs/WORKFLOW_VALIDATION_REPORT.md** | Infrastructure audit | Architecture analysis, redundancy findings |
| **docs/diagrams/WORKFLOW_ARCHITECTURE.puml** | Data flow diagram | Visual architecture |
| **docs/diagrams/INTEGRATION_LAYER.puml** | Integration design | Proposed Python layer |
| **docs/agents/TABLE_INVENTORY.md** | Database tables | Schema documentation |
| **docs/PITCH_FEATURE_MART_SCHEMA.md** | Feature mart docs | 220+ features explained |

### Analysis & Research

| Document | Purpose | Content |
|----------|---------|---------|
| **analysis/** | Research outputs | PCA, correlations, feature importance |
| **docs/AT_BAT_OUTCOME_MODEL_REVIEW.md** | Model review | Previous model analysis |
| **docs/ADVANCED_MODELING_PLAN.md** | Modeling roadmap | Future plans |

---

## Quick Reference by Task

### "How do I...?"

#### Get Started
- **Quick setup**: README.md → Section "Quick Start"
- **First prediction**: docs/USER_MANUAL.md → "Quick Start Guide"
- **Understand architecture**: docs/USER_MANUAL.md → "System Architecture"

#### Work with Data
- **Check what data exists**: docs/USER_MANUAL.md → "Data Layers Explained"
- **Query features**: docs/PROCEDURES_DETAILED.md → Procedure 7, 8, 9
- **Add custom features**: docs/PROCEDURES_DETAILED.md → Procedure 24

#### Train Models
- **Train a model**: docs/USER_MANUAL.md → "Model Training"
- **Feature selection**: docs/PROCEDURES_DETAILED.md → Procedure 8
- **Cross-validation**: docs/PROCEDURES_DETAILED.md → Procedure 12
- **Custom model**: docs/USER_MANUAL.md → "Adding Custom Models"

#### Make Predictions
- **Batch predictions**: docs/PROCEDURES_DETAILED.md → Procedure 13
- **Live predictions**: docs/PROCEDURES_DETAILED.md → Procedure 14
- **Check calibration**: docs/PROCEDURES_DETAILED.md → Procedure 15

#### Fix Issues
- **Something broke**: docs/PROCEDURES_DETAILED.md → "Troubleshooting Procedures"
- **Database issues**: Procedure 21
- **Model registry issues**: Procedure 22
- **Performance problems**: Procedure 23

#### Maintain System
- **Rebuild warehouse**: docs/USER_MANUAL.md → "5-Minute Warehouse Rebuild"
- **Database maintenance**: docs/PROCEDURES_DETAILED.md → Procedure 19
- **Backup**: docs/PROCEDURES_DETAILED.md → Procedure 20

---

## Documentation Standards

### For AI Agents Creating Documentation

**Required Header**:
```markdown
# Title

**Purpose**: One sentence description  
**Audience**: Who should read this  
**Prerequisites**: What you need to know first
```

**Required Sections**:
1. Overview/Introduction
2. Prerequisites
3. Step-by-step instructions
4. Validation steps
5. Troubleshooting
6. References to other docs

**Forbidden**:
- Vague descriptions ("do the thing")
- Missing file paths
- Assumptions about knowledge
- Outdated information

---

## Key Insights (Read These)

### 1. Framework Schema is DEPRECATED
**Location**: docs/WORKFLOW_VALIDATION_REPORT.md
**Key Finding**: `sql/framework/001_framework_schema.sql` creates redundant tables. Use existing infrastructure instead.

### 2. The Warehouse is 85% Complete
**Location**: docs/WORKFLOW_VALIDATION_REPORT.md
**Key Finding**: Most infrastructure exists and works. Only need thin Python integration layer.

### 3. Reproducibility Mandate
**Location**: docs/agents/AGENTS.md
**Key Rule**: ALL database operations must be in version-controlled .sql files. Never ad-hoc SQL.

### 4. SQL-First Development
**Location**: docs/agents/AGENTS.md
**Key Rule**: Write SQL → Test → Commit → Document → Then run.

---

## Common Workflows

### Workflow 1: New Researcher Onboarding
```
1. Read README.md (10 min)
2. Read docs/USER_MANUAL.md → Quick Start (15 min)
3. Run: ./scripts/rebuild_warehouse.sh --mode quick (10 min)
4. Try: docs/USER_MANUAL.md → First Prediction in 3 Commands (5 min)
5. Explore: docs/USER_MANUAL.md → Data Layers (30 min)
```
**Total time**: 1 hour to productive use

### Workflow 2: Adding a Custom Model
```
1. Read docs/USER_MANUAL.md → Adding Custom Models
2. Create model class (5 lines of code)
3. Register in configs/
4. Train: mlb-predict train --model my_model
5. Verify: psql -c "SELECT * FROM models.model_registry"
```
**Total time**: 30 minutes

### Workflow 3: Running an Experiment
```
1. Create config: configs/experiments/my_exp.yaml
2. Read docs/PROCEDURES_DETAILED.md → Experiment Tracking
3. Run: mlb-predict experiment run configs/experiments/my_exp.yaml
4. Analyze: psql -c "SELECT * FROM framework.experiments"
```
**Total time**: 1 hour (plus training time)

### Workflow 4: Troubleshooting Data Issues
```
1. Read docs/PROCEDURES_DETAILED.md → Procedure 21
2. Run diagnosis SQL queries
3. Identify issue (stale data, missing data, etc.)
4. Apply fix from procedure
5. Validate fix worked
```
**Total time**: 15-30 minutes

---

## File Navigation

### Where to Find...

**SQL Files**:
- Schema definitions: `sql/<schema>/001_*.sql`
- Feature engineering: `sql/features/*.sql`
- Bridge tables: `sql/bridge/*.sql`
- Warehouse orchestration: `sql/warehouse/*.sql`

**Python Scripts**:
- Data ingestion: `scripts/data_ingestion/`
- Model training: `scripts/model_training/`
- Inference: `scripts/model_inference/`
- Analysis: `scripts/analysis/`
- Bridge: `scripts/bridge/`

**Configuration**:
- Database: `config/chadwick_event_columns.txt`
- Experiments: `configs/experiments/*.yaml`
- Models: `configs/models/*.yaml`

**Documentation**:
- User docs: `docs/*.md`
- Agent docs: `docs/agents/*.md`
- Diagrams: `docs/diagrams/*.puml`

---

## Validation Checklist

Before using any documentation:

- [ ] Check PROJECT_LOG.md for recent changes
- [ ] Verify file exists in FILE_INVENTORY.md
- [ ] Check if marked DEPRECATED
- [ ] Look for "Status" field
- [ ] Verify last updated date

Before creating new documentation:

- [ ] Check if similar doc already exists
- [ ] Follow header template
- [ ] Add to FILE_INVENTORY.md
- [ ] Add to PROJECT_LOG.md
- [ ] Update this MASTER_INDEX.md

---

## Questions?

### "Is this documentation current?"
Check:
1. `docs/PROJECT_LOG.md` - Look for recent entries
2. File header "Date" field
3. `docs/agents/FILE_INVENTORY.md` - Status column

### "Which procedure should I use?"
Check:
1. `docs/PROCEDURES_DETAILED.md` - Table of contents
2. This MASTER_INDEX.md → "Quick Reference by Task"

### "How does the system work?"
Read:
1. `docs/WORKFLOW_VALIDATION_REPORT.md` - Architecture
2. `docs/USER_MANUAL.md` - System Architecture section
3. `docs/diagrams/*.puml` - Visual diagrams

### "What can the system do?"
Read:
1. `docs/USER_MANUAL.md` - Complete feature list
2. `docs/PROCEDURES_DETAILED.md` - All 25 procedures

---

## Change Log

### 2026-04-24
- Created MASTER_INDEX.md
- Created USER_MANUAL.md (comprehensive user guide)
- Created PROCEDURES_DETAILED.md (25 detailed procedures)
- Created WORKFLOW_VALIDATION_REPORT.md
- Created architecture diagrams
- Deprecated redundant framework schema
- Added batch_operations.sql
- Added feature_importance.sql
- Updated FILE_INVENTORY.md
- Updated PROJECT_LOG.md

---

**End of Master Index**

For the complete picture, read in order:
1. README.md
2. docs/agents/AGENTS.md
3. docs/USER_MANUAL.md
4. docs/PROCEDURES_DETAILED.md
