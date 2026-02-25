"""
Combat Resolution Module.

Handles all combat calculations and outcomes for military actions.
"""

from typing import TYPE_CHECKING, Optional, Tuple, List
from dataclasses import dataclass
import random

from geomas.actions.defense.schemas import (
    UnitType,
    UNIT_COSTS,
    TERRAIN_DEFENSE_MULTIPLIER,
    # FIX: Re-export so handler.py's lazy import `from combat import get_terrain_defense_bonus` resolves correctly.
    get_terrain_defense_bonus,
)
from geomas.schemas.world import TerrainType, ProvinceState

if TYPE_CHECKING:
    from geomas.schemas.world import WorldState, NationState


# --- COMBAT STRENGTH (per unit) ---
UNIT_COMBAT_STRENGTH: dict[UnitType, float] = {
    UnitType.SOLDIER: 1.0,    # Individual soldier
    UnitType.NAVY: 10.0,      # Ship with 10 crew
    UnitType.AIRCRAFT: 5.0,   # Aircraft with 5 crew
}


@dataclass
class CombatResult:
    """Result of a combat engagement."""
    attacker_wins: bool
    attacker_losses: int
    defender_losses: int
    province_conquered: bool
    landing_province_id: Optional[int] = None  # For naval landings
    log_message: str = ""


def calculate_force(
    soldiers: int = 0,
    navy: int = 0,
    aircraft: int = 0,
    terrain_modifier: float = 1.0
) -> float:
    """Calculate total combat force for a side."""
    force = (
        soldiers * UNIT_COMBAT_STRENGTH[UnitType.SOLDIER] +
        navy * UNIT_COMBAT_STRENGTH[UnitType.NAVY] +
        aircraft * UNIT_COMBAT_STRENGTH[UnitType.AIRCRAFT]
    )
    return force * terrain_modifier


def get_total_defenders(province: ProvinceState) -> Tuple[int, int, int]:
    """Return total soldiers, aircraft, and navy in a province, including guest troops."""
    soldiers = province.soldiers
    aircraft = province.aircraft
    navy = province.navy
    if province.guest_troops:
        for force in province.guest_troops.values():
            soldiers += force.get("soldiers", 0)
            aircraft += force.get("aircraft", 0)
            navy += force.get("navy", 0)
    return soldiers, aircraft, navy


def resolve_land_combat(
    attacker_soldiers: int,
    defender_province: ProvinceState,
    rng: random.Random
) -> CombatResult:
    """
    Resolve land combat between attacking soldiers and province defenders (including guests).
    
    Binary outcome: attacker wins → conquers, attacker loses → all soldiers lost.
    Undefended provinces are captured automatically without combat roll.
    """
    total_soldiers, total_aircraft, total_navy = get_total_defenders(defender_province)
    
    # Short-circuit: undefended province → automatic capture
    if total_soldiers == 0 and total_aircraft == 0:
        return CombatResult(
            attacker_wins=True,
            attacker_losses=0,
            defender_losses=0,
            province_conquered=True,
            log_message=f"Province undefended! {attacker_soldiers} soldiers capture it without resistance."
        )

    terrain_mod = TERRAIN_DEFENSE_MULTIPLIER.get(defender_province.terrain, 1.0)
    
    attacker_force = calculate_force(soldiers=attacker_soldiers)
    defender_force = calculate_force(
        soldiers=total_soldiers,
        aircraft=total_aircraft,
        terrain_modifier=terrain_mod
    )
    
    # Add small random factor for determinism with same seed
    attacker_roll = attacker_force * (0.9 + rng.random() * 0.2)
    defender_roll = defender_force * (0.9 + rng.random() * 0.2)
    
    attacker_wins = attacker_roll > defender_roll
    
    if attacker_wins:
        return CombatResult(
            attacker_wins=True,
            attacker_losses=0,  # Winner doesn't lose units
            defender_losses=total_soldiers + total_aircraft,
            province_conquered=True,
            log_message=f"Attacker wins! {attacker_soldiers} soldiers conquer province. "
                        f"Defenders lost: {total_soldiers} soldiers, "
                        f"{total_aircraft} aircraft"
        )
    else:
        return CombatResult(
            attacker_wins=False,
            attacker_losses=attacker_soldiers,
            defender_losses=0,
            province_conquered=False,
            log_message=f"Defender wins! {attacker_soldiers} attackers destroyed. "
                        f"Province defended by {defender_force:.0f} force"
        )


