"""
Defense Package.

Handles military/defense actions: CREATE_UNIT, MOVE_TROOPS, NUCLEAR_OPTION.
"""

from geomas.actions.defense.schemas import (
    DefenseActionType,
    DefensePayload,
    DefenseProposalPayload,
    DefenseActionItem,
    UnitType,
    Decision,
    UNIT_COSTS,
    UNIT_MAINTENANCE,
    UNIT_TERRAIN_CONSTRAINTS,
    TERRAIN_DEFENSE_MULTIPLIER,
    MOVEMENT_ENERGY_COST,
    MOVEMENT_RANGE,
    can_place_unit,
    can_afford_unit,
    get_terrain_defense_bonus,
)
from geomas.actions.defense.handler import execute_defense_waterfall

__all__ = [
    "DefenseActionType",
    "DefensePayload",
    "DefenseProposalPayload",
    "DefenseActionItem",
    "UnitType",
    "Decision",
    "UNIT_COSTS",
    "UNIT_MAINTENANCE",
    "UNIT_TERRAIN_CONSTRAINTS",
    "TERRAIN_DEFENSE_MULTIPLIER",
    "MOVEMENT_ENERGY_COST",
    "MOVEMENT_RANGE",
    "can_place_unit",
    "can_afford_unit",
    "get_terrain_defense_bonus",
    "execute_defense_waterfall",
]
