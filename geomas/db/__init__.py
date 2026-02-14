"""
Database Package.

DuckDB-based persistence layer for simulation data and XAI explainability.

Modules:
    - connection: Database connection management
    - schema: Table definitions and creation
    - repositories: Data access classes
    - serialization: Pydantic model serialization helpers
    - cache: In-events turn caching
    - genesis: Genesis historical events database

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