def resolve_naval_combat(
    attacker_navy: int,
    defender_navy: int,
    rng: random.Random
) -> CombatResult:
    """
    Resolve naval combat between ships.
    
    Binary outcome: winner destroys all enemy ships.
    """
    attacker_force = calculate_force(navy=attacker_navy)
    defender_force = calculate_force(navy=defender_navy)
    
    attacker_roll = attacker_force * (0.9 + rng.random() * 0.2)
    defender_roll = defender_force * (0.9 + rng.random() * 0.2)
    
    attacker_wins = attacker_roll > defender_roll
    
    if attacker_wins:
        return CombatResult(
            attacker_wins=True,
            attacker_losses=0,
            defender_losses=defender_navy,
            province_conquered=False,  # Naval combat doesn't conquer water
            log_message=f"Naval victory! {attacker_navy} ships destroy {defender_navy} enemy ships"
        )
    else:
        return CombatResult(
            attacker_wins=False,
            attacker_losses=attacker_navy,
            defender_losses=0,
            province_conquered=False,
            log_message=f"Naval defeat! {attacker_navy} ships destroyed by {defender_navy} enemy ships"
        )


def resolve_air_strike(
    attacker_aircraft: int,
    defender_province: ProvinceState,
    rng: random.Random
) -> CombatResult:
    """
    Resolve air strike against province defenders.
    
    Binary outcome:
    - Win: destroy all defenders, aircraft return to base
    - Lose: all aircraft destroyed
    
    Note: Air strikes cannot conquer territory.
    """
    terrain_mod = TERRAIN_DEFENSE_MULTIPLIER.get(defender_province.terrain, 1.0)
    
    total_soldiers, total_aircraft, total_navy = get_total_defenders(defender_province)
    
    attacker_force = calculate_force(aircraft=attacker_aircraft)
    defender_force = calculate_force(
        soldiers=total_soldiers,
        aircraft=total_aircraft,
        terrain_modifier=terrain_mod
    )
    
    attacker_roll = attacker_force * (0.9 + rng.random() * 0.2)
    defender_roll = defender_force * (0.9 + rng.random() * 0.2)
    
    attacker_wins = attacker_roll > defender_roll
    
    total_defenders = total_soldiers + total_aircraft
    
    if attacker_wins:
        return CombatResult(
            attacker_wins=True,
            attacker_losses=0,
            defender_losses=total_defenders,
            province_conquered=False,  # Aircraft cannot hold territory
            log_message=f"Air strike success! {attacker_aircraft} aircraft destroy "
                        f"{total_soldiers} soldiers, {total_aircraft} aircraft"
        )
    else:
        return CombatResult(
            attacker_wins=False,
            attacker_losses=attacker_aircraft,
            defender_losses=0,
            province_conquered=False,
            log_message=f"Air strike repelled! {attacker_aircraft} aircraft shot down by "
                        f"{defender_force:.0f} defense force"
        )


