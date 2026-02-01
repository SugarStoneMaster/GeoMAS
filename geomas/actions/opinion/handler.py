"""
Opinion Handler.

Applies satisfaction dynamics, triggers, and processes population LLM output.
"""

from typing import TYPE_CHECKING, List
import random
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


def apply_satisfaction_deltas(engine: 'ActionEngine', nation_id: str, rng: random.Random = None) -> float:
    """
    Calculate and apply base satisfaction deltas for a turn.
    
    Strategy:
    1. Calculate all positive deltas, sum them → positive_total
    2. Calculate all negative deltas, sum them → negative_total
    3. Apply multipliers: positive_total * multiplier_increase
    4. Apply multipliers: negative_total * multiplier_decrease
    5. Final delta = positive_multiplied + negative_multiplied
    
    Returns the total final delta.
    """
    world = engine.world
    nation = world.nations.get(nation_id)
    if not nation:
        return 0.0
    
    positive_deltas = 0.0
    negative_deltas = 0.0
    
    # --- WAR/PEACE STATUS ---
    at_war = False
    for other_id in world.nations:
        if other_id != nation_id:
            rel = world.relationship_matrix.get(nation_id, {}).get(other_id, "PEACE")
            if rel == "WAR":
                at_war = True
                negative_deltas += DELTA_WAR_PENALTY  # -3 per war
    
    # Peace bonus only if at peace with everyone
    if not at_war:
        positive_deltas += DELTA_PEACE_BONUS  # +1
    
    # --- RESOURCE CHECK ---
    if nation.total_food < 0 or nation.total_energy < 0 or nation.total_materials < 0:
        negative_deltas += DELTA_RESOURCE_DEFICIT  # -2
    elif nation.total_food > 100 and nation.total_energy > 100:
        positive_deltas += DELTA_RESOURCE_SURPLUS  # +1
    
    # --- APPLY MULTIPLIERS ---
    positive_multiplied = positive_deltas * nation.population_multiplier_increase
    negative_multiplied = negative_deltas * nation.population_multiplier_decrease
    
    final_delta = positive_multiplied + negative_multiplied
    
    # Update satisfaction
    old_sat = nation.public_satisfaction
    nation.public_satisfaction = max(0, min(100, old_sat + final_delta))
    
    engine.logs.append(
        f"[OPINION] {nation_id}: satisfaction {old_sat:.0f} -> {nation.public_satisfaction:.0f} "
        f"(+{positive_deltas:+.1f}*{nation.population_multiplier_increase:.1f} "
        f"{negative_deltas:+.1f}*{nation.population_multiplier_decrease:.1f} = {final_delta:+.1f})"
    )
    
    return final_delta


def check_triggers(engine: 'ActionEngine', nation_id: str, rng: random.Random = None) -> List[OpinionTrigger]:
    """
    Check and apply automatic triggers based on satisfaction levels.
    
    Args:
        rng: Random generator for deterministic province selection
    
    Returns list of triggered events.
    """
    world = engine.world
    nation = world.nations.get(nation_id)
    if not nation:
        return []
    
    if rng is None:
        rng = random.Random()
    
    triggered = []
    sat = nation.public_satisfaction
    
    # --- CIVIL_UNREST (sat < 10) ---
    if sat < THRESHOLD_CIVIL_UNREST and not nation.civil_unrest_active:
        nation.civil_unrest_active = True
        triggered.append(OpinionTrigger.CIVIL_UNREST)
        
        # Select 50% of provinces randomly to revolt
        province_ids = list(nation.province_ids)
        rng.shuffle(province_ids)
        num_revolt = len(province_ids) // 2
        revolting_provinces = province_ids[:max(1, num_revolt)]
        
        for prov_id in revolting_provinces:
            prov = world.provinces.get(prov_id)
            if prov:
                prov.in_revolt = True
                prov.soldiers = 0
                prov.navy = 0
                prov.aircraft = 0
        
        engine.logs.append(
            f"[OPINION] 🔥 CIVIL UNREST in {nation_id}! {len(revolting_provinces)} provinces in revolt."
        )
        world.global_events.append(
            f"[Turn {world.turn}] CIVIL UNREST: {nation_id} - {len(revolting_provinces)} provinces revolt!"
        )
    
    # --- Check unrest recovery (sat > 50) ---
    elif nation.civil_unrest_active and sat >= THRESHOLD_UNREST_RECOVERY:
        nation.civil_unrest_active = False
        
        # Restore all revolting provinces
        for prov_id in nation.province_ids:
            prov = world.provinces.get(prov_id)
            if prov and prov.in_revolt:
                prov.in_revolt = False
        
        engine.logs.append(
            f"[OPINION] ✅ {nation_id} civil unrest ended. Provinces restored."
        )
    
    # --- GENERAL_STRIKE (sat < 20 but >= 10) ---
    if sat < THRESHOLD_GENERAL_STRIKE and sat >= THRESHOLD_CIVIL_UNREST:
        triggered.append(OpinionTrigger.GENERAL_STRIKE)
        engine.logs.append(
            f"[OPINION] ⚠️ GENERAL STRIKE in {nation_id}! Production -50%."
        )
    
    return triggered


def is_nation_on_strike(nation: 'NationState') -> bool:
    """Check if nation is under general strike (for production penalty)."""
    return nation.public_satisfaction < THRESHOLD_GENERAL_STRIKE


def get_production_multiplier(nation: 'NationState') -> float:
    """Get production multiplier considering strikes and unrest."""
    if nation.civil_unrest_active:
        return 0.0  # No production during unrest (handled per-province via in_revolt)
    elif is_nation_on_strike(nation):
        return STRIKE_PRODUCTION_PENALTY  # 50% during strike
    return 1.0


def get_province_production_multiplier(province, nation: 'NationState') -> float:
    """
    Get production multiplier for a specific province.
    
    Returns:
        0.0 if province in revolt
        0.5 if nation on strike
        1.0 otherwise
    """
    if province.in_revolt:
        return 0.0
    if nation and is_nation_on_strike(nation):
        return STRIKE_PRODUCTION_PENALTY
    return 1.0
