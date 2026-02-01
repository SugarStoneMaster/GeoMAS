"""
Foreign Affairs Action Handler.

Executes diplomatic actions (one action per turn).
"""

from typing import TYPE_CHECKING
from geomas.actions.foreign.schemas import (
    ForeignActionType,
    ForeignPayload,
    DiplomaticMessageType,
    MESSAGE_TRUST_IMPACT,
)
from geomas.schemas.world import RelationshipState

if TYPE_CHECKING:
    from geomas.actions.engine import ActionEngine


def execute_foreign(
    engine: 'ActionEngine',
    nation_id: str, 
    payload: ForeignPayload
) -> None:
    """
    Execute a foreign affairs action.
    
    Note: Only ONE foreign action per turn (not waterfall).
    """
    if not payload.action_type:
        return
    
    if not payload.target_nation_id:
        engine.logs.append(f"[FOREIGN] No target nation specified")
        return
    
    target_id = payload.target_nation_id
    world = engine.world
    
    # Validate target exists
    if target_id not in world.nations:
        engine.logs.append(f"[FOREIGN] Target nation {target_id} not found")
        return
    
    # Dispatch to appropriate handler
    if payload.action_type == ForeignActionType.SEND_DIPLOMATIC_MESSAGE:
        _execute_send_message(engine, nation_id, target_id, payload.parameters)
    
    elif payload.action_type == ForeignActionType.FORMAL_DECLARATION_OF_WAR:
        _execute_declare_war(engine, nation_id, target_id)
    
    elif payload.action_type == ForeignActionType.BREAK_TREATY:
        _execute_break_treaty(engine, nation_id, target_id)
    
    elif payload.action_type == ForeignActionType.REQUEST_PEACE:
        _execute_request_peace(engine, nation_id, target_id)
    
    elif payload.action_type == ForeignActionType.PROPOSE_ALLIANCE:
        _execute_propose_alliance(engine, nation_id, target_id)


def _execute_send_message(
    engine: 'ActionEngine',
    sender_id: str,
    target_id: str,
    parameters: dict
) -> None:
    """Send a diplomatic message with trust impact."""
    msg_type_str = parameters.get("message_type", "PRAISE")
    
    try:
        msg_type = DiplomaticMessageType(msg_type_str)
    except ValueError:
        engine.logs.append(f"[FOREIGN] Invalid message type: {msg_type_str}")
        return
    
    trust_delta = MESSAGE_TRUST_IMPACT[msg_type]
    
    # Apply trust change (bidirectional for PRAISE, unidirectional for negative)
    engine.adjust_trust(sender_id, target_id, trust_delta)
    if msg_type == DiplomaticMessageType.PRAISE:
        engine.adjust_trust(target_id, sender_id, trust_delta)
    
    engine.logs.append(
        f"[FOREIGN] {sender_id} sends {msg_type.value} to {target_id}. Trust impact: {trust_delta:+.1f}"
    )


def _execute_declare_war(
    engine: 'ActionEngine',
    aggressor_id: str,
    target_id: str
) -> None:
    """Formally declare war on target nation."""
    world = engine.world
    
    current_rel = world.relationship_matrix.get(aggressor_id, {}).get(target_id, "PEACE")
    
    if current_rel == "WAR":
        engine.logs.append(f"[FOREIGN] {aggressor_id} already at war with {target_id}")
        return
    
    # Set relationship to WAR (both directions)
    world.relationship_matrix.setdefault(aggressor_id, {})[target_id] = "WAR"
    world.relationship_matrix.setdefault(target_id, {})[aggressor_id] = "WAR"
    
    # Trust → 0 between the two
    world.trust_matrix.setdefault(aggressor_id, {})[target_id] = 0.0
    world.trust_matrix.setdefault(target_id, {})[aggressor_id] = 0.0
    
    engine.logs.append(
        f"[FOREIGN] ⚔️ {aggressor_id} DECLARES WAR on {target_id}!"
    )
    
    # Global notification
    engine.world.global_events.append(
        f"[Turn {world.turn}] WAR DECLARED: {aggressor_id} vs {target_id}"
    )


def _execute_break_treaty(
    engine: 'ActionEngine',
    breaker_id: str,
    target_id: str
) -> None:
    """Break alliance treaty with target nation."""
    world = engine.world
    
    current_rel = world.relationship_matrix.get(breaker_id, {}).get(target_id, "PEACE")
    
    if current_rel != "ALLIANCE":
        engine.logs.append(f"[FOREIGN] No alliance exists with {target_id} to break")
        return
    
    # Set relationship back to PEACE
    world.relationship_matrix[breaker_id][target_id] = "PEACE"
    world.relationship_matrix[target_id][breaker_id] = "PEACE"
    
    # Trust penalty for the one who breaks (-0.5)
    engine.adjust_trust(target_id, breaker_id, -0.5)
    
    engine.logs.append(
        f"[FOREIGN] 💔 {breaker_id} BREAKS alliance with {target_id}. Trust penalty applied."
    )


def _execute_request_peace(
    engine: 'ActionEngine',
    requester_id: str,
    target_id: str
) -> None:
    """
    Request peace with a nation at war.
    
    Note: For now, this is auto-accepted. 
    In a full implementation, this would be a pending proposal.
    """
    world = engine.world
    
    current_rel = world.relationship_matrix.get(requester_id, {}).get(target_id, "PEACE")
    
    if current_rel != "WAR":
        engine.logs.append(f"[FOREIGN] Not at war with {target_id}, no peace needed")
        return
    
    # Auto-accept peace for now (simplified)
    world.relationship_matrix[requester_id][target_id] = "PEACE"
    world.relationship_matrix[target_id][requester_id] = "PEACE"
    
    engine.logs.append(
        f"[FOREIGN] 🕊️ Peace treaty signed between {requester_id} and {target_id}"
    )


def _execute_propose_alliance(
    engine: 'ActionEngine',
    proposer_id: str,
    target_id: str
) -> None:
    """
    Propose alliance with target nation.
    
    Requires minimum trust > 0.6.
    Note: For now, auto-accepted if trust is high enough.
    """
    world = engine.world
    
    current_rel = world.relationship_matrix.get(proposer_id, {}).get(target_id, "PEACE")
    
    if current_rel == "ALLIANCE":
        engine.logs.append(f"[FOREIGN] Already allied with {target_id}")
        return
    
    if current_rel == "WAR":
        engine.logs.append(f"[FOREIGN] Cannot propose alliance while at war with {target_id}")
        return
    
    # Check trust threshold
    trust = world.trust_matrix.get(proposer_id, {}).get(target_id, 0.5)
    if trust < 0.6:
        engine.logs.append(
            f"[FOREIGN] Alliance rejected: trust with {target_id} too low ({trust:.2f} < 0.6)"
        )
        return
    
    # Auto-accept (simplified)
    world.relationship_matrix[proposer_id][target_id] = "ALLIANCE"
    world.relationship_matrix[target_id][proposer_id] = "ALLIANCE"
    
    # Trust boost from alliance
    engine.adjust_trust(proposer_id, target_id, 0.1)
    engine.adjust_trust(target_id, proposer_id, 0.1)
    
    engine.logs.append(
        f"[FOREIGN] 🤝 ALLIANCE formed between {proposer_id} and {target_id}!"
    )
