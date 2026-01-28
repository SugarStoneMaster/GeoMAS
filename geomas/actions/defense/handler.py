"""
Defense Action Handler.

Executes military/defense actions using waterfall priority logic.
"""

from typing import TYPE_CHECKING, Optional, List
from geomas.actions.defense.schemas import (
    DefenseActionType, 
    DefensePayload,
    UnitType,
    UNIT_COSTS,
    MOVEMENT_ENERGY_COST,
    MOVEMENT_RANGE,
    can_afford_unit,
    can_place_unit,
)
from geomas.schemas.world import TerrainType

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
            _execute_move_troops(engine, nation_id, move.parameters)
            
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


def _execute_move_troops(
    engine: 'ActionEngine',
    nation_id: str,
    parameters: dict
) -> None:
    """
    Execute MOVE_TROOPS action.
    
    Parameters:
        - unit_type: UnitType enum value (SOLDIER, NAVY, AIRCRAFT)
        - quantity: Number of units to move
        - from_province_id: Source province
        - to_province_id: Destination province
    """
    world = engine.world
    nation = world.nations[nation_id]
    
    # Parse parameters
    unit_type_str = parameters.get("unit_type", "SOLDIER")
    quantity = parameters.get("quantity", 1)
    from_province_id = parameters.get("from_province_id")
    to_province_id = parameters.get("to_province_id")
    
    # Validate unit type
    try:
        unit_type = UnitType(unit_type_str)
    except ValueError:
        engine.logs.append(f"[DEFENSE] MOVE_TROOPS: Invalid unit type: {unit_type_str}")
        return
    
    # Validate provinces specified
    if from_province_id is None or to_province_id is None:
        engine.logs.append(f"[DEFENSE] MOVE_TROOPS: Must specify from_province_id and to_province_id")
        return
    
    # Validate provinces exist
    from_province = world.provinces.get(from_province_id)
    to_province = world.provinces.get(to_province_id)
    
    if not from_province:
        engine.logs.append(f"[DEFENSE] MOVE_TROOPS: Source province {from_province_id} does not exist")
        return
    if not to_province:
        engine.logs.append(f"[DEFENSE] MOVE_TROOPS: Destination province {to_province_id} does not exist")
        return
    
    # Validate ownership of source province
    if unit_type == UnitType.NAVY:
        if from_province_id not in nation.territorial_water_ids:
            engine.logs.append(f"[DEFENSE] MOVE_TROOPS: Source {from_province_id} not in territorial waters")
            return
    else:
        if from_province.owner_id != nation_id:
            engine.logs.append(f"[DEFENSE] MOVE_TROOPS: Source {from_province_id} not owned by {nation_id}")
            return
    
    # Validate units available in source
    available_units = _get_units_in_province(from_province, unit_type)
    if available_units < quantity:
        engine.logs.append(
            f"[DEFENSE] MOVE_TROOPS: Not enough {unit_type.value} in province {from_province_id}. "
            f"Have {available_units}, need {quantity}"
        )
        return
    
    # Validate path exists and is valid for unit type
    path = _find_valid_path(engine, nation_id, from_province_id, to_province_id, unit_type)
    if path is None:
        engine.logs.append(
            f"[DEFENSE] MOVE_TROOPS: No valid path from {from_province_id} to {to_province_id} "
            f"for {unit_type.value}"
        )
        return
    
    # Calculate distance (path includes start and end)
    distance = len(path) - 1
    
    # Validate range
    max_range = MOVEMENT_RANGE[unit_type]
    if distance > max_range:
        engine.logs.append(
            f"[DEFENSE] MOVE_TROOPS: Distance {distance} exceeds {unit_type.value} range of {max_range}"
        )
        return
    
    # Calculate and validate energy cost
    energy_per_unit = MOVEMENT_ENERGY_COST[unit_type]
    total_energy_cost = energy_per_unit * quantity * distance
    
    if nation.total_energy < total_energy_cost:
        engine.logs.append(
            f"[DEFENSE] MOVE_TROOPS: Insufficient energy. Need {total_energy_cost:.1f}, have {nation.total_energy:.1f}"
        )
        return
    
    # Check destination is valid for unit type (must be owned or passable for reinforcement)
    is_enemy = _is_enemy_territory(world, nation_id, to_province_id, unit_type)
    
    # --- EXECUTE: Deduct energy first ---
    nation.total_energy -= total_energy_cost
    
    # Remove units from source
    _remove_units_from_province(from_province, unit_type, quantity)
    
    if is_enemy:
        # Combat resolution
        from geomas.actions.defense.combat import (
            resolve_land_combat,
            execute_naval_landing,
            _conquer_province,
        )
        import random
        rng = random.Random(engine.world.turn + hash(nation_id))
        
        if unit_type == UnitType.NAVY:
            # Naval landing logic
            result = execute_naval_landing(
                world=world,
                attacker_nation_id=nation_id,
                attacker_navy=quantity,
                target_water_province_id=to_province_id,
                rng=rng
            )
            
            # Update attacker navy count
            nation.total_navy -= quantity
            
            engine.logs.append(f"[COMBAT] {result.log_message}")
            
            if result.attacker_wins:
                engine.logs.append(
                    f"[COMBAT] Naval landing successful at province {result.landing_province_id}"
                )
            else:
                engine.logs.append(f"[COMBAT] Naval assault failed - all ships lost")
        
        elif unit_type == UnitType.SOLDIER:
            # Land combat
            result = resolve_land_combat(
                attacker_soldiers=quantity,
                defender_province=to_province,
                rng=rng
            )
            
            engine.logs.append(f"[COMBAT] {result.log_message}")
            
            if result.attacker_wins:
                # Conquer the province
                old_owner = to_province.owner_id
                _conquer_province(world, nation_id, to_province)
                
                # Place attacking soldiers in conquered province
                to_province.soldiers = quantity
                nation.total_soldiers += quantity  # They were removed but now added back
                
                engine.logs.append(
                    f"[COMBAT] Province {to_province_id} conquered by {nation_id}"
                )
                
                # Trust impact: combat causes trust decrease
                if old_owner:
                    engine.adjust_trust(nation_id, old_owner, -0.2)
                    engine.adjust_trust(old_owner, nation_id, -0.2)
                    engine.logs.append(f"[DIPLOMACY] Trust between {nation_id} and {old_owner} decreased")
            else:
                # Attacker loses all soldiers
                nation.total_soldiers -= quantity
                engine.logs.append(
                    f"[COMBAT] Attack failed - {quantity} soldiers lost"
                )
                
                # Trust impact even on failed attack
                defender_id = to_province.owner_id
                if defender_id:
                    engine.adjust_trust(nation_id, defender_id, -0.2)
                    engine.adjust_trust(defender_id, nation_id, -0.2)
        
        elif unit_type == UnitType.AIRCRAFT:
            # Air strike: combat but no conquest
            from geomas.actions.defense.combat import resolve_air_strike
            
            defender_id = to_province.owner_id
            
            result = resolve_air_strike(
                attacker_aircraft=quantity,
                defender_province=to_province,
                rng=rng
            )
            
            engine.logs.append(f"[COMBAT] {result.log_message}")
            
            if result.attacker_wins:
                # Aircraft wins: kill all defenders and return to base
                defender_nation = world.nations.get(defender_id)
                if defender_nation:
                    defender_nation.total_soldiers -= to_province.soldiers
                    defender_nation.total_aircraft -= to_province.aircraft
                
                to_province.soldiers = 0
                to_province.aircraft = 0
                
                # Return aircraft to source
                _add_units_to_province(from_province, unit_type, quantity)
                engine.logs.append(
                    f"[COMBAT] Air strike successful! {quantity} aircraft return to base"
                )
            else:
                # Aircraft destroyed
                nation.total_aircraft -= quantity
                engine.logs.append(
                    f"[COMBAT] Air strike failed - {quantity} aircraft shot down"
                )
            
            # Trust impact
            if defender_id:
                engine.adjust_trust(nation_id, defender_id, -0.2)
                engine.adjust_trust(defender_id, nation_id, -0.2)
        
        return
    
    # Friendly territory - validate destination terrain
    if not can_place_unit(unit_type, to_province.terrain):
        # Refund - return units to source
        _add_units_to_province(from_province, unit_type, quantity)
        nation.total_energy += total_energy_cost  # Refund energy
        engine.logs.append(
            f"[DEFENSE] MOVE_TROOPS: Cannot move {unit_type.value} to {to_province.terrain.value} terrain"
        )
        return
    
    # --- EXECUTE: Move units to friendly territory ---
    _add_units_to_province(to_province, unit_type, quantity)
    
    engine.logs.append(
        f"[DEFENSE] Moved {quantity}x {unit_type.value} from {from_province_id} to {to_province_id}. "
        f"Distance: {distance}, Energy: {total_energy_cost:.1f}"
    )


