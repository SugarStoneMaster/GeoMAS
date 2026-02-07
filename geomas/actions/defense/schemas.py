"""
Defense Domain Schemas.

Action types and payloads for military/defense operations.
"""

from enum import Enum
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, Optional, List

from geomas.actions.common import Decision


class DefenseActionType(str, Enum):
    """Defense-related action types handled by the Defense Minister."""
    CREATE_UNIT = "CREATE_UNIT"
    MOVE_TROOPS = "MOVE_TROOPS"
    NUCLEAR_OPTION = "NUCLEAR_OPTION"


class UnitType(str, Enum):
    """Military unit types that can be created and deployed."""
    SOLDIER = "SOLDIER"   # Ground troops, can be on LAND/COASTAL/MOUNTAIN or transported by NAVY
    NAVY = "NAVY"         # Naval vessels, can only be on OCEAN (territorial waters)
    AIRCRAFT = "AIRCRAFT" # Air units, can be on LAND/COASTAL/MOUNTAIN, have extended range


# --- UNIT COSTS (per single unit) ---
# Each unit requires resources to CREATE and population to MAINTAIN
UNIT_COSTS: dict[UnitType, dict[str, float]] = {
    UnitType.SOLDIER: {
        "budget": 5.0,        # Currency cost to recruit
        "materials": 2.0,     # Equipment cost
        "energy": 0.0,        # No energy required for infantry
        "population": 1,      # Each soldier consumes 1 population
    },
    UnitType.NAVY: {
        "budget": 50.0,       # Ships are expensive
        "materials": 30.0,    # Hull, weapons, etc.
        "energy": 5.0,        # Fuel for construction
        "population": 10,     # Crew requirement
    },
    UnitType.AIRCRAFT: {
        "budget": 80.0,       # Advanced technology
        "materials": 40.0,    # Airframe, avionics
        "energy": 10.0,       # Fuel for testing
        "population": 5,      # Pilots and ground crew
    },
}

# --- MAINTENANCE COSTS (per unit per turn) ---
UNIT_MAINTENANCE: dict[UnitType, dict[str, float]] = {
    UnitType.SOLDIER: {
        "budget": 1.0,        # Pay and supplies
        "materials": 0.5,     # Ammunition, equipment wear
        "energy": 0.0,
    },
    UnitType.NAVY: {
        "budget": 10.0,       # Crew pay, port fees
        "materials": 5.0,     # Repairs, ammunition
        "energy": 3.0,        # Fuel consumption
    },
    UnitType.AIRCRAFT: {
        "budget": 15.0,       # Pilot pay, hangar
        "materials": 8.0,     # Parts, repairs
        "energy": 5.0,        # Aviation fuel
    },
}


# --- TERRAIN CONSTRAINTS ---
# Defines which terrain types each unit can be stationed on
from geomas.schemas.world import TerrainType

UNIT_TERRAIN_CONSTRAINTS: dict[UnitType, set[TerrainType]] = {
    UnitType.SOLDIER: {TerrainType.LAND, TerrainType.COASTAL, TerrainType.MOUNTAIN},
    UnitType.NAVY: {TerrainType.OCEAN},  # Only in territorial waters
    UnitType.AIRCRAFT: {TerrainType.LAND, TerrainType.COASTAL, TerrainType.MOUNTAIN},
}

# --- TERRAIN COMBAT MODIFIERS ---
# Defense multiplier when defending on specific terrain
TERRAIN_DEFENSE_MULTIPLIER: dict[TerrainType, float] = {
    TerrainType.LAND: 1.0,       # Baseline
    TerrainType.COASTAL: 0.9,    # Slight disadvantage (multiple attack vectors)
    TerrainType.MOUNTAIN: 1.5,   # Strong defensive advantage
    TerrainType.OCEAN: 1.0,      # Baseline for naval combat
}


# --- MOVEMENT COSTS (per unit per province traversed) ---
MOVEMENT_ENERGY_COST: dict[UnitType, float] = {
    UnitType.SOLDIER: 0.1,    # Infantry: low energy just for logistics
    UnitType.NAVY: 1.0,       # Ships consume fuel
    UnitType.AIRCRAFT: 2.0,   # Aircraft consume most fuel
}

# Movement range (max provinces per turn)
MOVEMENT_RANGE: dict[UnitType, int] = {
    UnitType.SOLDIER: 2,      # Infantry moves slowly
    UnitType.NAVY: 4,         # Ships have good range
    UnitType.AIRCRAFT: 6,     # Aircraft have best range
}


class DefenseActionItem(BaseModel):
    """A single defense action in the waterfall priority queue."""
    priority: int
    action_type: DefenseActionType
    target_nation_id: Optional[str] = None
    target_province_id: Optional[int] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class DefensePayload(BaseModel):
    """Payload for Defense Minister actions."""
    decision: Decision
    moves: List[DefenseActionItem] = Field(
        default_factory=list, 
        max_length=3,
        description="Ordered list of actions (Waterfall Logic). MAXIMUM 3 ACTIONS ALLOWED."
    )

    @field_validator("moves")
    @classmethod
    def limit_actions(cls, v: List[DefenseActionItem]) -> List[DefenseActionItem]:
        if len(v) > 3:
            raise ValueError("Defense Minister can perform at most 3 actions per turn.")
        return v


# --- VALIDATION HELPERS ---

def can_place_unit(unit_type: UnitType, terrain: TerrainType) -> bool:
    """Check if a unit type can be placed on a given terrain."""
    return terrain in UNIT_TERRAIN_CONSTRAINTS[unit_type]


def can_afford_unit(
    unit_type: UnitType,
    quantity: int,
    budget: float,
    materials: float,
    energy: float,
    available_population: int
) -> tuple[bool, str]:
    """
    Check if a nation can afford to create units.
    
    Returns:
        Tuple of (can_afford: bool, reason: str if failed)
    """
    costs = UNIT_COSTS[unit_type]
    
    total_budget = costs["budget"] * quantity
    total_materials = costs["materials"] * quantity
    total_energy = costs["energy"] * quantity
    total_pop = int(costs["population"]) * quantity
    
    if budget < total_budget:
        return False, f"Insufficient budget: need {total_budget:.1f}, have {budget:.1f}"
    if materials < total_materials:
        return False, f"Insufficient materials: need {total_materials:.1f}, have {materials:.1f}"
    if energy < total_energy:
        return False, f"Insufficient energy: need {total_energy:.1f}, have {energy:.1f}"
    if available_population < total_pop:
        return False, f"Insufficient population: need {total_pop}, have {available_population}"
    
    return True, ""


def get_terrain_defense_bonus(terrain: TerrainType) -> float:
    """Get the defense multiplier for a terrain type."""
    return TERRAIN_DEFENSE_MULTIPLIER.get(terrain, 1.0)

