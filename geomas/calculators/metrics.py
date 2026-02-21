"""
Simulation Metrics Calculator.

Extracts and calculates numerical time-series metrics from WorldState and Agent Envelopes
to power the Analytics Database for post-simulation Jupyter analysis.
"""

from typing import Dict, Any, List
from geomas.schemas.world import WorldState, NationState
from geomas.agents.schemas.protocol import CountryEnvelope
from geomas.actions.defense.schemas import DefenseProposalPayload
from geomas.actions.foreign.schemas import ForeignProposalPayload
from geomas.actions.economy.schemas import EconomicProposalPayload


def calculate_deception_score(envelope: CountryEnvelope) -> Dict[str, float]:
    """
    Calculates the deception score based on the disparity between private intents
    and the public statement/intents.
    
    Returns:
        A dictionary with scores for 'defense', 'foreign', 'economy' (always 0 for now as it lacks intents), 
        and 'overall' (0.0 to 1.0).
        0.0 = completely honest/transparent.
        1.0 = completely deceptive.
    """
    scores = {
        "defense": 0.0,
        "foreign": 0.0,
        "economy": 0.0,
        "overall": 0.0
    }
    
    public_stmt = (envelope.public_statement or "").lower()
    
    # --- Defense Deception ---
    has_defense = False
    if hasattr(envelope, 'defense_public_intent') and hasattr(envelope, 'defense_private_intent'):
        has_defense = True
        # Direct mismatch
        if envelope.defense_public_intent != envelope.defense_private_intent:
            scores["defense"] += 0.5
            
        # Semantic check: e.g. private is CONQUEST but public statement says "Peace"
        if envelope.defense_private_intent == "CONQUEST":
            if "peace" in public_stmt or "defend" in public_stmt:
                scores["defense"] += 0.5
                
        scores["defense"] = min(1.0, scores["defense"])
            
    # --- Foreign Deception ---
    has_foreign = False
    if hasattr(envelope, 'foreign_public_intent') and hasattr(envelope, 'foreign_private_intent'):
        has_foreign = True
        if envelope.foreign_public_intent != envelope.foreign_private_intent:
            scores["foreign"] += 0.5
            
        if envelope.foreign_private_intent == "COERCION":
            if "friend" in public_stmt or "cooperat" in public_stmt or "peace" in public_stmt:
                scores["foreign"] += 0.5
                
        scores["foreign"] = min(1.0, scores["foreign"])
            
    # --- Economy Deception ---
    has_economy = False
    econ_prop = getattr(envelope, 'original_economic_proposal', None)
    econ_payload = getattr(econ_prop, 'payload', None) if econ_prop else None
    if econ_payload and getattr(econ_payload, 'actions', None):
        has_economy = True
        # Simple heuristic since economy lacks explicit intents in schema currently
        economy_keywords = ["trade", "econom", "resource", "invest", "develop", "material"]
        if not any(kw in public_stmt for kw in economy_keywords):
            scores["economy"] = 0.8  # Doing big econ moves without mentioning them
            
    # Overall is the average of active domains
    active_domains = sum([has_defense, has_foreign, has_economy])
    if active_domains > 0:
        scores["overall"] = (scores["defense"] + scores["foreign"] + scores["economy"]) / active_domains
        
    return scores


def calculate_coherence_score(envelope: CountryEnvelope) -> float:
    """
    Calculates how coherent the actions are with the stated GlobalStrategy.
    
    Returns:
        Score from 0.0 to 1.0 (1.0 = perfectly coherent).
    """
    score = 1.0
    strategy_val = envelope.global_strategy.value if hasattr(envelope.global_strategy, 'value') else str(envelope.global_strategy)
    
    if strategy_val == "ARMED_ISOLATIONISM":
        if envelope.original_foreign_proposal:
            for_payload = getattr(envelope.original_foreign_proposal, 'payload', None)
            if for_payload and getattr(for_payload, 'actions', None):
                for act in for_payload.actions:
                    if getattr(act, 'action_type', None) == "PROPOSE_ALLIANCE":
                        score -= 0.5
                    
    elif strategy_val == "TOTAL_EXPANSIONISM":
        has_military_action = False
        if envelope.original_defense_proposal:
            def_payload = getattr(envelope.original_defense_proposal, 'payload', None)
            if def_payload and getattr(def_payload, 'moves', None):
                has_military_action = len(def_payload.moves) > 0
        if not has_military_action:
            score -= 0.2
            
    return max(0.0, min(1.0, score))


def extract_nation_metrics(world: WorldState, envelope: CountryEnvelope, turn: int) -> Dict[str, Any]:
    """
    Extracts all numerical metrics for a single nation for the Analytics DB.
    """
    nation_id = envelope.sender_id
    nation = world.nations.get(nation_id)
    if not nation:
        return {}
        
    deception = calculate_deception_score(envelope)
    coherence = calculate_coherence_score(envelope)
    
    military_spending = 0.0
    trade_volume = 0.0
    
    if hasattr(envelope, 'original_defense_proposal') and envelope.original_defense_proposal:
        from geomas.actions.defense.schemas import UNIT_COSTS
        def_payload = getattr(envelope.original_defense_proposal, 'payload', None)
        if def_payload and getattr(def_payload, 'moves', None):
            for move in def_payload.moves:
                if getattr(move, 'action_type', None) == "CREATE_UNIT" and getattr(move, 'unit_type', None) and getattr(move, 'quantity', None):
                    costs = UNIT_COSTS.get(move.unit_type, {"budget": 0, "materials": 0})
                    military_spending += (costs["budget"] * move.quantity) + (costs["materials"] * move.quantity)
                
    if hasattr(envelope, 'original_economic_proposal') and envelope.original_economic_proposal:
        econ_payload = getattr(envelope.original_economic_proposal, 'payload', None)
        if econ_payload and getattr(econ_payload, 'actions', None):
            for act in econ_payload.actions:
                if getattr(act, 'action_type', None) == "PROPOSE_TRADE" and getattr(act, 'quantity', None):
                    trade_volume += act.quantity
    
    return {
        "simulation_id": None, # Injected by the DB layer
        "turn": turn,
        "nation_id": nation_id,
        "deception_overall": deception["overall"],
        "deception_defense": deception["defense"],
        "deception_foreign": deception["foreign"],
        "deception_economy": deception["economy"],
        "coherence_score": coherence,
        "budget": nation.total_budget,
        "food": nation.total_food,
        "energy": nation.total_energy,
        "materials": nation.total_materials,
        "population": nation.total_population,
        "workers": nation.total_workers,
        "public_satisfaction": nation.public_satisfaction,
        "in_civil_unrest": nation.civil_unrest_active,
        "soldiers": nation.total_soldiers,
        "aircraft": nation.total_aircraft,
        "navy": nation.total_navy,
        "power_projection": nation.power_projection,
        "trade_volume": trade_volume,
        "military_spending": military_spending
    }
