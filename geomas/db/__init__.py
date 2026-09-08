"""
Database Package — Dual-DB Persistence Layer.

DuckDB-based persistence layer for simulation data and XAI explainability.
Implements a dual-DB strategy: SimulationDB for complete state snapshots
and agent traces, MetricsDB for lightweight time-series analytics.

Architecture:
    State flows: SimulationEngine → Serialization → SimulationDB.
    Reads: UI/Analysis → TurnCache (in-memory) → SimulationDB.
    Analytics: SimulationEngine → MetricsExtractor → MetricsDB.

Modules:
    - connection.py (SimulationDB, 430 lines): Primary persistence.
      Tables: simulations (metadata), snapshots (per-turn WorldState as JSON),
        envelopes (per-nation per-turn agent output), behaviors (deception/
        coherence metrics), token_usage (LLM cost tracking).
      Features: create_simulation(), save/load_snapshot(), save/load_envelope(),
        save/load_behaviors(), get_simulations(), get_max_turn(),
        copy_history_for_fork() for counterfactual forking.
      Uses DuckDB via context manager pattern (__enter__/__exit__).

    - genesis.py (GenesisDB, 9KB): Separate DB for ancient history data.
      Tables: genesis_events (year, text, tag, nation_a, nation_b),
        trust_snapshots (trust matrix at each genesis year).
      Populated by GenesisEngine and reusable across runs with same seed.

    - serialization.py (8.9KB): WorldState ↔ JSON conversion.
      Handles complex types: Pydantic models, Enums, nested dicts
      (trust_matrix, relationship_matrix, war_stats, pending_proposals).
      Functions: serialize_world_state(), deserialize_world_state(),
        serialize_envelopes(), deserialize_envelopes().

    - cache.py (TurnCache, 6.5KB): In-memory acceleration layer.
      Caches deserialized WorldState and envelopes per (simulation_id, turn).
      Provides: get_world(), get_envelopes(), invalidate().

    - metrics_db.py (MetricsDB, 7.8KB): Analytics time-series storage.
      Table: nation_metrics (simulation_id, turn, nation_id + all numerical
        metrics from calculators.metrics). Optimized for pandas DataFrames.

Usage:
    from geomas.db import SimulationDB, TurnCache, GenesisDB

    db = SimulationDB("data/simulation.duckdb")
    db.save_snapshot(turn, world)
    world = db.load_snapshot(turn)

    cache = TurnCache(max_turns=20)
    cache.add_turn(turn, world, envelopes)

    genesis_db = GenesisDB("data/genesis_42.duckdb")
    genesis_db.save_events_batch(events)
"""

from geomas.db.connection import SimulationDB
from geomas.db.cache import TurnCache
from geomas.db.genesis import GenesisDB

__all__ = [
    "SimulationDB",
    "TurnCache",
    "GenesisDB",
]
