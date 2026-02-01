"""
Opinion Handler.

Applies satisfaction dynamics, triggers, and processes population LLM output.
"""

from typing import TYPE_CHECKING, List, Tuple
from geomas.actions.opinion.schemas import (
    OpinionPayload,
    OpinionTrigger,
    DELTA_WAR_PENALTY,
    DELTA_PEACE_BONUS,
    DELTA_RESOURCE_DEFICIT,
    DELTA_RESOURCE_SURPLUS,
    THRESHOLD_GENERAL_STRIKE,
    THRESHOLD_CIVIL_UNREST,
    THRESHOLD_UNREST_RECOVERY,
    STRIKE_PRODUCTION_PENALTY,
)

if TYPE_CHECKING:
    from geomas.actions.engine import ActionEngine
    from geomas.schemas.world import WorldState, NationState


def execute_opinion(
    engine: 'ActionEngine',
    nation_id: str,
    payload: OpinionPayload
) -> None:
    """
    Process population LLM response and update multipliers.
    Called after LLM agent provides opinion multipliers.
    """
    nation = engine.world.nations.get(nation_id)
    if not nation:
        return
    
    # Update multipliers from LLM agent (clamped 0.1-2.0)
    nation.population_multiplier_increase = max(0.1, min(2.0, payload.multiplier_increase))
    nation.population_multiplier_decrease = max(0.1, min(2.0, payload.multiplier_decrease))
    
    if payload.reasoning:
        engine.logs.append(
            f"[OPINION] {nation_id} population mood: {payload.reasoning[:100]}..."
        )


def apply_satisfaction_deltas(engine: 'ActionEngine', nation_id: str) -> float:
    """
    Calculate and apply base satisfaction deltas for a turn.
    Returns the total delta before multiplier application.
    
    Called at the start of each turn.
    """
    world = engine.world
    nation = world.nations.get(nation_id)
    if not nation:
        return 0.0
    
    total_delta = 0.0
    
    # Check war status
    at_war = False
    for other_id in world.nations:
        if other_id != nation_id:
            rel = world.relationship_matrix.get(nation_id, {}).get(other_id, "PEACE")
            if rel == "WAR":
                at_war = True
                total_delta += DELTA_WAR_PENALTY
    
    # Peace bonus only if at peace with everyone
    if not at_war:
        total_delta += DELTA_PEACE_BONUS
    
    # Resource check (simplified: negative if any deficit)
    if nation.total_food < 0 or nation.total_energy < 0 or nation.total_materials < 0:
        total_delta += DELTA_RESOURCE_DEFICIT
    elif nation.total_food > 100 and nation.total_energy > 100:
        total_delta += DELTA_RESOURCE_SURPLUS
    
    # Apply multiplier based on direction
    if total_delta > 0:
        multiplied_delta = total_delta * nation.population_multiplier_increase
    else:
        multiplied_delta = total_delta * nation.population_multiplier_decrease
    
    # Update satisfaction
    old_sat = nation.public_satisfaction
    nation.public_satisfaction = max(0, min(100, old_sat + multiplied_delta))
    
    engine.logs.append(
        f"[OPINION] {nation_id}: satisfaction {old_sat:.0f} -> {nation.public_satisfaction:.0f} "
        f"(base: {total_delta:+.1f}, mult: {multiplied_delta:+.1f})"
    )
    
    return multiplied_delta


def check_triggers(engine: 'ActionEngine', nation_id: str) -> List[OpinionTrigger]:
    """
    Check and apply automatic triggers based on satisfaction levels.
    Returns list of triggered events.
    """
    world = engine.world
    nation = world.nations.get(nation_id)
    if not nation:
        return []
    
    triggered = []
    sat = nation.public_satisfaction
    
    # --- CIVIL_UNREST ---
    if sat < THRESHOLD_CIVIL_UNREST and not nation.civil_unrest_active:
        nation.civil_unrest_active = True
        triggered.append(OpinionTrigger.CIVIL_UNREST)
        
        # Apply civil unrest: all provinces lose output
        for prov_id in nation.province_ids:
            prov = world.provinces.get(prov_id)
            if prov:
                prov.soldiers = 0
                prov.navy = 0
                prov.aircraft = 0
                # Mark province output as suspended (production handled elsewhere)
        
        engine.logs.append(
            f"[OPINION] 🔥 CIVIL UNREST in {nation_id}! Provinces lose military output."
        )
        world.global_events.append(
            f"[Turn {world.turn}] CIVIL UNREST: {nation_id} population revolts!"
        )
    
    # Check unrest recovery
    elif nation.civil_unrest_active and sat >= THRESHOLD_UNREST_RECOVERY:
        nation.civil_unrest_active = False
        engine.logs.append(
            f"[OPINION] {nation_id} civil unrest has ended (satisfaction > {THRESHOLD_UNREST_RECOVERY})."
        )
    
    # --- GENERAL_STRIKE ---
    if sat < THRESHOLD_GENERAL_STRIKE and sat >= THRESHOLD_CIVIL_UNREST:
        triggered.append(OpinionTrigger.GENERAL_STRIKE)
        engine.logs.append(
            f"[OPINION] ⚠️ GENERAL STRIKE in {nation_id}! Production -50%."
        )
        # Production penalty applied in resource calculation phase
    
    return triggered


def is_nation_on_strike(nation: 'NationState') -> bool:
    """Check if nation is under general strike (for production penalty)."""
    return nation.public_satisfaction < THRESHOLD_GENERAL_STRIKE


def get_production_multiplier(nation: 'NationState') -> float:
    """Get production multiplier considering strikes and unrest."""
    if nation.civil_unrest_active:
        return 0.0  # No production during unrest
    elif is_nation_on_strike(nation):
        return STRIKE_PRODUCTION_PENALTY  # 50% during strike
    return 1.0
