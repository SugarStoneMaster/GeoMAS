"""
Database Package.

DuckDB-based persistence layer for simulation data and XAI explainability.

Modules:
    - connection: Database connection management
    - schema: Table definitions and creation
    - repositories: Data access classes
    - serialization: Pydantic model serialization helpers

Usage:
    from geomas.db import SimulationDB
    
    db = SimulationDB("data/simulation.duckdb")
    db.save_snapshot(turn, world)
    world = db.load_snapshot(turn)
"""

from geomas.db.connection import SimulationDB

__all__ = [
    "SimulationDB",
]
