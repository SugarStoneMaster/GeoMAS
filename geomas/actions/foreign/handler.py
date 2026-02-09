"""
Foreign Affairs Action Handler.

Executes diplomatic actions (one action per turn).
"""

from typing import TYPE_CHECKING, Optional
import uuid
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
    world = engine.world
    
    # 1. PROCESS RESPONSES (Inbox)
    if payload.proposal_responses:
        for response in payload.proposal_responses:
            respond_to_proposal(
                engine, 
                nation_id, 
                response
            )

    # 2. PROCESS ACTIVE MEASURE (Agenda)
    if not payload.action_type or payload.action_type == ForeignActionType.IDLE:
        return

    # Validate active target exists (if required by action)
    if not payload.target_nation_id:
        # IDLE doesn't need target, but others do
        if payload.action_type != ForeignActionType.IDLE:
             engine.logs.append(f"[FOREIGN] No target nation specified for {payload.action_type}")
             return
    
    target_id = payload.target_nation_id
    
    if target_id and target_id not in world.nations:
        engine.logs.append(f"[FOREIGN] Target nation {target_id} not found")
        return
    
    # Dispatch to appropriate handler
    if payload.action_type == ForeignActionType.SEND_DIPLOMATIC_MESSAGE:
        _execute_send_message(engine, nation_id, target_id, payload.diplomatic_message_type, payload.message)
    
    elif payload.action_type == ForeignActionType.FORMAL_DECLARATION_OF_WAR:
        _execute_declare_war(engine, nation_id, target_id, payload.message)
    
    elif payload.action_type == ForeignActionType.BREAK_TREATY:
        _execute_break_treaty(engine, nation_id, target_id, payload.message)
    
    elif payload.action_type == ForeignActionType.REQUEST_PEACE:
        _execute_request_peace(engine, nation_id, target_id, payload.message)
    
    elif payload.action_type == ForeignActionType.PROPOSE_ALLIANCE:
        _execute_propose_alliance(engine, nation_id, target_id, payload.message)