def execute_naval_landing(
    world: 'WorldState',
    attacker_nation_id: str,
    attacker_navy: int,
    target_water_province_id: int,
    rng: random.Random
) -> CombatResult:
    """
    Execute unified naval landing logic.
    
    Flow:
    1. Check for enemy navy in water cell
    2. If navy → naval combat
    3. Find adjacent coastal province
    4. If defenders → land combat
    5. Otherwise → auto-land
    6. Always: navy destroyed, soldiers = population (10 per ship)
    """
    water_province = world.provinces.get(target_water_province_id)
    if not water_province:
        return CombatResult(
            attacker_wins=False,
            attacker_losses=attacker_navy,
            defender_losses=0,
            province_conquered=False,
            log_message="Invalid water province"
        )
    
    # Find the defender nation (owner of territorial waters)
    defender_nation_id = None
    for nation_id, nation in world.nations.items():
        if target_water_province_id in nation.territorial_water_ids:
            defender_nation_id = nation_id
            break
    
    if not defender_nation_id:
        return CombatResult(
            attacker_wins=False,
            attacker_losses=attacker_navy,
            defender_losses=0,
            province_conquered=False,
            log_message="Water province has no owner"
        )
    
    # Step 1: Check for enemy navy in the water cell (including guests)
    _, _, total_defender_navy = get_total_defenders(water_province)
    
    if total_defender_navy > 0:
        # Naval combat
        naval_result = resolve_naval_combat(attacker_navy, total_defender_navy, rng)
        
        if not naval_result.attacker_wins:
            # Attacker loses, no landing
            return CombatResult(
                attacker_wins=False,
                attacker_losses=attacker_navy,
                defender_losses=0,
                province_conquered=False,
                log_message=f"Naval landing failed! {attacker_navy} ships sunk by {total_defender_navy} defenders"
            )
        
        # Attacker won naval combat, destroy ALL defender navies in cell
        if defender_nation_id:
             world.nations[defender_nation_id].total_navy -= water_province.navy  # Primary owner
        water_province.navy = 0

        if water_province.guest_troops:
            to_remove = []
            for guest_id, guest_force in water_province.guest_troops.items():
                g_nav = guest_force.get("navy", 0)
                if g_nav > 0:
                    g_nation = world.nations.get(guest_id)
                    if g_nation:
                        g_nation.total_navy -= g_nav
                    guest_force["navy"] = 0
                # Clean up the entry if all unit types are now at zero
                if all(v == 0 for v in guest_force.values()):
                    to_remove.append(guest_id)
            for guest_id in to_remove:
                del water_province.guest_troops[guest_id]
    
    # Step 2: Find adjacent coastal provinces (enemy land)
    adjacent_coasts = []
    for neighbor_id in water_province.neighbors:
        neighbor = world.provinces.get(neighbor_id)
        if neighbor and neighbor.owner_id == defender_nation_id:
            if neighbor.terrain in (TerrainType.COASTAL, TerrainType.LAND, TerrainType.MOUNTAIN):
                adjacent_coasts.append(neighbor_id)
    
    if not adjacent_coasts:
        return CombatResult(
            attacker_wins=False,
            attacker_losses=attacker_navy,
            defender_losses=total_defender_navy,
            province_conquered=False,
            log_message="No adjacent coastal province to land on"
        )
    
    # Step 3: Pick landing target
    landing_province_id = rng.choice(adjacent_coasts)
    landing_province = world.provinces[landing_province_id]
    
    # Calculate landing soldiers (population of navy = crew)
    landing_soldiers = attacker_navy * int(UNIT_COSTS[UnitType.NAVY]["population"])
    
    # Step 4: Check for defenders on coast
    total_soldiers, total_aircraft, _ = get_total_defenders(landing_province)
    total_defenders = total_soldiers + total_aircraft
    
    if total_defenders > 0:
        # Land combat
        land_result = resolve_land_combat(landing_soldiers, landing_province, rng)
        
        if not land_result.attacker_wins:
            return CombatResult(
                attacker_wins=False,
                attacker_losses=attacker_navy,
                defender_losses=total_defender_navy,
                province_conquered=False,
                log_message=f"Landing repelled! {landing_soldiers} soldiers defeated by coastal defenders"
            )
        
        # Successful landing with combat
        _conquer_province(world, attacker_nation_id, landing_province)
        landing_province.soldiers = landing_soldiers
        world.nations[attacker_nation_id].total_soldiers += landing_soldiers
        
        return CombatResult(
            attacker_wins=True,
            attacker_losses=attacker_navy,  # Navy is always destroyed
            defender_losses=total_defender_navy + total_defenders,
            province_conquered=True,
            landing_province_id=landing_province_id,
            log_message=f"Amphibious assault successful! {landing_soldiers} soldiers landed and "
                        f"conquered province {landing_province_id} from {defender_nation_id}"
        )
    
    # Step 5: No defenders - automatic landing
    _conquer_province(world, attacker_nation_id, landing_province)
    landing_province.soldiers = landing_soldiers
    world.nations[attacker_nation_id].total_soldiers += landing_soldiers

    return CombatResult(
        attacker_wins=True,
        attacker_losses=attacker_navy,  # Navy destroyed
        defender_losses=total_defender_navy,
        province_conquered=True,
        landing_province_id=landing_province_id,
        log_message=f"Unopposed landing! {landing_soldiers} soldiers occupy province {landing_province_id} (from {defender_nation_id})"
    )


