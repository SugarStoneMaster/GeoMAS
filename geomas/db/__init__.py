"""
Database Package.

DuckDB-based persistence layer for simulation data and XAI explainability.

Modules:
    - connection: Database connection management
    - schema: Table definitions and creation
    - repositories: Data access classes
    - serialization: Pydantic model serialization helpers
    - cache: In-memory turn caching

Usage:
    from geomas.db import SimulationDB, TurnCache
    
    db = SimulationDB("data/simulation.duckdb")
    db.save_snapshot(turn, world)
    world = db.load_snapshot(turn)
    
    cache = TurnCache(max_turns=20)
    cache.add_turn(turn, world, envelopes)
"""

from geomas.db.connection import SimulationDB
from geomas.db.cache import TurnCache

__all__ = [
    "SimulationDB",
    "TurnCache",
]
