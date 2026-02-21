"""
Defense Domain Schemas.

Action types and payloads for military/defense operations.
"""

from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Dict, Any, Optional, List

from geomas.actions.common import Decision, ExecutionOutcome


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
# Single Source of Truth: imported from consumption calculator
from geomas.calculators.consumption import MAINTENANCE_DATA

UNIT_MAINTENANCE: dict[UnitType, dict[str, float]] = {
    ut: MAINTENANCE_DATA[ut.value] for ut in UnitType
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
    TerrainType.VOID: 1.0,       # Neutral baseline for non-actionable zones
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
    target_nation_id: Optional[str] = Field(None, description="REQUIRED. For CREATE_UNIT: must be YOUR ID. For MOVE/NUKE: must be TARGET ID.")

    # Explicit fields for strong typing
    unit_type: Optional[UnitType] = Field(None, description="REQUIRED for CREATE_UNIT and MOVE_TROOPS.")
    quantity: Optional[int] = Field(None, gt=0, description="REQUIRED for CREATE_UNIT and MOVE_TROOPS. Must be positive.")
    source_province_id: Optional[int] = Field(None, description="REQUIRED for MOVE_TROOPS. The ID of the province WHERE THE TROOPS ARE NOW.")
    target_province_id: Optional[int] = Field(None, description="REQUIRED for MOVE_TROOPS (Destination), CREATE_UNIT (Location), NUCLEAR_OPTION (Target).")

    # Internal execution field (not visible to LLM)
    execution_outcome: ExecutionOutcome = Field(
        default_factory=ExecutionOutcome,
        exclude=True,
        description="INTERNAL USE ONLY. Tracks success/failure of this specific action."
    )

    @field_validator("source_province_id")
    @classmethod
    def validate_source_for_move(cls, v: Optional[int], info: Any) -> Optional[int]:
        if info.data.get("action_type") == DefenseActionType.MOVE_TROOPS and v is None:
            raise ValueError("source_province_id is required for MOVE_TROOPS")
        return v

    @model_validator(mode='after')
    def validate_action_requirements(self) -> 'DefenseActionItem':
        """Ensure all required fields are present for the specific action type."""
        action = self.action_type
        
        if action == DefenseActionType.MOVE_TROOPS:
            if self.target_province_id is None:
                raise ValueError("target_province_id is required for MOVE_TROOPS (destination)")
            if self.source_province_id is None:
                # Should be caught by field validator, but double check
                raise ValueError("source_province_id is required for MOVE_TROOPS (origin)")
                
        elif action == DefenseActionType.CREATE_UNIT:
            if self.target_province_id is None:
                raise ValueError("target_province_id is required for CREATE_UNIT (location)")
            if self.unit_type is None:
                # Default to SOLDIER if missing? No, force LLM to specify
                raise ValueError("unit_type is required for CREATE_UNIT")
            if self.quantity is None:
                raise ValueError("quantity is required for CREATE_UNIT")
                
        elif action == DefenseActionType.NUCLEAR_OPTION:
            if self.target_province_id is None:
                raise ValueError("target_province_id is required for NUCLEAR_OPTION")
            if not self.target_nation_id:
                raise ValueError("target_nation_id is required for NUCLEAR_OPTION")
                
        return self


class DefenseProposalPayload(BaseModel):
    """
    Payload for Defense Minister proposals (NO DECISION FIELD).
    This is what the Minister generates.
    """
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


class DefensePayload(DefenseProposalPayload):
    """
    Payload for executon (INCLUDES DECISION FIELD).
    This is what the President approves/vetoes and puts in the envelope.
    """
    decision: Decision = Field(
        default=Decision.PENDING,
        description="FOR PRESIDENT ONLY. Ministers MUST leave as PENDING."
    )


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
    available_population: int,
    bureaucracy_multiplier: float = 1.0
) -> tuple[bool, str]:
    """
    Check if a nation can afford to create units.
    
    Returns:
        Tuple of (can_afford: bool, reason: str if failed)
    """
    costs = UNIT_COSTS[unit_type]
    
    total_budget = costs["budget"] * quantity * bureaucracy_multiplier
    total_materials = costs["materials"] * quantity * bureaucracy_multiplier
    total_energy = costs["energy"] * quantity * bureaucracy_multiplier
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

