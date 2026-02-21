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
    THRESHOLD_PRODUCTION_DECAY_START,
    THRESHOLD_PRODUCTION_DECAY_FLOOR,
    MIN_PRODUCTION_MULTIPLIER,
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
            f"📊 [OPINION] {nation_id} population mood: {payload.reasoning[:100]}..."
        )


def calculate_turn_satisfaction_delta(
    nation: 'NationState',
    world: 'WorldState',
    events: List[str],
    gov_actions: List[str],
    at_war: bool
) -> float:
    """
    Centralized satisfaction delta calculation.
    Combines events, government actions, and state-based deltas.
    Applies nation-specific LLM multipliers for increase/decrease.
    """
    pos_sum = 0.0
    neg_sum = 0.0
    
    # 1. State-based impacts (War & Resources)
    if at_war:
        neg_sum += abs(DELTA_WAR_PENALTY)
    else:
        pos_sum += abs(DELTA_PEACE_BONUS)
        
    if nation.total_food < 50 or nation.total_energy < 50:
        neg_sum += abs(DELTA_RESOURCE_DEFICIT)
    elif nation.total_food > 150 and nation.total_energy > 150:
        pos_sum += abs(DELTA_RESOURCE_SURPLUS)
        
    # 2. Event-based impacts
    for event in events:
        event_upper = event.upper()
        if "ALLIANCE_FORMED" in event_upper:
            pos_sum += 3.0
        if "PEACE_SIGNED" in event_upper:
            pos_sum += 5.0
        if "TRADE_DEAL" in event_upper:
            pos_sum += 2.0
        if "TERRITORY_GAINED" in event_upper:
            pos_sum += 4.0
            
        if "WAR_DECLARED" in event_upper and nation.name in event:
            neg_sum += 5.0
        if "ALLIANCE_BROKEN" in event_upper:
            neg_sum += 3.0
        if "TERRITORY_LOST" in event_upper:
            neg_sum += 6.0
        if "NUCLEAR_STRIKE" in event_upper:
            neg_sum += 10.0

    # 3. Action-based impacts
    for action in gov_actions:
        action_upper = action.upper()
        if "INVEST_WELFARE" in action_upper:
            pos_sum += 3.0
        if "RAISE_WAR_TAX" in action_upper or "WAR_TAX" in action_upper:
            neg_sum += 5.0

    # 4. Apply Multipliers
    final_pos = pos_sum * nation.population_multiplier_increase
    final_neg = neg_sum * nation.population_multiplier_decrease
    
    return final_pos - final_neg


def apply_satisfaction_deltas(engine: 'ActionEngine', nation_id: str, rng: random.Random = None) -> float:
    """
    DEPRECATED: Use calculate_turn_satisfaction_delta from phases.py.
    Left for compatibility with older tests if needed.
    """
    world = engine.world
    nation = world.nations.get(nation_id)
    if not nation:
        return 0.0
    
    # Fallback to simple logic for legacy callers
    at_war = any(
        world.relationship_matrix.get(nation_id, {}).get(nid) == "WAR"
        for nid in world.nations if nid != nation_id
    )
    
    final_delta = calculate_turn_satisfaction_delta(
        nation, world, [], [], at_war
    )
    
    # Update satisfaction
    old_sat = nation.public_satisfaction
    nation.public_satisfaction = max(0, min(100, old_sat + final_delta))
    
    engine.logs.append(
        f"📊 [OPINION] {nation_id}: satisfaction {old_sat:.0f} -> {nation.public_satisfaction:.0f} ({final_delta:+.1f})"
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
            f"🔥 [OPINION] CIVIL UNREST in {nation_id}! {len(revolting_provinces)} provinces in revolt."
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
            f"✅ [OPINION] {nation_id} civil unrest ended. Provinces restored."
        )
    
    # --- GENERAL_STRIKE (sat < 20 but >= 10) ---
    # We keep this as a formal trigger for narrative/logging consistency
    if sat < THRESHOLD_GENERAL_STRIKE and sat >= THRESHOLD_CIVIL_UNREST:
        triggered.append(OpinionTrigger.GENERAL_STRIKE)
        engine.logs.append(
            f"⚠️ [OPINION] GENERAL STRIKE in {nation_id}! Efficiency is low."
        )
        world.global_events.append(
            f"[Turn {world.turn}] GENERAL STRIKE: {nation_id} - Efficiency is critically low!"
        )
    
    # --- PRODUCTION DECAY LOGGING (starts earlier) ---
    if sat < THRESHOLD_PRODUCTION_DECAY_START and sat >= THRESHOLD_GENERAL_STRIKE:
        mult = get_production_multiplier(nation)
        engine.logs.append(
            f"📉 [OPINION] DECAYING PRODUCTIVITY in {nation_id}: {mult*100:.1f}% efficiency."
        )
    
    return triggered


def is_nation_on_strike(nation: 'NationState') -> bool:
    """Check if nation is under general strike (legacy check)."""
    return nation.public_satisfaction < THRESHOLD_PRODUCTION_DECAY_START


def get_production_multiplier(nation: 'NationState') -> float:
    """Get production multiplier considering linear decay and unrest."""
    if nation.civil_unrest_active:
        return 0.0
    
    sat = nation.public_satisfaction
    
    if sat >= THRESHOLD_PRODUCTION_DECAY_START:
        return 1.0
    
    if sat <= THRESHOLD_PRODUCTION_DECAY_FLOOR:
        return MIN_PRODUCTION_MULTIPLIER
    
    # Linear interpolation between DECAY_START (1.0) and DECAY_FLOOR (MIN_MULT)
    # Range: 50 -> 10, Multiplier: 1.0 -> 0.5
    decay_range = THRESHOLD_PRODUCTION_DECAY_START - THRESHOLD_PRODUCTION_DECAY_FLOOR
    mult_range = 1.0 - MIN_PRODUCTION_MULTIPLIER
    
    relative_sat = sat - THRESHOLD_PRODUCTION_DECAY_FLOOR
    decay_ratio = relative_sat / decay_range
    
    return MIN_PRODUCTION_MULTIPLIER + (decay_ratio * mult_range)


def get_province_production_multiplier(province, nation: 'NationState') -> float:
    """
    Get production multiplier for a specific province.
    
    Returns:
        0.0 if province in revolt
        linear decay multiplier if nation has low satisfaction
        1.0 otherwise
    """
    if province.in_revolt:
        return 0.0
    if nation:
        return get_production_multiplier(nation)
    return 1.0
