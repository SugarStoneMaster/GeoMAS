"""
Defense Action Handler.

Executes military/defense actions using waterfall priority logic.
"""

from typing import TYPE_CHECKING, Optional, List
from geomas.actions.defense.schemas import (
    DefenseActionType, 
    DefensePayload,
    DefenseActionItem,
    UnitType,
    UNIT_COSTS,
    MOVEMENT_ENERGY_COST,
    MOVEMENT_RANGE,
    can_afford_unit,
    can_place_unit,
    get_terrain_defense_bonus,
)
from geomas.schemas.world import TerrainType, RelationshipState

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
    # Sort by priority (1 is highest) and limit to 3 actions
    moves = sorted(payload.moves, key=lambda x: x.priority)[:3]
    
    if len(payload.moves) > 3:
        engine.logs.append(f"⚔️ [DEFENSE] Warning: {nation_id} proposed {len(payload.moves)} actions. Truncating to 3 (highest priority).")
    
    nation = engine.world.nations.get(nation_id)
    if not nation:
        engine.logs.append(f"⚔️ [DEFENSE] Unknown nation: {nation_id}")
        return
    
    for move in moves:
        if move.action_type == DefenseActionType.CREATE_UNIT:
            _execute_create_unit(engine, nation_id, move)
            
        elif move.action_type == DefenseActionType.MOVE_TROOPS:
            _execute_move_troops(engine, nation_id, move)
            
        elif move.action_type == DefenseActionType.NUCLEAR_OPTION:
            _execute_nuclear_option(engine, nation_id, move)


