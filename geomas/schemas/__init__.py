"""
Schemas Package — The Single Source of Truth.

Core Pydantic models defining the complete simulation state. WorldState is
THE canonical representation — every module reads from and writes to it.
All fields are strongly typed with Pydantic validation.

Models:
    - WorldState: Top-level container holding all simulation state.
      Fields: turn (int), provinces (Dict[int, ProvinceState]),
        nations (Dict[str, NationState]), trust_matrix (Dict[str, Dict[str, float]]),
        relationship_matrix (Dict[str, Dict[str, RelationshipState]]),
        war_stats (Dict[str, WarStats]), pending_proposals (List),
        world_events (List[str]), fallen_nations (Dict[str, dict]).

    - NationState: A sovereign nation's aggregated state.
      Identity: id, name, government_type, cultural_traits.
      Territory: province_ids (List[int]), territorial_water_ids (List[int]).
      Resources: total_budget, total_food, total_energy, total_materials.
      Military: total_soldiers, total_aircraft, total_navy, nukes.
      Demographics: total_population, total_workers (non-military).
      Stability: public_satisfaction (0-100), civil_unrest_active (bool),
        provinces_in_revolt (List[int]).
      Analytics: power_projection (float), is_active (bool).

    - ProvinceState: A single Voronoi cell territory unit.
      Geography: id, name, terrain (TerrainType enum), centroid (x,y),
        vertices (polygon), neighbors (List[int]).
      Ownership: owner_id (str, nullable for ocean).
      Demographics: population, workers.
      Military: soldiers, aircraft, navy, guest_troops (Dict[str, dict]).
      Economy: food_production, energy_production, materials_production,
        tax_revenue.

    - TerrainType (Enum): PLAINS, MOUNTAIN, DESERT, FOREST, COASTAL,
      OCEAN, VOID. Affects unit placement (navy → ocean only,
      soldiers → no ocean), defense bonuses (MOUNTAIN → 1.5x),
      resource distributions (DESERT → low food, MOUNTAIN → high materials).

    - RelationshipState (Enum): PEACE, WAR, NON_AGGRESSION, MUTUAL_DEFENSE.
      Defines diplomatic status and constrains military actions.

    - WarStats: Tracks war metadata — aggressor_id, defender_id,
      start_turn, casualties on each side.

These are the "core" schemas shared across all packages. Domain-specific
schemas live in their respective packages:
    - geomas.actions.*.schemas: Action types and payloads
    - geomas.agents.schemas: Protocol and communication models

Design Principle:
    All models use Pydantic for validation and serialization.
    The WorldState is the Single Source of Truth for the simulation.
"""

from geomas.schemas.world import (
    WorldState,
    NationState,
    ProvinceState,
    TerrainType
)

__all__ = [
    "WorldState",
    "NationState", 
    "ProvinceState",
    "TerrainType"
]
