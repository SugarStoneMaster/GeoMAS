"""
Schemas Package.

Core data models representing the simulation world state.

Modules:
    - world: Contains the fundamental Pydantic models:
        - WorldState: Complete simulation state at a given turn
        - NationState: A nation's identity, territory, and resources
        - ProvinceState: A single territory cell with population/military
        - MinisterialState: Internal metrics (public satisfaction)
        - TerrainType: Enum for terrain classification

These are the "core" schemas shared across all packages. Domain-specific
schemas live in their respective packages:
    - geomas.actions.schemas: Action types and payloads
    - geomas.agents.schemas: Protocol and communication models

Design Principle:
    All models use Pydantic for validation and serialization.
    The WorldState is the Single Source of Truth for the simulation.
"""

from geomas.schemas.world import (
    WorldState,
    NationState,
    ProvinceState,
    MinisterialState,
    TerrainType
)

__all__ = [
    "WorldState",
    "NationState", 
    "ProvinceState",
    "MinisterialState",
    "TerrainType"
]
