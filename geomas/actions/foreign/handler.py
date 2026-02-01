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


# Anti-spam: minimum turns between messages to same nation
MESSAGE_COOLDOWN_TURNS = 5


def execute_foreign(
    engine: 'ActionEngine',
    nation_id: str, 
    payload: ForeignPayload
) -> None:
    """
    Execute a foreign affairs action.
    
    Note: Only ONE foreign action per turn.
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
    
    elif payload.action_type == ForeignActionType.ACCEPT_PROPOSAL:
        proposal_type = payload.parameters.get("proposal_type", "ALLIANCE")
        respond_to_proposal(engine, nation_id, target_id, proposal_type, accept=True)
    
    elif payload.action_type == ForeignActionType.REJECT_PROPOSAL:
        proposal_type = payload.parameters.get("proposal_type", "ALLIANCE")
        respond_to_proposal(engine, nation_id, target_id, proposal_type, accept=False)


def _execute_send_message(
    engine: 'ActionEngine',
    sender_id: str,
    target_id: str,
    parameters: dict
) -> None:
    """Send a diplomatic message with trust impact (with cooldown)."""
    world = engine.world
    sender = world.nations[sender_id]
    current_turn = world.turn
    
    # Check cooldown
    last_msg_turn = sender.message_cooldown.get(target_id, -999)
    if current_turn - last_msg_turn < MESSAGE_COOLDOWN_TURNS:
        turns_left = MESSAGE_COOLDOWN_TURNS - (current_turn - last_msg_turn)
        engine.logs.append(
            f"[FOREIGN] Cannot message {target_id}: cooldown active ({turns_left} turns left)"
        )
        return
    
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
    
    # Set cooldown
    sender.message_cooldown[target_id] = current_turn
    
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
    world.trust_matrix.setdefault(aggressor_id, {})[target_id] = 0
    world.trust_matrix.setdefault(target_id, {})[aggressor_id] = 0
    
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
    
    # Trust penalty for the one who breaks (-50 on 0-100 scale)
    engine.adjust_trust(target_id, breaker_id, -50)
    
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
    Creates a pending proposal that target must accept/reject next turn.
    """
    world = engine.world
    
    current_rel = world.relationship_matrix.get(requester_id, {}).get(target_id, "PEACE")
    
    if current_rel != "WAR":
        engine.logs.append(f"[FOREIGN] Not at war with {target_id}, no peace needed")
        return
    
    # Add pending proposal to target nation
    target_nation = world.nations[target_id]
    target_nation.pending_proposals.append({
        "type": "PEACE",
        "from": requester_id,
        "turn": world.turn
    })
    
    engine.logs.append(
        f"[FOREIGN] 🕊️ {requester_id} requests peace with {target_id}. Awaiting response."
    )


def _execute_propose_alliance(
    engine: 'ActionEngine',
    proposer_id: str,
    target_id: str
) -> None:
    """
    Propose alliance with target nation.
    Requires minimum trust > 0.6.
    Creates a pending proposal that target must accept/reject next turn.
    """
    world = engine.world
    
    current_rel = world.relationship_matrix.get(proposer_id, {}).get(target_id, "PEACE")
    
    if current_rel == "ALLIANCE":
        engine.logs.append(f"[FOREIGN] Already allied with {target_id}")
        return
    
    if current_rel == "WAR":
        engine.logs.append(f"[FOREIGN] Cannot propose alliance while at war with {target_id}")
        return
    
    # Check trust threshold (60 on 0-100 scale)
    trust = world.trust_matrix.get(proposer_id, {}).get(target_id, 50)
    if trust < 60:
        engine.logs.append(
            f"[FOREIGN] Alliance proposal rejected: trust too low ({trust:.0f} < 60)"
        )
        return
    
    # Add pending proposal to target nation
    target_nation = world.nations[target_id]
    target_nation.pending_proposals.append({
        "type": "ALLIANCE",
        "from": proposer_id,
        "turn": world.turn
    })
    
    engine.logs.append(
        f"[FOREIGN] 🤝 {proposer_id} proposes alliance to {target_id}. Awaiting response."
    )


# --- RESPONSE ACTIONS ---

def respond_to_proposal(
    engine: 'ActionEngine',
    nation_id: str,
    proposer_id: str,
    proposal_type: str,
    accept: bool
) -> None:
    """
    Respond to a pending proposal (ACCEPT or REJECT).
    Called when processing ACCEPT_PROPOSAL or REJECT_PROPOSAL actions.
    """
    world = engine.world
    nation = world.nations[nation_id]
    
    # Find and remove the proposal
    proposal_found = None
    for i, prop in enumerate(nation.pending_proposals):
        if prop["from"] == proposer_id and prop["type"] == proposal_type:
            proposal_found = nation.pending_proposals.pop(i)
            break
    
    if not proposal_found:
        engine.logs.append(
            f"[FOREIGN] No pending {proposal_type} proposal from {proposer_id}"
        )
        return
    
    # Check if proposal expired (only valid for 1 turn)
    if world.turn - proposal_found["turn"] > 1:
        engine.logs.append(
            f"[FOREIGN] {proposal_type} proposal from {proposer_id} has expired"
        )
        return
    
    if not accept:
        engine.logs.append(
            f"[FOREIGN] {nation_id} REJECTS {proposal_type} proposal from {proposer_id}"
        )
        return
    
    # Accept the proposal
    if proposal_type == "PEACE":
        world.relationship_matrix[nation_id][proposer_id] = "PEACE"
        world.relationship_matrix[proposer_id][nation_id] = "PEACE"
        engine.logs.append(
            f"[FOREIGN] 🕊️ Peace treaty signed between {nation_id} and {proposer_id}"
        )
    
    elif proposal_type == "ALLIANCE":
        world.relationship_matrix[nation_id][proposer_id] = "ALLIANCE"
        world.relationship_matrix[proposer_id][nation_id] = "ALLIANCE"
        engine.adjust_trust(nation_id, proposer_id, 10)  # 0-100 scale
        engine.adjust_trust(proposer_id, nation_id, 10)
        engine.logs.append(
            f"[FOREIGN] 🤝 ALLIANCE formed between {nation_id} and {proposer_id}!"
        )


def clear_expired_proposals(world: 'WorldState') -> None:
    """Clear all proposals older than 1 turn. Call at start of each turn."""
    current_turn = world.turn
    for nation in world.nations.values():
        nation.pending_proposals = [
            p for p in nation.pending_proposals 
            if current_turn - p["turn"] <= 1
        ]
