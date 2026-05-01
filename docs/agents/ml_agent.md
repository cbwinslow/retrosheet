# ML Agent Instructions

## Purpose

Build a reproducible, leak-resistant ML layer on top of baseball state and feature tables.

## Core Principles

- Features must be versioned or reproducible by SQL/Python logic.
- Models must be versioned.
- Training runs must be tracked.
- Predictions must record model version and scoring timestamp.
- Backtesting is required for live models.
- Prevent future leakage.

## Initial Model Priorities

- win_probability
- next_run_probability
- plate_appearance_outcome
- later: pitch_outcome

## Required Tables

- models.registry
- models.training_runs
- models.artifacts
- predictions.game_live
- predictions.plate_appearance_live
- predictions.pitch_live

## Feature Rules

Use sabermetric state as first-class modeling context:
- Run expectancy
- Win expectancy
- Leverage index
- Base-out state
- Inning context
- Score differential
- Platoon state
- Park and weather effects
- Rolling player form
- Bullpen/fatigue context

## Avoid

- Notebook-only feature definitions
- Unversioned models
- Ad hoc training data dumps with no lineage
- Backtests that use unavailable future information
