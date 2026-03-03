"""
Defense Action Handler.

Executes military/defense actions using waterfall priority logic.
"""

from typing import TYPE_CHECKING, Optional, List
from geomas.calculators.consumption import calculate_bureaucracy_multiplier
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
from geomas.schemas.world import TerrainType, RelationshipState, WarStats
from geomas.actions.foreign.handler import _generate_call_to_arms

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
            
        elif move.action_type == DefenseActionType.IDLE:
            move.execution_outcome.status = "SUCCESS"
            move.execution_outcome.reason = "Minister is idle."


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
    
    bureaucracy_mult = calculate_bureaucracy_multiplier(nation)
    total_budget = costs["budget"] * quantity * bureaucracy_mult
    total_materials = costs["materials"] * quantity * bureaucracy_mult
    total_energy = costs["energy"] * quantity * bureaucracy_mult
    total_pop = int(costs["population"]) * quantity
    
    # Validate affordability
    can_afford, reason = can_afford_unit(
        unit_type=unit_type,
        quantity=quantity,
        budget=nation.total_budget,
        materials=nation.total_materials,
        energy=nation.total_energy,
        available_population=nation.total_workers,
        bureaucracy_multiplier=bureaucracy_mult
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
    
    # Identify ALL defending nations for fallout (owner + guests)
    defending_nations = set()
    if to_province.owner_id:
        defending_nations.add(to_province.owner_id)
    if to_province.guest_troops:
        defending_nations.update(to_province.guest_troops.keys())
    
    # For navy, also consider territorial water owners as defenders
    if unit_type == UnitType.NAVY:
        for n_id, n_state in world.nations.items():
            if to_province.id in n_state.territorial_water_ids:
                defending_nations.add(n_id)
        # FIX: Also add nations with guest naval troops in this water province.
        if to_province.guest_troops:
            for guest_id, guest_force in to_province.guest_troops.items():
                if guest_force.get("navy", 0) > 0:
                    defending_nations.add(guest_id)

    if nation_id in defending_nations:
        defending_nations.remove(nation_id)

    # Determine if this is an attack or a friendly move (Stationing)
    is_attack = False

    # FIX: Unowned (neutral) territory is always an attack target — move soldiers into it to conquer.
    if to_province.owner_id is None and unit_type == UnitType.SOLDIER:
        is_attack = True

    # Check if we are attacking the owner OR any guests
    for def_id in defending_nations:
        rel = world.relationship_matrix.get(nation_id, {}).get(def_id, RelationshipState.PEACE)
        # If any force present is an ENEMY (War or Peace), it's an attack.
        # Allies (MUTUAL_DEFENSE, NON_AGGRESSION) or OWN land are NOT targets for attack.
        if rel not in (RelationshipState.MUTUAL_DEFENSE, RelationshipState.NON_AGGRESSION):
            is_attack = True
            break

    # If the province owner is an ENEMY (Neutral or War), it's definitely an attack
    if to_province.owner_id and to_province.owner_id != nation_id:
        rel = world.relationship_matrix.get(nation_id, {}).get(to_province.owner_id, RelationshipState.PEACE)
        if rel not in (RelationshipState.MUTUAL_DEFENSE, RelationshipState.NON_AGGRESSION):
            is_attack = True

    # --- EXECUTE MOVEMENT ---

    # --- EXECUTE: Deduct energy first ---
    nation.total_energy -= total_energy_cost
    
    # Remove units from source
    _remove_units_from_province(from_province, unit_type, quantity, nation_id)

    if is_attack:
        # --- DIPLOMATIC FALLOUT ---
        from geomas.schemas.world import WarStats
        aggressor = world.nations[nation_id]

        for def_nation_id in defending_nations:
            rel = world.relationship_matrix.get(nation_id, {}).get(def_nation_id, RelationshipState.PEACE)
            
            # We hit them if they are an enemy OR if they are an ally that we are hitting by attacking this province
            if rel != RelationshipState.WAR:
                world.relationship_matrix.setdefault(nation_id, {})[def_nation_id] = RelationshipState.WAR
                world.relationship_matrix.setdefault(def_nation_id, {})[nation_id] = RelationshipState.WAR
                
                # Trust penalty for betrayal vs peace aggression
                if rel in (RelationshipState.MUTUAL_DEFENSE, RelationshipState.NON_AGGRESSION):
                    engine.adjust_trust(nation_id, def_nation_id, -50.0)
                    engine.adjust_trust(def_nation_id, nation_id, -50.0)
                    engine.logs.append(
                        f"💔 [DIPLOMACY] {nation_id} BROKE ALLIANCE by attacking {def_nation_id}! Relationship set to WAR."
                    )
                else:
                    engine.logs.append(
                        f"⚔️ [DIPLOMACY] {nation_id} started WAR with {def_nation_id} by aggression."
                    )
                    _generate_call_to_arms(engine, nation_id, def_nation_id, attack_type="SNEAK ATTACKED")

                # Init War Stats
                victim = world.nations.get(def_nation_id)
                if victim:
                    if def_nation_id not in aggressor.active_wars:
                        aggressor.active_wars[def_nation_id] = WarStats(
                            start_turn=world.turn,
                            initiator_id=nation_id,
                            original_provinces=len(victim.province_ids)
                        )
                    if nation_id not in victim.active_wars:
                        victim.active_wars[nation_id] = WarStats(
                            start_turn=world.turn,
                            initiator_id=nation_id,
                            original_provinces=len(victim.province_ids)
                        )

        # --- COMBAT RESOLUTION ---
        from geomas.actions.defense.combat import (
            resolve_land_combat,
            execute_naval_landing,
            _conquer_province,
        )
        import random
        import zlib
        rng = random.Random(engine.world.turn + zlib.adler32(nation_id.encode()))
        
        # Suicide check (Warning but no abort)
        from geomas.actions.defense.combat import get_total_defenders, get_terrain_defense_bonus
        
        defending_force = 0
        if unit_type == UnitType.SOLDIER:
            defending_force, _, _ = get_total_defenders(to_province)
        elif unit_type == UnitType.NAVY:
            _, _, defending_force = get_total_defenders(to_province)
        elif unit_type == UnitType.AIRCRAFT:
            _, defending_force, _ = get_total_defenders(to_province)
            
        defense_bonus = get_terrain_defense_bonus(to_province.terrain)
        effective_defense = defending_force * defense_bonus
        
        if defending_force > 0 and quantity < (effective_defense * 0.1):
            engine.logs.append(
                f"⚔️ [COMBAT] ⚠️ RISKY ATTACK: {quantity} {unit_type.value} vs {defending_force} defenders. High probability of defeat."
            )

        # Branch by Unit Type
        if unit_type == UnitType.NAVY:
            result = execute_naval_landing(world, nation_id, quantity, to_province_id, rng)
            nation.total_navy -= quantity
            move.execution_outcome.status = "SUCCESS" if result.attacker_wins else "FAILED"
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
                _conquer_province(world, nation_id, to_province, engine=engine)
                
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
            
            # --- COMBAT RESOLUTION ---
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
                # Cleanup Units for ALL defending nations
                for def_id in defending_nations:
                    def_nation = world.nations.get(def_id)
                    if def_nation:
                        if def_id == to_province.owner_id:
                            def_nation.total_soldiers -= to_province.soldiers
                            def_nation.total_aircraft -= to_province.aircraft
                        elif def_id in to_province.guest_troops:
                            guest_force = to_province.guest_troops[def_id]
                            def_nation.total_soldiers -= guest_force.get("soldiers", 0)
                            def_nation.total_aircraft -= guest_force.get("aircraft", 0)

                to_province.soldiers = 0
                to_province.aircraft = 0
                to_province.guest_troops.clear()

                # Return aircraft to source
                _add_units_to_province(from_province, unit_type, quantity, nation_id)
                engine.logs.append(
                    f"⚔️ [COMBAT] Air strike successful! {quantity} aircraft return to base"
                )
                
                # Trust impact for ALL defending nations hit
                for def_id in defending_nations:
                    engine.adjust_trust(nation_id, def_id, -20)
                    engine.adjust_trust(def_id, nation_id, -20)
                    engine.logs.append(f"💔 [DIPLOMACY] Trust between {nation_id} and {def_id} decreased")
            else:
                # Aircraft destroyed
                nation.total_aircraft -= quantity
                engine.logs.append(
                    f"⚔️ [COMBAT] Air strike failed - {quantity} aircraft shot down"
                )
        
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
        elif unit_type == UnitType.NAVY:
            return guest_force.get("navy", 0)
            
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
        key = "soldiers" if unit_type == UnitType.SOLDIER else ("aircraft" if unit_type == UnitType.AIRCRAFT else "navy")
        
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
            province.guest_troops[nation_id] = {"soldiers": 0, "aircraft": 0, "navy": 0}
            
        guest_force = province.guest_troops[nation_id]
        
        if unit_type == UnitType.SOLDIER:
            guest_force["soldiers"] += quantity
        elif unit_type == UnitType.AIRCRAFT:
            guest_force["aircraft"] += quantity
        elif unit_type == UnitType.NAVY:
            guest_force["navy"] += quantity
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
        # Soldiers must move through owned/allied land provinces.
        # We find a permitted path using relationship-aware logic.
        permitted_ids = {
            oid for oid, rel in world.relationship_matrix.get(nation_id, {}).items()
            if rel in [RelationshipState.MUTUAL_DEFENSE, RelationshipState.NON_AGGRESSION]
        }
        
        path = engine.spatial.get_permitted_path(
            from_id, 
            to_id, 
            nation_id, 
            permitted_ids, 
            unit_type="SOLDIER"
        )
        
        if path is None:
            # Check if there was a path at all but it was blocked
            raw_path = engine.spatial.get_shortest_path(from_id, to_id)
            if raw_path:
                 # It exists but isn't permitted. Log why.
                 # Find the first non-permitted province for better logging.
                 for p_id in raw_path[1:-1]:
                     p = world.provinces.get(p_id)
                     if not p: continue
                     if p.owner_id == nation_id or p.owner_id in permitted_ids: continue
                     
                     rel = world.relationship_matrix.get(nation_id, {}).get(p.owner_id, RelationshipState.PEACE)
                     engine.logs.append(f"⛔ [DEFENSE] Cannot move through neutral/hostile {p.owner_id} (Province {p_id}). Relation: {rel}")
                     break
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
    defending_nations = set()
    if victim_id:
        defending_nations.add(victim_id)
    if target_province.guest_troops:
        defending_nations.update(target_province.guest_troops.keys())

    if nation_id in defending_nations:
        defending_nations.remove(nation_id)

    from geomas.schemas.world import WarStats
    aggressor = world.nations[nation_id]

    for def_nation_id in defending_nations:
        rel = world.relationship_matrix.get(nation_id, {}).get(def_nation_id, RelationshipState.PEACE)
        
        # Launching a nuke ALWAYS starts a war with all forces present
        if rel != RelationshipState.WAR:
            world.relationship_matrix.setdefault(nation_id, {})[def_nation_id] = RelationshipState.WAR
            world.relationship_matrix.setdefault(def_nation_id, {})[nation_id] = RelationshipState.WAR
            
            victim = world.nations.get(def_nation_id)
            if victim:
                if def_nation_id not in aggressor.active_wars:
                    aggressor.active_wars[def_nation_id] = WarStats(
                        start_turn=world.turn,
                        initiator_id=nation_id,
                        original_provinces=len(victim.province_ids)
                    )
                if nation_id not in victim.active_wars:
                    victim.active_wars[nation_id] = WarStats(
                        start_turn=world.turn,
                        initiator_id=nation_id,
                        original_provinces=len(victim.province_ids)
                    )

            if rel in (RelationshipState.MUTUAL_DEFENSE, RelationshipState.NON_AGGRESSION):
                engine.logs.append(
                    f"💔 [DIPLOMACY] {nation_id} BROKE ALLIANCE by nuking {def_nation_id}'s troops! Relationship set to WAR."
                )
            else:
                 engine.logs.append(
                    f"⚔️ [DIPLOMACY] {nation_id} started WAR with {def_nation_id} by nuclear aggression."
                )

    # Consume nuke
    nation.nukes -= quantity
    
    # Store pre-strike values for logging
    from geomas.actions.defense.combat import get_total_defenders
    pre_soldiers, pre_aircraft, pre_navy = get_total_defenders(target_province)
    pre_navy = target_province.navy
    pre_pop = target_province.population
    
    # Update victim nation totals
    if victim_id:
        victim_nation = world.nations.get(victim_id)
        if victim_nation:
            victim_nation.total_soldiers -= target_province.soldiers
            victim_nation.total_aircraft -= target_province.aircraft
            victim_nation.total_navy -= target_province.navy
            
    # Clear guest troops
    if target_province.guest_troops:
        for guest_id, force in target_province.guest_troops.items():
            guest_nation = world.nations.get(guest_id)
            if guest_nation:
                guest_nation.total_soldiers -= force.get("soldiers", 0)
                guest_nation.total_aircraft -= force.get("aircraft", 0)
        target_province.guest_troops.clear()
    
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
        
        # NUCLEAR CALL TO ARMS
        _generate_call_to_arms(engine, nation_id, victim_id, attack_type="NUKED")
    
    # ALL other nations: trust -= 80 toward attacker (high penalty)
    for other_nation_id in world.nations:
        if other_nation_id != nation_id and other_nation_id != victim_id:
            engine.adjust_trust(other_nation_id, nation_id, -80)
            engine.logs.append(
                f"💔 [DIPLOMACY] {other_nation_id}'s trust toward {nation_id} decreased by 80"
            )
