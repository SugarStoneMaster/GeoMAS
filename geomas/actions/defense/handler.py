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
    can_place_unit,
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
        - unit_type: UnitType enum value (SOLDIER, NAVY, AIRCRAFT)
        - quantity: Number of units to create
        - province_id: Target province for placement (required)
    """
    world = engine.world
    nation = world.nations[nation_id]
    
    # Parse parameters
    unit_type_str = parameters.get("unit_type", "SOLDIER")
    quantity = parameters.get("quantity", 1)
    province_id = parameters.get("province_id")
    
    # Validate unit type
    try:
        unit_type = UnitType(unit_type_str)
    except ValueError:
        engine.logs.append(f"[DEFENSE] Invalid unit type: {unit_type_str}")
        return
    
    # Validate province specified
    if province_id is None:
        # Default to capital if not specified
        province_id = nation.capital_province_id
        if province_id is None:
            engine.logs.append(f"[DEFENSE] No province specified and no capital found")
            return
    
    # Validate province exists and is owned
    province = world.provinces.get(province_id)
    if not province:
        engine.logs.append(f"[DEFENSE] Province {province_id} does not exist")
        return
    
    # For NAVY, check territorial waters; for others, check owned land
    if unit_type == UnitType.NAVY:
        if province_id not in nation.territorial_water_ids:
            engine.logs.append(f"[DEFENSE] Province {province_id} is not in territorial waters")
            return
    else:
        if province.owner_id != nation_id:
            engine.logs.append(f"[DEFENSE] Province {province_id} not owned by {nation_id}")
            return
    
    # Validate terrain constraint
    if not can_place_unit(unit_type, province.terrain):
        engine.logs.append(
            f"[DEFENSE] Cannot place {unit_type.value} on {province.terrain.value} terrain"
        )
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
    
    # --- EXECUTE: Deduct resources ---
    nation.total_budget -= total_budget
    nation.total_materials -= total_materials
    nation.total_energy -= total_energy
    nation.total_workers -= total_pop  # Workers become soldiers
    
    # --- EXECUTE: Add units to province ---
    if unit_type == UnitType.SOLDIER:
        province.soldiers += quantity
        nation.total_soldiers += quantity
    elif unit_type == UnitType.NAVY:
        province.navy += quantity
        nation.total_navy += quantity
    elif unit_type == UnitType.AIRCRAFT:
        province.aircraft += quantity
        nation.total_aircraft += quantity
    
    engine.logs.append(
        f"[DEFENSE] Created {quantity}x {unit_type.value} in province {province_id}. "
        f"Cost: {total_budget:.1f} budget, {total_materials:.1f} materials"
    )