def _execute_send_message(
    engine: 'ActionEngine',
    sender_id: str,
    target_id: str,
    message_type: Optional[DiplomaticMessageType],
    message: Optional[str] = None
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
    
    if not message_type:
        engine.logs.append(f"[FOREIGN] Missing message_type for SEND_DIPLOMATIC_MESSAGE")
        return
    
    msg_type = message_type
    
    trust_delta = MESSAGE_TRUST_IMPACT[msg_type]
    
    # Apply trust change (bidirectional for PRAISE, unidirectional for negative)
    engine.adjust_trust(sender_id, target_id, trust_delta)
    if msg_type == DiplomaticMessageType.PRAISE:
        engine.adjust_trust(target_id, sender_id, trust_delta)
    
    # Set cooldown
    sender.message_cooldown[target_id] = current_turn
    
    msg_str = f" Message: '{message}'" if message else ""
    engine.logs.append(
        f"[FOREIGN] {sender_id} sends {msg_type.value} to {target_id}. Trust impact: {trust_delta:+.1f}.{msg_str}"
    )


def _execute_declare_war(
    engine: 'ActionEngine',
    aggressor_id: str,
    target_id: str,
    message: Optional[str] = None
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
    
    msg_str = f" Message: '{message}'" if message else ""
    engine.logs.append(
        f"[FOREIGN] ⚔️ {aggressor_id} DECLARES WAR on {target_id}!{msg_str}"
    )
    
    # Global notification
    engine.world.global_events.append(
        f"[Turn {world.turn}] WAR DECLARED: {aggressor_id} vs {target_id}"
    )


def _execute_break_treaty(
    engine: 'ActionEngine',
    breaker_id: str,
    target_id: str,
    message: Optional[str] = None
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
    
    msg_str = f" Message: '{message}'" if message else ""
    engine.logs.append(
        f"[FOREIGN] 💔 {breaker_id} BREAKS alliance with {target_id}. Trust penalty applied.{msg_str}"
    )


def _execute_request_peace(
    engine: 'ActionEngine',
    requester_id: str,
    target_id: str,
    message: Optional[str] = None
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
        "id": str(uuid.uuid4())[:8],
        "type": "PEACE",
        "from": requester_id,
        "turn": world.turn,
        "message": message
    })
    
    msg_str = f" Message: '{message}'" if message else ""
    msg_str = f" Message: '{message}'" if message else ""
    summary = f"[FOREIGN] 🕊️ {requester_id} requests peace with {target_id}. Awaiting response.{msg_str}"
    engine.logs.append(summary)
    
    # Global notification (Real Event)
    engine.world.global_events.append(summary)


def _execute_propose_alliance(
    engine: 'ActionEngine',
    proposer_id: str,
    target_id: str,
    message: Optional[str] = None
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

    # Check if already proposed to prevent spam
    for p in target_nation.pending_proposals:
        if p["from"] == proposer_id and p["type"] == "ALLIANCE":
            engine.logs.append(f"[FOREIGN] Alliance proposal to {target_id} already pending")
            return
    
    target_nation.pending_proposals.append({
        "id": str(uuid.uuid4())[:8],
        "type": "ALLIANCE",
        "from": proposer_id,
        "turn": world.turn,
        "message": message
    })

    
    msg_str = f" Message: '{message}'" if message else ""
    msg_str = f" Message: '{message}'" if message else ""
    summary = f"[FOREIGN] 🤝 {proposer_id} proposes alliance to {target_id}. Awaiting response.{msg_str}"
    engine.logs.append(summary)
    
    # Global notification (Real Event)
    engine.world.global_events.append(summary)


# --- RESPONSE ACTIONS ---

def respond_to_proposal(
    engine: 'ActionEngine',
    nation_id: str,
    response: 'ProposalResponse'
) -> None:
    """
    Respond to a pending proposal (ACCEPT or REJECT).
    """
    world = engine.world
    nation = world.nations[nation_id]
    accept = (response.response == "ACCEPT")
    message = response.message
    
    # Find and remove the proposal
    proposal_found = None
    for i, prop in enumerate(nation.pending_proposals):
        # Match by ID now
        if prop.get("id") == response.proposal_id:
            proposal_found = nation.pending_proposals.pop(i)
            break
            
    if not proposal_found:
        engine.logs.append(
            f"[FOREIGN] No pending proposal found with ID {response.proposal_id}"
        )
        return

    proposer_id = proposal_found["from"]
    proposal_type = proposal_found["type"]
    
    # Check if proposal expired (only valid for 1 turn)
    if world.turn - proposal_found["turn"] > 1:
        engine.logs.append(
            f"[FOREIGN] {proposal_type} proposal from {proposer_id} has expired"
        )
        return
    
    msg_str = f" Message: '{message}'" if message else ""
    if not accept:
        engine.logs.append(
            f"[FOREIGN] {nation_id} REJECTS {proposal_type} proposal from {proposer_id}.{msg_str}"
        )
        return
    
    # Accept the proposal
    if proposal_type == "PEACE":
        world.relationship_matrix[nation_id][proposer_id] = "PEACE"
        world.relationship_matrix[proposer_id][nation_id] = "PEACE"
        engine.logs.append(
            f"[FOREIGN] 🕊️ Peace treaty signed between {nation_id} and {proposer_id}.{msg_str}"
        )
    
    elif proposal_type == "ALLIANCE":
        world.relationship_matrix[nation_id][proposer_id] = "ALLIANCE"
        world.relationship_matrix[proposer_id][nation_id] = "ALLIANCE"
        engine.adjust_trust(nation_id, proposer_id, 10)  # 0-100 scale
        engine.adjust_trust(proposer_id, nation_id, 10)
        engine.logs.append(
            f"[FOREIGN] 🤝 ALLIANCE formed between {nation_id} and {proposer_id}!{msg_str}"
        )


def clear_expired_proposals(world: 'WorldState') -> None:
    """Clear all proposals older than 1 turn. Call at start of each turn."""
    current_turn = world.turn
    for nation in world.nations.values():
        proposals = nation.pending_proposals
        # Log expired ones? We need the engine to log.
        # For now, just clear them to prevent infinite growth.
        
        nation.pending_proposals = [
            p for p in proposals 
            if current_turn - p["turn"] <= 1
        ]

