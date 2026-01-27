"""
Defense Action Handler.

Executes military/defense actions using waterfall priority logic.
"""

from typing import TYPE_CHECKING
from geomas.actions.defense.schemas import (
    DefenseActionType, 
    DefensePayload,
    UnitType,
    UNIT_COSTS,
    can_afford_unit,
)

if TYPE_CHECKING:
    from geomas.actions.engine import ActionEngine


def execute_defense_waterfall(
    engine: 'ActionEngine',
    nation_id: str, 
    payload: DefensePayload
) -> None:
    """
    Execute defense actions in priority order (waterfall).
    
    Lower priority number = higher priority.
    Actions are executed until one fails validation.
    """
    # Sort by priority (1 is highest)
    moves = sorted(payload.moves, key=lambda x: x.priority)
    
    nation = engine.world.nations.get(nation_id)
    if not nation:
        engine.logs.append(f"[DEFENSE] Unknown nation: {nation_id}")
        return
    
    for move in moves:
        if move.action_type == DefenseActionType.CREATE_UNIT:
            _execute_create_unit(engine, nation_id, move.parameters)
            
        elif move.action_type == DefenseActionType.MOVE_TROOPS:
            # TODO: Implement in Phase 4
            engine.logs.append(f"[DEFENSE] MOVE_TROOPS not yet implemented")
            
        elif move.action_type == DefenseActionType.NUCLEAR_OPTION:
            # TODO: Implement in Phase 4
            engine.logs.append(f"[DEFENSE] NUCLEAR_OPTION not yet implemented")


def _execute_create_unit(
    engine: 'ActionEngine',
    nation_id: str,
    parameters: dict
) -> None:
    """
    Execute CREATE_UNIT action.
    
    Parameters:
        - unit_type: UnitType enum value
        - quantity: Number of units to create
        - province_id: Target province for placement
    """
    nation = engine.world.nations[nation_id]
    
    # Parse parameters
    unit_type_str = parameters.get("unit_type", "SOLDIER")
    quantity = parameters.get("quantity", 1)
    province_id = parameters.get("province_id")
    
    try:
        unit_type = UnitType(unit_type_str)
    except ValueError:
        engine.logs.append(f"[DEFENSE] Invalid unit type: {unit_type_str}")
        return
    
    # Get costs
    costs = UNIT_COSTS[unit_type]
    total_budget = costs["budget"] * quantity
    total_materials = costs["materials"] * quantity
    total_energy = costs["energy"] * quantity
    total_pop = int(costs["population"]) * quantity
    
    # Validate affordability
    can_afford, reason = can_afford_unit(
        unit_type=unit_type,
        quantity=quantity,
        budget=nation.total_budget,
        materials=nation.total_materials,
        energy=nation.total_energy,
        available_population=nation.total_workers
    )
    
    if not can_afford:
        engine.logs.append(f"[DEFENSE] CREATE_UNIT failed: {reason}")
        return
    
    # Deduct resources
    nation.total_budget -= total_budget
    nation.total_materials -= total_materials
    nation.total_energy -= total_energy
    
    # TODO: Add units to province (Phase 4 complete implementation)
    engine.logs.append(
        f"[DEFENSE] Created {quantity}x {unit_type.value}. "
        f"Cost: {total_budget:.1f} budget, {total_materials:.1f} materials"
    )