def _conquer_province(
    world: 'WorldState',
    new_owner_id: str,
    province: 'ProvinceState',
    engine: Optional['ActionEngine'] = None
) -> None:
    """Transfer province ownership from defender to attacker."""
    old_owner_id = province.owner_id
    
    if old_owner_id:
        old_nation = world.nations.get(old_owner_id)
        if old_nation and province.id in old_nation.province_ids:
            old_nation.province_ids.remove(province.id)
            # Clear defender units
            old_nation.total_soldiers -= province.soldiers
            old_nation.total_aircraft -= province.aircraft

    # Clear guest troops if present
    if province.guest_troops:
        for guest_id, force in province.guest_troops.items():
            guest_nation = world.nations.get(guest_id)
            if guest_nation:
                guest_nation.total_soldiers -= force.get("soldiers", 0)
                guest_nation.total_aircraft -= force.get("aircraft", 0)
        province.guest_troops.clear()

    if old_owner_id and old_nation:
        # --- WAR STATS TRACKING ---
        from geomas.schemas.world import RelationshipState, WarStats
        
        # Check if at WAR
        rel = world.relationship_matrix.get(old_owner_id, {}).get(new_owner_id, RelationshipState.PEACE)
        if rel == RelationshipState.WAR:
            # Update Loser
            if new_owner_id not in old_nation.active_wars:
                # Lazy init (should have been done at declaration, but for safety)
                old_nation.active_wars[new_owner_id] = WarStats(
                    start_turn=world.turn,
                    initiator_id=new_owner_id,
                    original_provinces=len(old_nation.province_ids) + 1 # +1 because we just removed one
                )
            old_nation.active_wars[new_owner_id].lost_provinces += 1
            
            # Update Winner
            new_nation_ref = world.nations.get(new_owner_id)
            if new_nation_ref:
                if old_owner_id not in new_nation_ref.active_wars:
                     new_nation_ref.active_wars[old_owner_id] = WarStats(
                        start_turn=world.turn,
                        initiator_id=new_owner_id,
                        original_provinces=len(old_nation.province_ids) + 1 # Use victim's size
                    )
                new_nation_ref.active_wars[old_owner_id].conquered_provinces += 1
    
    # Transfer to new owner
    province.owner_id = new_owner_id
    province.soldiers = 0
    province.aircraft = 0
    
    new_nation = world.nations.get(new_owner_id)
    if new_nation:
        new_nation.province_ids.append(province.id)
        
    # --- CHECK FOR NATION ELIMINATION ---
    if old_owner_id and old_nation:
        if not old_nation.province_ids:
            old_nation.is_active = False
            victim_name = getattr(old_nation, 'name', old_owner_id)
            conqueror_name = getattr(new_nation, 'name', new_owner_id) if new_nation else new_owner_id
            
            fall_msg = f"🚩 [NATION FALLEN] {victim_name} ({old_owner_id}) has been fully annexed by {conqueror_name} ({new_owner_id})!"
            
            # 1. Structural Logging (Memory for Agents)
            # Use getattr for robustness against mocks or incomplete ActionEngine objects
            cm = getattr(engine, 'context_manager', None)
            if cm:
                cm.log_nation_fallen(
                    turn=world.turn,
                    victim_id=old_owner_id,
                    victim_name=victim_name,
                    conqueror_id=new_owner_id,
                    conqueror_name=conqueror_name
                )
            
            # 2. Global Event Logging (News feed)
            events = getattr(world, 'global_events', None)
            if events is not None:
                # Deduplicate: CM already adds to global_events
                already_logged = any(
                    (hasattr(e, 'event_type') and getattr(e, 'event_type') == 'NATION_FALLEN' and old_owner_id in getattr(e, 'actors', []))
                    or fall_msg in str(e)
                    for e in events
                )
                if not already_logged:
                    events.append(f"T{world.turn}: {fall_msg}")
            
            # 3. Cleanup simulation artifacts for the fallen nation
            # A. Clean up guest troops nationwide
            provinces_dict = getattr(world, 'provinces', None)
            if provinces_dict and isinstance(provinces_dict, dict):
                for p in provinces_dict.values():
                    gt = getattr(p, 'guest_troops', None)
                    if gt and isinstance(gt, dict) and old_owner_id in gt:
                        del gt[old_owner_id]
            
            # B. Zero out resources and military to prevent "ghost" power in stats
            old_nation.total_soldiers = 0
            old_nation.total_navy = 0
            old_nation.total_aircraft = 0
            old_nation.total_budget = 0
            old_nation.total_food = 0
            old_nation.total_energy = 0
            old_nation.total_materials = 0
            if hasattr(old_nation, 'active_wars') and isinstance(old_nation.active_wars, dict):
                old_nation.active_wars.clear()
            
            # Remove this war from the conqueror's active list
            if new_nation and hasattr(new_nation, 'active_wars') and isinstance(new_nation.active_wars, dict):
                new_nation.active_wars.pop(old_owner_id, None)
            
            # C. Clean up pending/sent proposals across the world involving this nation
            if hasattr(old_nation, 'pending_proposals') and isinstance(old_nation.pending_proposals, list):
                old_nation.pending_proposals.clear()
            if hasattr(old_nation, 'sent_proposals') and isinstance(old_nation.sent_proposals, list):
                old_nation.sent_proposals.clear()
            
            # Wipe proposals involving victim from other nations' inboxes
            for other_n in world.nations.values():
                pp = getattr(other_n, 'pending_proposals', None)
                if pp and isinstance(pp, list):
                    other_n.pending_proposals = [p for p in pp if p.get("from") != old_owner_id]
                sp = getattr(other_n, 'sent_proposals', None)
                if sp and isinstance(sp, list):
                    other_n.sent_proposals = [p for p in sp if p.get("to") != old_owner_id]
            
            # D. Message cooldowns
            if hasattr(old_nation, 'message_cooldown') and isinstance(old_nation.message_cooldown, dict):
                old_nation.message_cooldown.clear()
            if hasattr(old_nation, 'betrayal_tracker') and isinstance(old_nation.betrayal_tracker, dict):
                old_nation.betrayal_tracker.clear()
            
    # --- UPDATE TERRITORIAL WATERS ---
    if province.terrain == TerrainType.COASTAL:
        from geomas.world.territory import update_territorial_waters
        # Check adjacent OCEAN cells and update their ownership
        for neighbor_id in province.neighbors:
            neighbor = world.provinces.get(neighbor_id)
            if neighbor and neighbor.terrain == TerrainType.OCEAN:
                update_territorial_waters(world, province.id)
