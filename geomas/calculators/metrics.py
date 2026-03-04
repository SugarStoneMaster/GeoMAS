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
from geomas.analysis.coherence import CoherenceAnalyzer


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
            
    # Overall is the average of active domains
    active_domains = sum([has_defense, has_foreign])
    if active_domains > 0:
        scores["overall"] = (scores["defense"] + scores["foreign"]) / active_domains
        
    return scores


def calculate_coherence_score(envelope: CountryEnvelope) -> float:
    """
    Calculates how coherent the actions are with the stated GlobalStrategy.
    Uses the robust CoherenceAnalyzer to compare Strategy vs Private Intents.
    
    Returns:
        Score from 0.0 to 1.0 (1.0 = perfectly coherent).
    """
    return CoherenceAnalyzer.calculate_score(
        envelope.global_strategy,
        envelope.defense_private_intent,
        envelope.foreign_private_intent
    )


def extract_nation_metrics(world: WorldState, envelope: CountryEnvelope, turn: int) -> Dict[str, Any]:
    """
    Extracts all numerical metrics for a single nation for the Analytics DB.
    """
    nation_id = envelope.sender_id
    nation = world.nations.get(nation_id)
    if not nation or not nation.is_active or not nation.province_ids:
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
        if econ_payload:
            action_type = getattr(econ_payload, 'action_type', None)
            if action_type:
                action_str = action_type.value if hasattr(action_type, 'value') else str(action_type)
                # The Enum is EconomicActionType.TRADE_PROPOSAL
                if action_str == "TRADE_PROPOSAL":
                    amount = getattr(econ_payload, 'give_amount', 0.0)
                    if amount:
                        trade_volume += float(amount)
    
    return {
        "simulation_id": None, # Injected by the DB layer
        "turn": turn,
        "nation_id": nation_id,
        "deception_overall": deception["overall"],
        "deception_defense": deception["defense"],
        "deception_foreign": deception["foreign"],
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


def extract_action_outcomes(
    envelope: CountryEnvelope, turn: int
) -> List[Dict[str, Any]]:
    """
    Extracts per-action engine-level outcomes from a single envelope.

    Iterates every individual action across all three domains and records
    whether the simulation engine accepted or rejected it, along with the
    reason (e.g. "Insufficient budget", "No path found").

    Returns:
        List of dicts ready for MetricsDB.insert_action_outcomes().
    """
    nation_id = envelope.sender_id
    rows: List[Dict[str, Any]] = []

    def _to_str(v) -> str:
        """Convert an enum value or plain string to a plain string."""
        return v.value if hasattr(v, "value") else str(v)

    # --- Defense (waterfall: multiple moves) ---
    if envelope.defense_payload and envelope.defense_payload.moves:
        for move in envelope.defense_payload.moves:
            outcome = getattr(move, "execution_outcome", None)
            status = _to_str(outcome.status) if outcome else "PENDING"
            reason = outcome.reason if outcome else None
            rows.append({
                "turn":        turn,
                "nation_id":   nation_id,
                "domain":      "Defense",
                "action_type": _to_str(move.action_type),
                "status":      status,
                "reason":      reason,
            })

    # --- Economy (single action) ---
    if envelope.economic_payload and envelope.economic_payload.action_type:
        outcome = getattr(envelope.economic_payload, "execution_outcome", None)
        status = _to_str(outcome.status) if outcome else "PENDING"
        reason = outcome.reason if outcome else None
        rows.append({
            "turn":        turn,
            "nation_id":   nation_id,
            "domain":      "Economy",
            "action_type": _to_str(envelope.economic_payload.action_type),
            "status":      status,
            "reason":      reason,
        })

    # --- Foreign (single action; responses are not tracked here as they
    #     are proposal-based and always succeed if the proposal existed) ---
    if envelope.foreign_payload and envelope.foreign_payload.action_type:
        outcome = getattr(envelope.foreign_payload, "execution_outcome", None)
        status = _to_str(outcome.status) if outcome else "PENDING"
        reason = outcome.reason if outcome else None
        rows.append({
            "turn":        turn,
            "nation_id":   nation_id,
            "domain":      "Foreign",
            "action_type": _to_str(envelope.foreign_payload.action_type),
            "status":      status,
            "reason":      reason,
        })

    return rows


def extract_presidential_decisions(
    envelope: CountryEnvelope, turn: int
) -> List[Dict[str, Any]]:
    """
    Extracts the President's APPROVE/VETO decisions from a single envelope.

    One row per domain, capturing:
    - domain: 'Defense', 'Economy', 'Foreign'
    - decision: 'APPROVE' or 'VETO'
    - action_type: the concrete action that the minister proposed
    - reasoning: the president's private reasoning (if available)

    Returns:
        List of dicts ready for MetricsDB.insert_presidential_decisions().
    """
    nation_id = envelope.sender_id
    rows: List[Dict[str, Any]] = []

    def _to_str(v) -> str:
        return v.value if hasattr(v, "value") else str(v) if v is not None else None

    # --- Defense ---
    if envelope.defense_payload:
        # For the defense waterfall the "proposed action" is summarised as a
        # comma-separated list of the action types proposed by the minister.
        def_actions = None
        if envelope.original_defense_proposal:
            proposal_payload = getattr(
                envelope.original_defense_proposal, "payload", None
            )
            if proposal_payload and getattr(proposal_payload, "moves", None):
                def_actions = ",".join(
                    _to_str(m.action_type) for m in proposal_payload.moves
                )

        rows.append({
            "turn":        turn,
            "nation_id":   nation_id,
            "domain":      "Defense",
            "decision":    _to_str(envelope.defense_payload.decision),
            "action_type": def_actions,
            "reasoning":   getattr(envelope, "defense_private_reasoning", None),
        })

    # --- Economy ---
    if envelope.original_economic_proposal:
        eco_payload_prop = getattr(envelope.original_economic_proposal, "payload", None)
        eco_action = _to_str(eco_payload_prop.action_type) if eco_payload_prop else None
        
        # Fallback to final payload if original is missing for some reason
        if not eco_action and envelope.economic_payload:
            eco_action = _to_str(envelope.economic_payload.action_type)
            
        rows.append({
            "turn":        turn,
            "nation_id":   nation_id,
            "domain":      "Economy",
            "decision":    _to_str(envelope.economic_payload.decision) if envelope.economic_payload else "APPROVE",
            "action_type": eco_action,
            "reasoning":   None,  # No private reasoning for economy
        })

    # --- Foreign ---
    if envelope.original_foreign_proposal:
        for_payload_prop = getattr(envelope.original_foreign_proposal, "payload", None)
        for_action = _to_str(for_payload_prop.action_type) if for_payload_prop else None
        
        if not for_action and envelope.foreign_payload:
            for_action = _to_str(envelope.foreign_payload.action_type)
            
        rows.append({
            "turn":        turn,
            "nation_id":   nation_id,
            "domain":      "Foreign",
            "decision":    _to_str(envelope.foreign_payload.decision) if envelope.foreign_payload else "APPROVE",
            "action_type": for_action,
            "reasoning":   getattr(envelope, "foreign_private_reasoning", None),
        })

    return rows

