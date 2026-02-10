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


def resolve_land_combat(
    attacker_soldiers: int,
    defender_province: ProvinceState,
    rng: random.Random
) -> CombatResult:
    """
    Resolve land combat between attacking soldiers and province defenders.
    
    Binary outcome: attacker wins → conquers, attacker loses → all soldiers lost.
    Undefended provinces are captured automatically without combat roll.
    """
    # Short-circuit: undefended province → automatic capture
    if defender_province.soldiers == 0 and defender_province.aircraft == 0:
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
        soldiers=defender_province.soldiers,
        aircraft=defender_province.aircraft,
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
            defender_losses=defender_province.soldiers + defender_province.aircraft,
            province_conquered=True,
            log_message=f"Attacker wins! {attacker_soldiers} soldiers conquer province. "
                        f"Defenders lost: {defender_province.soldiers} soldiers, "
                        f"{defender_province.aircraft} aircraft"
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
    
    attacker_force = calculate_force(aircraft=attacker_aircraft)
    defender_force = calculate_force(
        soldiers=defender_province.soldiers,
        aircraft=defender_province.aircraft,
        terrain_modifier=terrain_mod
    )
    
    attacker_roll = attacker_force * (0.9 + rng.random() * 0.2)
    defender_roll = defender_force * (0.9 + rng.random() * 0.2)
    
    attacker_wins = attacker_roll > defender_roll
    
    total_defenders = defender_province.soldiers + defender_province.aircraft
    
    if attacker_wins:
        return CombatResult(
            attacker_wins=True,
            attacker_losses=0,
            defender_losses=total_defenders,
            province_conquered=False,  # Aircraft cannot hold territory
            log_message=f"Air strike success! {attacker_aircraft} aircraft destroy "
                        f"{defender_province.soldiers} soldiers, {defender_province.aircraft} aircraft"
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
    
    # Step 1: Check for enemy navy in the water cell
    defender_navy = water_province.navy
    
    if defender_navy > 0:
        # Naval combat first
        naval_result = resolve_naval_combat(attacker_navy, defender_navy, rng)
        
        if not naval_result.attacker_wins:
            # Attacker loses, no landing
            return CombatResult(
                attacker_wins=False,
                attacker_losses=attacker_navy,
                defender_losses=0,
                province_conquered=False,
                log_message=f"Naval landing failed! {attacker_navy} ships sunk by {defender_navy} defenders"
            )
        
        # Attacker won naval combat, destroy defender navy
        water_province.navy = 0
        world.nations[defender_nation_id].total_navy -= defender_navy
    
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
            defender_losses=defender_navy if defender_navy > 0 else 0,
            province_conquered=False,
            log_message="No adjacent coastal province to land on"
        )
    
    # Step 3: Pick landing target
    landing_province_id = rng.choice(adjacent_coasts)
    landing_province = world.provinces[landing_province_id]
    
    # Calculate landing soldiers (population of navy = crew)
    landing_soldiers = attacker_navy * int(UNIT_COSTS[UnitType.NAVY]["population"])
    
    # Step 4: Check for defenders on coast
    total_defenders = landing_province.soldiers + landing_province.aircraft
    
    if total_defenders > 0:
        # Land combat
        land_result = resolve_land_combat(landing_soldiers, landing_province, rng)
        
        if not land_result.attacker_wins:
            return CombatResult(
                attacker_wins=False,
                attacker_losses=attacker_navy,
                defender_losses=defender_navy if defender_navy > 0 else 0,
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
            defender_losses=defender_navy + total_defenders,
            province_conquered=True,
            landing_province_id=landing_province_id,
            log_message=f"Amphibious assault successful! {landing_soldiers} soldiers landed and "
                        f"conquered province {landing_province_id}"
        )
    
    # Step 5: No defenders - automatic landing
    _conquer_province(world, attacker_nation_id, landing_province)
    landing_province.soldiers = landing_soldiers
    world.nations[attacker_nation_id].total_soldiers += landing_soldiers
    
    return CombatResult(
        attacker_wins=True,
        attacker_losses=attacker_navy,  # Navy destroyed
        defender_losses=defender_navy if defender_navy > 0 else 0,
        province_conquered=True,
        landing_province_id=landing_province_id,
        log_message=f"Unopposed landing! {landing_soldiers} soldiers occupy province {landing_province_id}"
    )


def _conquer_province(
    world: 'WorldState',
    new_owner_id: str,
    province: ProvinceState
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
    
    # Transfer to new owner
    province.owner_id = new_owner_id
    province.soldiers = 0
    province.aircraft = 0
    
    new_nation = world.nations.get(new_owner_id)
    if new_nation:
        new_nation.province_ids.append(province.id)