def _execute_create_unit(
    engine: 'ActionEngine',
    nation_id: str,
    move: DefenseActionItem
) -> None:
    """
    Execute CREATE_UNIT action.
    Uses move.unit_type, move.quantity, move.target_province_id.
    """
    world = engine.world
    nation = world.nations[nation_id]
    
    # Parse parameters
    # Parse parameters from explicit fields
    unit_type = move.unit_type or UnitType.SOLDIER
    quantity = move.quantity or 1
    province_id = move.target_province_id
    target_nation_id = move.target_nation_id
    
    # CREATE_UNIT always creates for SELF regardless of target_nation_id
    if target_nation_id and target_nation_id != nation_id:
        engine.logs.append(
            f"🛠️ [DEFENSE] CREATE_UNIT: target_nation_id corrected from {target_nation_id} to {nation_id}"
        )
    target_nation_id = nation_id
    
    # Validate unit type
    # unit_type is already an Enum or None, validated by Pydantic if parsed correctly
    # If it's None, we defaulted to SOLDIER above.
    
    # Validate province specified
    if province_id is None:
        move.execution_outcome.status = "FAILED"
        move.execution_outcome.reason = "No province_id specified"
        engine.logs.append(f"⚔️ [DEFENSE] CREATE_UNIT failed: No province_id specified")
        return
    
    # Validate province exists and is owned
    province = world.provinces.get(province_id)
    if not province:
        move.execution_outcome.status = "FAILED"
        move.execution_outcome.reason = f"Province {province_id} does not exist"
        engine.logs.append(f"⚔️ [DEFENSE] Province {province_id} does not exist")
        return
    
    # For NAVY, check territorial waters; for others, check owned land
    if unit_type == UnitType.NAVY:
        if province_id not in nation.territorial_water_ids:
            move.execution_outcome.status = "FAILED"
            move.execution_outcome.reason = f"Province {province_id} is not in territorial waters"
            engine.logs.append(f"⚔️ [DEFENSE] Province {province_id} is not in territorial waters")
            return
    else:
        if province.owner_id != nation_id:
            move.execution_outcome.status = "FAILED"
            move.execution_outcome.reason = f"Province {province_id} not owned by {nation_id}"
            engine.logs.append(f"⚔️ [DEFENSE] Province {province_id} not owned by {nation_id}")
            return
    
    # Validate terrain constraint
    if not can_place_unit(unit_type, province.terrain):
        move.execution_outcome.status = "FAILED"
        move.execution_outcome.reason = f"Cannot place {unit_type.value} on {province.terrain.value} terrain"
        engine.logs.append(
            f"⚔️ [DEFENSE] Cannot place {unit_type.value} on {province.terrain.value} terrain"
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
        move.execution_outcome.status = "FAILED"
        move.execution_outcome.reason = reason
        engine.logs.append(f"⚔️ [DEFENSE] CREATE_UNIT failed: {reason}")
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
    
    # Final Success
    move.execution_outcome.status = "SUCCESS"
    move.execution_outcome.details = {
        "unit_type": unit_type.value,
        "quantity": quantity,
        "province_id": province_id,
        "budget_spent": total_budget,
        "materials_spent": total_materials
    }

    engine.logs.append(
        f"🛠️ [DEFENSE] Created {quantity}x {unit_type.value} in province {province_id}. "
        f"Cost: {total_budget:.1f} budget, {total_materials:.1f} materials"
    )


def _execute_move_troops(
    engine: 'ActionEngine',
    nation_id: str,
    move: DefenseActionItem
) -> None:
    """
    Execute MOVE_TROOPS action.
    Uses move.unit_type, move.quantity, move.source_province_id, move.target_province_id.
    """
    world = engine.world
    nation = world.nations[nation_id]
    
    # Parse parameters
    # Parse parameters
    unit_type = move.unit_type or UnitType.SOLDIER
    quantity = move.quantity or 1
    from_province_id = move.source_province_id
    to_province_id = move.target_province_id
    
    # Validate unit type
    # unit_type is Enum
    
    # Validate provinces specified
    if from_province_id is None or to_province_id is None:
        move.execution_outcome.status = "FAILED"
        move.execution_outcome.reason = "Source or destination province not specified"
        engine.logs.append(f"🚚 [DEFENSE] MOVE_TROOPS: Must specify from_province_id and to_province_id")
        return
    
    # Guard: same-province move is a no-op
    if from_province_id == to_province_id:
        move.execution_outcome.status = "SUCCESS"
        move.execution_outcome.reason = "Source and destination are the same"
        engine.logs.append(f"🚚 [DEFENSE] MOVE_TROOPS: Source and destination are the same ({from_province_id}), skipping")
        return
    
    # Validate provinces exist
    from_province = world.provinces.get(from_province_id)
    to_province = world.provinces.get(to_province_id)
    
    if not from_province:
        move.execution_outcome.status = "FAILED"
        move.execution_outcome.reason = f"Source province {from_province_id} does not exist"
        engine.logs.append(f"🚚 [DEFENSE] MOVE_TROOPS: Source province {from_province_id} does not exist")
        return
    if not to_province:
        move.execution_outcome.status = "FAILED"
        move.execution_outcome.reason = f"Destination province {to_province_id} does not exist"
        engine.logs.append(f"🚚 [DEFENSE] MOVE_TROOPS: Destination province {to_province_id} does not exist")
        return
    
    # Validate ownership of source province
    if unit_type == UnitType.NAVY:
        if from_province_id not in nation.territorial_water_ids:
            move.execution_outcome.status = "FAILED"
            move.execution_outcome.reason = f"Source {from_province_id} not in territorial waters"
            engine.logs.append(f"🚚 [DEFENSE] MOVE_TROOPS: Source {from_province_id} not in territorial waters")
            return
    else:
        # Allow move if Owner OR if Guest Troops present
        has_guest_troops = from_province.guest_troops and nation_id in from_province.guest_troops
        if from_province.owner_id != nation_id and not has_guest_troops:
            move.execution_outcome.status = "FAILED"
            move.execution_outcome.reason = f"Source {from_province_id} not owned by {nation_id} and no guest troops present"
            engine.logs.append(f"🚚 [DEFENSE] MOVE_TROOPS: Source {from_province_id} not owned by {nation_id}")
            return
    
    # Relaxed validation for target_nation_id in MOVE_TROOPS
    # If specified, we just warn if mismatch, but rely on province ownership for mechanics
    if to_province and to_province.owner_id and move.target_nation_id:
        if move.target_nation_id != to_province.owner_id:
            # Just a warning, proceed with the actual province owner
            pass
    
    # Validate units available in source — clamp to available if exceeds
    # Validate units available in source — clamp to available if exceeds
    available_units = _get_units_in_province(from_province, unit_type, nation_id)
    if available_units <= 0:
        move.execution_outcome.status = "FAILED"
        move.execution_outcome.reason = f"No {unit_type.value} in province {from_province_id}"
        engine.logs.append(
            f"🚚 [DEFENSE] MOVE_TROOPS: No {unit_type.value} in province {from_province_id}"
        )
        return
    if available_units < quantity:
        engine.logs.append(
            f"🚚 [DEFENSE] MOVE_TROOPS: Clamped {unit_type.value} from {quantity} to {available_units} "
            f"(province {from_province_id} only has {available_units})"
        )
        quantity = available_units
    
    # Validate path exists and is valid for unit type
    path = _find_valid_path(engine, nation_id, from_province_id, to_province_id, unit_type)
    if path is None:
        move.execution_outcome.status = "FAILED"
        move.execution_outcome.reason = f"No valid path from {from_province_id} to {to_province_id} for {unit_type.value}"
        engine.logs.append(
            f"🚚 [DEFENSE] MOVE_TROOPS: No valid path from {from_province_id} to {to_province_id} "
            f"for {unit_type.value}"
        )
        return
    
    # Calculate distance (path includes start and end)
    distance = len(path) - 1
    
    # Validate range
    max_range = MOVEMENT_RANGE[unit_type]
    if distance > max_range:
        move.execution_outcome.status = "FAILED"
        move.execution_outcome.reason = f"Distance {distance} exceeds {unit_type.value} range of {max_range}"
        engine.logs.append(
            f"🚚 [DEFENSE] MOVE_TROOPS: Distance {distance} exceeds {unit_type.value} range of {max_range}"
        )
        return
    
    # Calculate and validate energy cost
    energy_per_unit = MOVEMENT_ENERGY_COST[unit_type]
    total_energy_cost = energy_per_unit * quantity * distance
    
    if nation.total_energy < total_energy_cost:
        move.execution_outcome.status = "FAILED"
        move.execution_outcome.reason = f"Insufficient energy: need {total_energy_cost:.1f}, have {nation.total_energy:.1f}"
        engine.logs.append(
            f"🚚 [DEFENSE] MOVE_TROOPS: Insufficient energy. Need {total_energy_cost:.1f}, have {nation.total_energy:.1f}"
        )
        return
    
    # Validating if it's actually an attack or just guest stationing
    is_enemy = _is_enemy_territory(world, nation_id, to_province_id, unit_type)
    
    if is_enemy:
        target_owner = to_province.owner_id
        rel = world.relationship_matrix.get(nation_id, {}).get(target_owner, RelationshipState.PEACE)
        if rel in [RelationshipState.MUTUAL_DEFENSE, RelationshipState.NON_AGGRESSION]:
            is_enemy = False # It's a friendly stationing
            engine.logs.append(f"🛡️ [DEFENSE] Stationing {quantity} {unit_type.value} in Allied {target_owner} province {to_province_id}")
    
    # --- EXECUTE: Deduct energy first ---
    nation.total_energy -= total_energy_cost
    
    # Remove units from source
    _remove_units_from_province(from_province, unit_type, quantity, nation_id)
    
    if is_enemy:
        # Check for ALLIANCE BETRAYAL (New Logic)
        target_id = to_province.owner_id
        if target_id:
            rel = world.relationship_matrix.get(nation_id, {}).get(target_id, RelationshipState.PEACE)
            if rel in (RelationshipState.MUTUAL_DEFENSE, RelationshipState.NON_AGGRESSION):
                # IMMEDIATE RUPTURE
                world.relationship_matrix[nation_id][target_id] = RelationshipState.WAR
                world.relationship_matrix[target_id][nation_id] = RelationshipState.WAR
                
                # Massive Trust Penalty
                engine.adjust_trust(nation_id, target_id, -50.0)
                engine.adjust_trust(target_id, nation_id, -50.0)
                
                # --- INIT WAR STATS ---
                from geomas.schemas.world import WarStats
                aggressor = world.nations[nation_id]
                victim = world.nations[target_id]
                
                if target_id not in aggressor.active_wars:
                    aggressor.active_wars[target_id] = WarStats(
                        start_turn=world.turn,
                        original_provinces=len(aggressor.province_ids)
                    )
                if nation_id not in victim.active_wars:
                    victim.active_wars[nation_id] = WarStats(
                        start_turn=world.turn,
                        original_provinces=len(victim.province_ids)
                    )

                engine.logs.append(
                    f"💔 [DIPLOMACY] {nation_id} BROKE ALLIANCE by attacking {target_id}! Relationship set to WAR."
                )

        # Combat resolution
        from geomas.actions.defense.combat import (
            resolve_land_combat,
            execute_naval_landing,
            _conquer_province,
        )
        import random
        rng = random.Random(engine.world.turn + hash(nation_id))
        
        # --- SUICIDE CHECK ---
        # Prevent attacks with negligible forces (<10% of defenders)
        defending_force = 0
        if unit_type == UnitType.SOLDIER:
            defending_force = to_province.soldiers
        elif unit_type == UnitType.NAVY:
            defending_force = to_province.navy
        elif unit_type == UnitType.AIRCRAFT:
            defending_force = to_province.aircraft
            
        # Apply terrain defense bonus to estimate effective defense strength
        defense_bonus = get_terrain_defense_bonus(to_province.terrain)
        effective_defense = defending_force * defense_bonus
        
        if defending_force > 0 and quantity < (effective_defense * 0.1):
            # Just warn, do NOT abort (User preference: let LLM makes its own mistakes)
            engine.logs.append(
                f"⚔️ [COMBAT] ⚠️ RISKY ATTACK: {quantity} {unit_type.value} vs {defending_force} defenders "
                f"(Effective Defense: {int(effective_defense)}). High probability of defeat."
            )
            # Proceed with combat...

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
            
            # Update outcome
            move.execution_outcome.status = "SUCCESS" if result.attacker_wins else "FAILED"
            move.execution_outcome.reason = result.log_message
            move.execution_outcome.details = {
                "attacker_wins": result.attacker_wins,
                "landing_province_id": result.landing_province_id,
                "attacker_losses_navy": quantity,  # Navy is consumed on landing in this version
                "defender_losses": result.defender_losses_navy if hasattr(result, 'defender_losses_navy') else 0
            }
            
            engine.logs.append(f"⚔️ [COMBAT] {result.log_message}")
            
            if result.attacker_wins:
                engine.logs.append(
                    f"⚔️ [COMBAT] Naval landing successful at province {result.landing_province_id}"
                )
            else:
                engine.logs.append(f"⚔️ [COMBAT] Naval assault failed - all ships lost")
        
        elif unit_type == UnitType.SOLDIER:
            # Land combat
            result = resolve_land_combat(
                attacker_soldiers=quantity,
                defender_province=to_province,
                rng=rng
            )
            
            # Update outcome
            move.execution_outcome.status = "SUCCESS" if result.attacker_wins else "FAILED"
            move.execution_outcome.reason = result.log_message
            move.execution_outcome.details = {
                "attacker_wins": result.attacker_wins,
                "attacker_losses": result.attacker_losses,
                "defender_losses": result.defender_losses
            }

            engine.logs.append(f"⚔️ [COMBAT] {result.log_message}")
            
            if result.attacker_wins:
                # Conquer the province
                old_owner = to_province.owner_id
                _conquer_province(world, nation_id, to_province)
                
                # Place attacking soldiers in conquered province
                to_province.soldiers = quantity
                nation.total_soldiers += quantity  # They were removed but now added back
                
                # Determine who lost the province for better logging
                lost_by = f" (lost by {old_owner})" if old_owner else " (from NEUTRAL)"
                engine.logs.append(
                    f"🚩 [COMBAT] Province {to_province_id} conquered by {nation_id}{lost_by}"
                )
                
                # Trust impact: combat causes trust decrease
                if old_owner:
                    engine.adjust_trust(nation_id, old_owner, -20)  # 0-100 scale
                    engine.adjust_trust(old_owner, nation_id, -20)
                    engine.logs.append(f"💔 [DIPLOMACY] Trust between {nation_id} and {old_owner} decreased")
            else:
                # Attacker loses all soldiers
                nation.total_soldiers -= quantity
                engine.logs.append(
                    f"⚔️ [COMBAT] Attack failed - {quantity} soldiers lost"
                )
                
                # Trust impact even on failed attack
                defender_id = to_province.owner_id
                if defender_id:
                    engine.adjust_trust(nation_id, defender_id, -20)
                    engine.adjust_trust(defender_id, nation_id, -20)
        
        elif unit_type == UnitType.AIRCRAFT:
            # Air strike: combat but no conquest
            from geomas.actions.defense.combat import resolve_air_strike
            
            defender_id = to_province.owner_id
            
            result = resolve_air_strike(
                attacker_aircraft=quantity,
                defender_province=to_province,
                rng=rng
            )
            
            # Update outcome
            move.execution_outcome.status = "SUCCESS" if result.attacker_wins else "FAILED"
            move.execution_outcome.reason = result.log_message
            move.execution_outcome.details = {
                "attacker_wins": result.attacker_wins,
                "attacker_losses": result.attacker_losses,
                "defender_losses": result.defender_losses
            }

            engine.logs.append(f"⚔️ [COMBAT] {result.log_message}")
            
            if result.attacker_wins:
                # Aircraft wins: kill all defenders and return to base
                defender_nation = world.nations.get(defender_id)
                if defender_nation:
                    defender_nation.total_soldiers -= to_province.soldiers
                    defender_nation.total_aircraft -= to_province.aircraft
                
                to_province.soldiers = 0
                to_province.aircraft = 0
                
                # Return aircraft to source
                _add_units_to_province(from_province, unit_type, quantity, nation_id)
                engine.logs.append(
                    f"⚔️ [COMBAT] Air strike successful! {quantity} aircraft return to base"
                )
            else:
                # Aircraft destroyed
                nation.total_aircraft -= quantity
                engine.logs.append(
                    f"⚔️ [COMBAT] Air strike failed - {quantity} aircraft shot down"
                )
            
            # Trust impact
            if defender_id:
                engine.adjust_trust(nation_id, defender_id, -20)
                engine.adjust_trust(defender_id, nation_id, -20)
        
        return
    
    # Friendly territory - validate destination terrain
    if not can_place_unit(unit_type, to_province.terrain):
        # Refund - return units to source
        _add_units_to_province(from_province, unit_type, quantity, nation_id)
        nation.total_energy += total_energy_cost  # Refund energy
        move.execution_outcome.status = "FAILED"
        move.execution_outcome.reason = f"Cannot move {unit_type.value} to {to_province.terrain.value} terrain"
        engine.logs.append(
            f"🚚 [DEFENSE] MOVE_TROOPS: Cannot move {unit_type.value} to {to_province.terrain.value} terrain"
        )
        return
    
    # --- EXECUTE: Move units to friendly territory ---
    # --- EXECUTE: Move units to friendly territory ---
    _add_units_to_province(to_province, unit_type, quantity, nation_id)
    
    # Success Outcome
    move.execution_outcome.status = "SUCCESS"
    move.execution_outcome.reason = "Reinforcement arrived"
    move.execution_outcome.details = {
        "unit_type": unit_type.value,
        "quantity": quantity,
        "from": from_province_id,
        "to": to_province_id,
        "energy_spent": total_energy_cost
    }

    engine.logs.append(
        f"🚚 [DEFENSE] Moved {quantity}x {unit_type.value} from {from_province_id} to {to_province_id}. "
        f"Distance: {distance}, Energy: {total_energy_cost:.1f}"
    )


def _get_units_in_province(province, unit_type: UnitType, nation_id: str = None) -> int:
    """Get the number of units of a type in a province for a specific nation."""
    
    # If nation_id is None or matches owner, use standard fields
    if nation_id is None or nation_id == province.owner_id:
        if unit_type == UnitType.SOLDIER:
            return province.soldiers
        elif unit_type == UnitType.NAVY:
            return province.navy
        elif unit_type == UnitType.AIRCRAFT:
            return province.aircraft
            
    # If Guest (Allied Stationing)
    elif province.guest_troops and nation_id in province.guest_troops:
        guest_force = province.guest_troops[nation_id]
        if unit_type == UnitType.SOLDIER:
            return guest_force.get("soldiers", 0)
        elif unit_type == UnitType.AIRCRAFT:
            return guest_force.get("aircraft", 0)
            
    return 0


def _remove_units_from_province(province, unit_type: UnitType, quantity: int, nation_id: str = None) -> None:
    """Remove units from a province."""
    
    # Standard Owner Removal
    if nation_id is None or nation_id == province.owner_id:
        if unit_type == UnitType.SOLDIER:
            province.soldiers -= quantity
        elif unit_type == UnitType.NAVY:
            province.navy -= quantity
        elif unit_type == UnitType.AIRCRAFT:
            province.aircraft -= quantity
            
    # Guest Removal
    elif province.guest_troops and nation_id in province.guest_troops:
        guest_force = province.guest_troops[nation_id]
        key = "soldiers" if unit_type == UnitType.SOLDIER else "aircraft"
        
        if key in guest_force:
            guest_force[key] -= quantity
            # Cleanup if empty
            if guest_force[key] <= 0:
                del guest_force[key]
        
        if not guest_force:
            del province.guest_troops[nation_id]


def _add_units_to_province(province, unit_type: UnitType, quantity: int, nation_id: str = None) -> None:
    """Add units to a province (Owner or Guest)."""
    
    # Standard Owner Addition
    if nation_id is None or nation_id == province.owner_id:
        if unit_type == UnitType.SOLDIER:
            province.soldiers += quantity
        elif unit_type == UnitType.NAVY:
            province.navy += quantity
        elif unit_type == UnitType.AIRCRAFT:
            province.aircraft += quantity
            
    # Guest Addition (Allied Stationing)
    else:
        if province.guest_troops is None:
            province.guest_troops = {}
            
        if nation_id not in province.guest_troops:
            province.guest_troops[nation_id] = {"soldiers": 0, "aircraft": 0}
            
        guest_force = province.guest_troops[nation_id]
        
        if unit_type == UnitType.SOLDIER:
            guest_force["soldiers"] += quantity
        elif unit_type == UnitType.AIRCRAFT:
            guest_force["aircraft"] += quantity
        # Navy cannot be guest (must be in water)


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
        
        # Validate all intermediate provinces are owned OR allied
        for p_id in path[1:-1]:  # Exclude start and end (end can be enemy for attack)
            prov = world.provinces.get(p_id)
            if not prov:
                return None
            
            # Must be owned land (not ocean)
            if prov.terrain == TerrainType.OCEAN:
                return None
            
            # 1. Check Ownership
            if prov.owner_id == nation_id:
                continue
                
            # 2. Check Alliance (Access Rights)
            # If not owned, must be an ally (Mutual Defense or Non-Aggression)
            owner_id = prov.owner_id
            if not owner_id:
                 return None # Cannot move through unclaimed land (unless we conquer it step by step, which requires separate moves)
            
            relationship = world.relationship_matrix.get(nation_id, {}).get(owner_id, RelationshipState.PEACE)
            
            # User Rule: "Se C è neutrale... lasci passare le truppe. Se C è alleata... ha senso".
            # We strictly allow access only for treaties. PEACE (Neutral) is NOT enough.
            if relationship not in [RelationshipState.MUTUAL_DEFENSE, RelationshipState.NON_AGGRESSION]:
                engine.logs.append(f"⛔ [DEFENSE] Cannot move through neutral/hostile {owner_id} (Province {p_id}). Relation: {relationship}")
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
    
    # For land units, enemy = NOT owned by us (includes neutral)
    return province.owner_id != nation_id


def _execute_nuclear_option(
    engine: 'ActionEngine',
    nation_id: str,
    move: DefenseActionItem
) -> None:
    """
    Execute a nuclear strike on a target province.
    
    Effects:
    - All military units in target → 0
    - Population × 0.1 (90% death)
    - Production × 0.2 (80% destroyed)
    - Trust with victim → 0
    - Trust with ALL other nations -= 80 (0-100 scale)
    """
    world = engine.world
    nation = world.nations.get(nation_id)
    
    if not nation:
        engine.logs.append(f"☢️ [NUCLEAR] Nation {nation_id} not found")
        return
    
    # Use explicit fields from DefenseActionItem
    target_province_id = move.target_province_id
    quantity = move.quantity or 1
    target_nation_id = move.target_nation_id

    # Validate target_nation_id (Input Check)
    if target_nation_id is None:
        move.execution_outcome.status = "FAILED"
        move.execution_outcome.reason = "Missing target_nation_id"
        engine.logs.append("☢️ [NUCLEAR] Missing target_nation_id")
        return

    if target_nation_id == nation_id:
        move.execution_outcome.status = "FAILED"
        move.execution_outcome.reason = "Cannot target SELF"
        engine.logs.append("☢️ [NUCLEAR] Cannot target SELF with nuclear option")
        return
    
    if target_province_id is None:
        move.execution_outcome.status = "FAILED"
        move.execution_outcome.reason = "Missing target_province_id"
        engine.logs.append("☢️ [NUCLEAR] Missing target_province_id")
        return
    
    # Validate: has nukes
    if nation.nukes < quantity:
        move.execution_outcome.status = "FAILED"
        move.execution_outcome.reason = f"Insufficient nukes. Have {nation.nukes}, need {quantity}"
        engine.logs.append(
            f"☢️ [NUCLEAR] Insufficient nukes. Have {nation.nukes}, need {quantity}"
        )
        return
    
    # Validate: target exists
    target_province = world.provinces.get(target_province_id)
    if not target_province:
        move.execution_outcome.status = "FAILED"
        move.execution_outcome.reason = f"Target province {target_province_id} not found"
        engine.logs.append(f"☢️ [NUCLEAR] Target province {target_province_id} not found")
        return
    
    # Validate: cannot nuke OCEAN or VOID terrain (no effect)
    from geomas.schemas.world import TerrainType
    if target_province.terrain in (TerrainType.OCEAN, TerrainType.VOID):
        move.execution_outcome.status = "FAILED"
        move.execution_outcome.reason = f"Cannot nuke {target_province.terrain.value} province"
        engine.logs.append(
            f"☢️ [NUCLEAR] Cannot nuke {target_province.terrain.value} province {target_province_id}"
        )
        return

    victim_id = target_province.owner_id

    # Validate target_nation_id matches province owner (Consistency Check)
    if target_nation_id != victim_id:
        move.execution_outcome.status = "FAILED"
        move.execution_outcome.reason = f"target_nation_id {target_nation_id} mismatch with owner {victim_id}"
        engine.logs.append(
            f"☢️ [NUCLEAR] target_nation_id {target_nation_id} does not match "
            f"province owner {victim_id}"
        )
        return
    
    # Validate: not own territory (Redundant but explicit safety)
    if victim_id == nation_id:
        engine.logs.append("☢️ [NUCLEAR] Cannot nuke own territory")
        return
    
    # --- EXECUTE ---
    
    # --- CHECK ALLIANCE BREAK ---
    # --- CHECK ALLIANCE BREAK / WAR START ---
    if victim_id:
        rel = world.relationship_matrix.get(nation_id, {}).get(victim_id, RelationshipState.PEACE)
        
        # Launching a nuke ALWAYS starts a war if not already at war
        if rel != RelationshipState.WAR:
            world.relationship_matrix[nation_id][victim_id] = RelationshipState.WAR
            world.relationship_matrix[victim_id][nation_id] = RelationshipState.WAR
            
            # --- INIT WAR STATS ---
            from geomas.schemas.world import WarStats
            aggressor = world.nations[nation_id]
            victim = world.nations.get(victim_id)
            
            if victim:
                if victim_id not in aggressor.active_wars:
                    aggressor.active_wars[victim_id] = WarStats(
                        start_turn=world.turn,
                        original_provinces=len(aggressor.province_ids)
                    )
                if nation_id not in victim.active_wars:
                    victim.active_wars[nation_id] = WarStats(
                        start_turn=world.turn,
                        original_provinces=len(victim.province_ids)
                    )

            if rel in (RelationshipState.MUTUAL_DEFENSE, RelationshipState.NON_AGGRESSION):
                engine.logs.append(
                    f"💔 [DIPLOMACY] {nation_id} BROKE ALLIANCE by nuking {victim_id}! Relationship set to WAR."
                )
            else:
                 engine.logs.append(
                    f"⚔️ [DIPLOMACY] {nation_id} started WAR with {victim_id} by nuclear aggression."
                )

    # Consume nuke
    nation.nukes -= quantity
    
    # Store pre-strike values for logging
    pre_soldiers = target_province.soldiers
    pre_aircraft = target_province.aircraft
    pre_navy = target_province.navy
    pre_pop = target_province.population
    
    # Update victim nation totals
    if victim_id:
        victim_nation = world.nations.get(victim_id)
        if victim_nation:
            victim_nation.total_soldiers -= target_province.soldiers
            victim_nation.total_aircraft -= target_province.aircraft
            victim_nation.total_navy -= target_province.navy
    
    # Devastating effects on province
    target_province.soldiers = 0
    target_province.navy = 0
    target_province.aircraft = 0
    target_province.population = int(target_province.population * 0.1)
    target_province.workers = int(target_province.workers * 0.1)
    target_province.food_production *= 0.2
    target_province.materials_production *= 0.2
    target_province.energy_production *= 0.2
    
    # Success Outcome
    move.execution_outcome.status = "SUCCESS"
    move.execution_outcome.reason = "Nuclear strike successful"
    move.execution_outcome.details = {
        "target_province": target_province_id,
        "victim_id": victim_id,
        "death_toll": pre_pop - target_province.population
    }
    
    engine.logs.append(
        f"☢️ [NUCLEAR] {nation_id} nukes province {target_province_id}! "
        f"Casualties: {pre_soldiers} soldiers, {pre_aircraft} aircraft, {pre_navy} navy. "
        f"Population: {pre_pop} → {target_province.population}"
    )
    
    # --- DIPLOMATIC FALLOUT ---
    
    # Trust with victim → 0
    if victim_id:
        engine.world.trust_matrix.setdefault(nation_id, {})[victim_id] = 0
        engine.world.trust_matrix.setdefault(victim_id, {})[nation_id] = 0
        engine.logs.append(f"💔 [DIPLOMACY] Trust between {nation_id} and {victim_id} → 0")
    
    # ALL other nations: trust -= 80 toward attacker (high penalty)
    for other_nation_id in world.nations:
        if other_nation_id != nation_id and other_nation_id != victim_id:
            engine.adjust_trust(other_nation_id, nation_id, -80)
            engine.logs.append(
                f"💔 [DIPLOMACY] {other_nation_id}'s trust toward {nation_id} decreased by 80"
            )