def _get_units_in_province(province, unit_type: UnitType) -> int:
    """Get the number of units of a type in a province."""
    if unit_type == UnitType.SOLDIER:
        return province.soldiers
    elif unit_type == UnitType.NAVY:
        return province.navy
    elif unit_type == UnitType.AIRCRAFT:
        return province.aircraft
    return 0


def _remove_units_from_province(province, unit_type: UnitType, quantity: int) -> None:
    """Remove units from a province."""
    if unit_type == UnitType.SOLDIER:
        province.soldiers -= quantity
    elif unit_type == UnitType.NAVY:
        province.navy -= quantity
    elif unit_type == UnitType.AIRCRAFT:
        province.aircraft -= quantity


def _add_units_to_province(province, unit_type: UnitType, quantity: int) -> None:
    """Add units to a province."""
    if unit_type == UnitType.SOLDIER:
        province.soldiers += quantity
    elif unit_type == UnitType.NAVY:
        province.navy += quantity
    elif unit_type == UnitType.AIRCRAFT:
        province.aircraft += quantity


def _find_valid_path(
    engine: 'ActionEngine',
    nation_id: str,
    from_id: int,
    to_id: int,
    unit_type: UnitType
) -> Optional[List[int]]:
    """
    Find a valid path for unit type from source to destination.
    
    - SOLDIER: Must move through owned land provinces (or allied)
    - NAVY: Must move through ocean provinces (own territorial + international waters)
    - AIRCRAFT: Can fly over any terrain to any valid landing spot
    """
    world = engine.world
    nation = world.nations[nation_id]
    
    if unit_type == UnitType.AIRCRAFT:
        # Aircraft can fly directly (simplified - no terrain restriction in path)
        path = engine.spatial.get_shortest_path(from_id, to_id)
        return path
    
    elif unit_type == UnitType.NAVY:
        # Navy must travel through ocean provinces
        path = engine.spatial.get_shortest_path(from_id, to_id)
        if path is None:
            return None
        
        # Validate all intermediate provinces are ocean
        for p_id in path[1:-1]:  # Exclude start and end
            prov = world.provinces.get(p_id)
            if not prov or prov.terrain != TerrainType.OCEAN:
                return None  # Path crosses non-ocean terrain
        
        # Destination must be ocean
        dest_prov = world.provinces.get(to_id)
        if dest_prov and dest_prov.terrain != TerrainType.OCEAN:
            return None
        
        return path
    
    else:  # SOLDIER
        # Soldiers must move through owned/allied land provinces
        path = engine.spatial.get_shortest_path(from_id, to_id)
        if path is None:
            return None
        
        # Validate all intermediate provinces are owned
        for p_id in path[1:-1]:  # Exclude start and end (end can be enemy for attack)
            prov = world.provinces.get(p_id)
            if not prov:
                return None
            
            # Must be owned land (not ocean)
            if prov.terrain == TerrainType.OCEAN:
                return None
            
            # Must be owned by us (or allied - simplified for now to just owned)
            if prov.owner_id != nation_id:
                return None
        
        return path


def _is_enemy_territory(world, nation_id: str, province_id: int, unit_type: UnitType) -> bool:
    """Check if the destination is enemy territory."""
    province = world.provinces.get(province_id)
    if not province:
        return False
    
    nation = world.nations.get(nation_id)
    if not nation:
        return False
    
    if unit_type == UnitType.NAVY:
        # For navy, enemy = not in our territorial waters
        return province_id not in nation.territorial_water_ids
    
    # For land units, enemy = owned by someone else
    return province.owner_id is not None and province.owner_id != nation_id
