"""
Foreign Affairs Action Handler.

Executes diplomatic actions (one action per turn).
"""

from typing import TYPE_CHECKING, Optional
import zlib
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
        nation = world.nations[nation_id]
        if not nation.pending_proposals:
            # Guard: LLM hallucinated proposal responses when no proposals exist
            engine.logs.append(
                f"📜 [FOREIGN] {nation_id} tried to respond to proposals, but has no pending proposals. Skipping."
            )
        else:
            response_details = []
            for response in payload.proposal_responses:
                success, msg, event_type, related_nation_id = respond_to_proposal(
                    engine, 
                    nation_id, 
                    response
                )
                response_details.append({
                    "proposal_id": response.proposal_id,
                    "success": success,
                    "message": msg,
                    "event_type": event_type,
                    "target_id": related_nation_id
                })
            
            # Store details in execution outcome for ContextManager
            if not payload.execution_outcome.details:
                payload.execution_outcome.details = {}
            payload.execution_outcome.details["responses"] = response_details

    # 2. PROCESS ACTIVE MEASURE (Agenda)
    if not payload.action_type or payload.action_type == ForeignActionType.IDLE:
        if payload.action_type == ForeignActionType.IDLE:
            payload.execution_outcome.status = "SUCCESS"
            payload.execution_outcome.reason = "Minister is idle."
            if payload.message:
                engine.logs.append(f"📜 [FOREIGN] IDLE: {payload.message}")
        return

    # Validate active target exists (if required by action)
    if not payload.target_nation_id:
        # IDLE doesn't need target, but others do
        if payload.action_type != ForeignActionType.IDLE:
             engine.logs.append(f"📜 [FOREIGN] No target nation specified for {payload.action_type}")
             return
    
    target_id = payload.target_nation_id
    
    if target_id and target_id not in world.nations:
        engine.logs.append(f"📜 [FOREIGN] Target nation {target_id} not found")
        return
    
    # Dispatch to appropriate handler
    if payload.action_type == ForeignActionType.SEND_DIPLOMATIC_MESSAGE:
        success, reason, trust_impacted = _execute_send_message(engine, nation_id, target_id, payload.diplomatic_message_type, payload.message)
        payload.execution_outcome.status = "SUCCESS" if success else "FAILED"
        payload.execution_outcome.reason = reason
        if success:
            payload.execution_outcome.details = {
                "message_type": payload.diplomatic_message_type, 
                "target": target_id,
                "trust_impacted": trust_impacted
            }
    
    elif payload.action_type == ForeignActionType.FORMAL_DECLARATION_OF_WAR:
        success, reason = _execute_declare_war(engine, nation_id, target_id, payload.message)
        payload.execution_outcome.status = "SUCCESS" if success else "FAILED"
        payload.execution_outcome.reason = reason
        if success:
             payload.execution_outcome.details = {"target": target_id}
    
    elif payload.action_type == ForeignActionType.BREAK_TREATY:
        success, reason = _execute_break_treaty(engine, nation_id, target_id, payload.message)
        payload.execution_outcome.status = "SUCCESS" if success else "FAILED"
        payload.execution_outcome.reason = reason
    
    elif payload.action_type == ForeignActionType.REQUEST_PEACE:
        success, reason = _execute_request_peace(engine, nation_id, target_id, payload.message)
        payload.execution_outcome.status = "SUCCESS" if success else "FAILED"
        payload.execution_outcome.reason = reason
    
    elif payload.action_type == ForeignActionType.PROPOSE_ALLIANCE:
        success, reason = _execute_propose_alliance(engine, nation_id, target_id, payload.treaty_tier, payload.message)
        payload.execution_outcome.status = "SUCCESS" if success else "FAILED"
        payload.execution_outcome.reason = reason


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
    cooldown_active = (current_turn - last_msg_turn < MESSAGE_COOLDOWN_TURNS)
    
    if not message_type:
        engine.logs.append(f"📜 [FOREIGN] Missing message_type for SEND_DIPLOMATIC_MESSAGE")
        return False, "Missing message_type"
    
    msg_type = message_type
    
    if cooldown_active:
        turns_left = MESSAGE_COOLDOWN_TURNS - (current_turn - last_msg_turn)
        trust_delta = 0
        update_cooldown = False
        engine.logs.append(
            f"📜 [FOREIGN] {sender_id} sends message to {target_id} (Cooldown active: {turns_left} turns left). No trust impact."
        )
    else:
        trust_delta = MESSAGE_TRUST_IMPACT[msg_type]
        update_cooldown = True
    
    # Apply trust change (bidirectional for PRAISE, unidirectional for negative)
    if trust_delta != 0:
        engine.adjust_trust(sender_id, target_id, trust_delta)
        if msg_type == DiplomaticMessageType.PRAISE:
            engine.adjust_trust(target_id, sender_id, trust_delta)
    
    # Set cooldown ONLY if it wasn't active (do not reset timer if spamming)
    if update_cooldown:
        sender.message_cooldown[target_id] = current_turn
    
    msg_str = f" Message: '{message}'" if message else ""
    engine.logs.append(
        f"📜 [FOREIGN] {sender_id} sends {msg_type.value} to {target_id}. Trust impact: {trust_delta:+.1f}.{msg_str}"
    )
    return True, "Message sent", (trust_delta != 0)


def _execute_declare_war(
    engine: 'ActionEngine',
    aggressor_id: str,
    target_id: str,
    message: Optional[str] = None
) -> None:
    """Formally declare war on target nation."""
    world = engine.world
    
    from geomas.schemas.world import RelationshipState
    current_rel = world.relationship_matrix.get(aggressor_id, {}).get(target_id, RelationshipState.PEACE)
    
    if current_rel == RelationshipState.WAR:
        engine.logs.append(f"⚔️ [FOREIGN] {aggressor_id} already at war with {target_id}")
        return False, "Already at war"
    
    # Set relationship to WAR (both directions)
    world.relationship_matrix.setdefault(aggressor_id, {})[target_id] = RelationshipState.WAR
    world.relationship_matrix.setdefault(target_id, {})[aggressor_id] = RelationshipState.WAR
    
    # Trust → 0 between the two
    world.trust_matrix.setdefault(aggressor_id, {})[target_id] = 0
    world.trust_matrix.setdefault(target_id, {})[aggressor_id] = 0
    
    # --- INIT WAR STATS ---
    from geomas.schemas.world import WarStats
    aggressor = world.nations[aggressor_id]
    target = world.nations[target_id]
    
    aggressor.active_wars[target_id] = WarStats(
        start_turn=world.turn,
        initiator_id=aggressor_id,
        original_provinces=len(target.province_ids)
    )
    target.active_wars[aggressor_id] = WarStats(
        start_turn=world.turn,
        initiator_id=aggressor_id,
        original_provinces=len(target.province_ids)
    )

    msg_str = f" Message: '{message}'" if message else ""
    engine.logs.append(
        f"⚔️ [FOREIGN] {aggressor_id} DECLARES WAR on {target_id}!{msg_str}"
    )
    
    # Global notification
    engine.world.global_events.append(
        f"[Turn {world.turn}] ⚔️ WAR DECLARED: {aggressor_id} vs {target_id}"
    )

    # CALL TO ARMS: Notify allies of the victim
    _generate_call_to_arms(engine, aggressor_id, target_id)

    return True, "War declared"


def _generate_call_to_arms(
    engine: 'ActionEngine',
    aggressor_id: str,
    victim_id: str,
    attack_type: str = "attacked"
) -> None:
    """Generate specialized notification for nations with Mutual Defense pacts with the victim."""
    world = engine.world
    
    for ally_id, relationship in world.relationship_matrix.get(victim_id, {}).items():
        if relationship == RelationshipState.MUTUAL_DEFENSE:
            # Check if the ally is already at war with the aggressor
            current_ally_rel = world.relationship_matrix.get(ally_id, {}).get(aggressor_id, RelationshipState.PEACE)
            if current_ally_rel != RelationshipState.WAR:
                summary = f"🚨 [CALL_TO_ARMS] {ally_id}: Your ally {victim_id} was {attack_type} by {aggressor_id}! You are summoned to honor your MUTUAL_DEFENSE pact."
                engine.logs.append(summary)
                world.global_events.append(summary)
                
                # DILEMMA PENALTY: 
                # If the ally (B) is also allied with the aggressor (C), 
                # B loses trust in C for creating a diplomatic conflict.
                if world.relationship_matrix.get(ally_id, {}).get(aggressor_id) == RelationshipState.MUTUAL_DEFENSE:
                    penalty = -15.0
                    engine.adjust_trust(ally_id, aggressor_id, penalty)
                    engine.logs.append(
                        f"📉 [DIPLOMACY] {ally_id} trust in {aggressor_id} decreased by {penalty:+.1f} "
                        f"(Cross-Alliance Conflict: {aggressor_id} attacked shared ally {victim_id})."
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
    
    if current_rel not in [RelationshipState.NON_AGGRESSION, RelationshipState.MUTUAL_DEFENSE]:
        engine.logs.append(f"💔 [FOREIGN] No treaty exists with {target_id} to break")
        return False, "No treaty exists"
    
    # Set relationship back to PEACE
    world.relationship_matrix[breaker_id][target_id] = "PEACE"
    world.relationship_matrix[target_id][breaker_id] = "PEACE"
    
    # Trust penalty for the one who breaks (-50 on 0-100 scale)
    engine.adjust_trust(target_id, breaker_id, -50)
    
    msg_str = f" Message: '{message}'" if message else ""
    engine.logs.append(
        f"💔 [FOREIGN] {breaker_id} BREAKS alliance with {target_id}. Trust penalty applied.{msg_str}"
    )
    return True, "Alliance broken"


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
        engine.logs.append(f"🕊️ [FOREIGN] Not at war with {target_id}, no peace needed")
        return False, "Not at war"
    
    # Add pending proposal to target nation
    target_nation = world.nations[target_id]
    # FIX: Deterministic proposal ID instead of uuid4
    proposal_id = hex(zlib.adler32(f"{world.turn}{requester_id}{target_id}PEACE".encode()))[2:]
    target_nation.pending_proposals.append({
        "id": proposal_id,
        "type": "PEACE",
        "from": requester_id,
        "turn": world.turn,
        "message": message
    })
    
    msg_str = f" Message: '{message}'" if message else ""
    summary = f"🕊️ [FOREIGN] {requester_id} requests peace with {target_id}. Awaiting response.{msg_str}"
    engine.logs.append(summary)
    
    # Global notification (Real Event)
    engine.world.global_events.append(summary)
    
    # Track sent proposal
    world.nations[requester_id].sent_proposals.append({
        "id": proposal_id,
        "type": "PEACE",
        "to": target_id,
        "turn": world.turn,
        "message": message,
        "status": "PENDING",
        "resolved_turn": -1
    })
    
    return True, "Peace requested"


def _execute_propose_alliance(
    engine: 'ActionEngine',
    proposer_id: str,
    target_id: str,
    tier: Optional['TreatyTier'] = None,
    message: Optional[str] = None
) -> None:
    """
    Propose alliance with target nation.
    Requires specifying a tier (NON_AGGRESSION or MUTUAL_DEFENSE).
    Creates a pending proposal that target must accept/reject next turn.
    """
    world = engine.world
    
    # Fallback to NON_AGGRESSION if tier not specified
    # Fallback to NON_AGGRESSION if tier not specified
    # Fallback to NON_AGGRESSION if tier not specified
    if not tier:
        from geomas.actions.foreign.schemas import TreatyTier
        
        # Smart Inference based on message content
        inferred_tier = TreatyTier.NON_AGGRESSION
        msg_lower = message.lower() if message else ""
        
        strong_md_keywords = [
            "mutual defense", 
            "defense pact", 
            "military alliance", 
            "fight together",
            "full alliance",
            "defend each other"
        ]
        
        strong_na_keywords = [
            "non aggression",
            "non-aggression",
            "peace pact",
            "no attack",
            "neutrality pact"
        ]
        
        if any(k in msg_lower for k in strong_md_keywords):
            inferred_tier = TreatyTier.MUTUAL_DEFENSE
        elif any(k in msg_lower for k in strong_na_keywords):
            inferred_tier = TreatyTier.NON_AGGRESSION
            
        tier = inferred_tier
        
        engine.logs.append(
            f"⚠️ [FOREIGN] {proposer_id} alliance proposal missing tier. "
            f"Inferred {tier.name} from message content."
        )

    current_rel = world.relationship_matrix.get(proposer_id, {}).get(target_id, RelationshipState.PEACE)
    
    # Check if we can proceed (Allow UPGRADE/DOWNGRADE)
    if current_rel in [RelationshipState.NON_AGGRESSION, RelationshipState.MUTUAL_DEFENSE]:
        if current_rel == tier:
            engine.logs.append(f"🤝 [FOREIGN] Already have {current_rel} treaty with {target_id}. No change needed.")
            return False, f"Already has {current_rel.value}"
        else:
            # Upgrade or Downgrade
            pass # Proceed to propose change
    
    if current_rel == "WAR":
        engine.logs.append(f"🤝 [FOREIGN] Cannot propose alliance while at war with {target_id}")
        return False, "Currently at war"
    
    # Trust check REMOVED: Agents decide freely.
    # trust = world.trust_matrix.get(proposer_id, {}).get(target_id, 50)
    # if trust < 60: ...
    
    # Add pending proposal to target nation
    target_nation = world.nations[target_id]

    # Check if already proposed to prevent spam
    for p in target_nation.pending_proposals:
        if p["from"] == proposer_id and p["type"] == "ALLIANCE":
            engine.logs.append(f"🤝 [FOREIGN] Alliance proposal to {target_id} already pending")
            return False, "Proposal already pending"

    # FIX: Deterministic proposal ID instead of uuid4
    proposal_id = hex(zlib.adler32(f"{world.turn}{proposer_id}{target_id}ALLIANCE".encode()))[2:]
    target_nation.pending_proposals.append({
        "id": proposal_id,
        "type": "ALLIANCE",
        "from": proposer_id,
        "turn": world.turn,
        "message": message,
        "tier": tier
    })

    msg_str = f" Message: '{message}'" if message else ""
    summary = f"🤝 [FOREIGN] {proposer_id} proposes alliance to {target_id}. Awaiting response.{msg_str}"
    engine.logs.append(summary)
    
    # Global notification (Real Event)
    engine.world.global_events.append(summary)
    
    # Track sent proposal
    world.nations[proposer_id].sent_proposals.append({
        "id": proposal_id,
        "type": "ALLIANCE",
        "tier": tier,
        "to": target_id,
        "turn": world.turn,
        "message": message,
        "status": "PENDING",
        "resolved_turn": -1
    })
    
    return True, "Alliance proposed"


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
            f"📜 [FOREIGN] No pending proposal found with ID {response.proposal_id}"
        )
        return False, "Proposal not found", None, None

    proposer_id = proposal_found["from"]
    proposal_type = proposal_found["type"]
    
    # Check if proposal expired (only valid for 1 turn)
    if world.turn - proposal_found["turn"] > 1:
        engine.logs.append(
            f"📜 [FOREIGN] {proposal_type} proposal from {proposer_id} has expired"
        )
        return False, "Proposal expired", None, proposer_id
    
    msg_str = f" Message: '{message}'" if message else ""
    # Update sender's tracking
    sender_nation = world.nations.get(proposer_id)
    if sender_nation:
        for sent_p in sender_nation.sent_proposals:
            if sent_p["id"] == response.proposal_id:
                sent_p["status"] = "ACCEPTED" if accept else "REJECTED"
                sent_p["resolved_turn"] = world.turn
                break

    # Accept the proposal
    if proposal_type == "PEACE" and accept:
        world.relationship_matrix[nation_id][proposer_id] = "PEACE"
        world.relationship_matrix[proposer_id][nation_id] = "PEACE"
        engine.logs.append(
            f"🕊️ [FOREIGN] Peace treaty signed between {nation_id} and {proposer_id}.{msg_str}"
        )
    elif proposal_type == "ALLIANCE" and accept:
        tier = proposal_found.get("tier", RelationshipState.MUTUAL_DEFENSE)
        
        # Detect Change Type (Establish, Upgrade, Downgrade)
        old_tier = world.relationship_matrix.get(nation_id, {}).get(proposer_id, RelationshipState.PEACE)
        event_type = "formed"
        
        if old_tier == RelationshipState.PEACE:
            event_type = "FORMED"
        elif old_tier == RelationshipState.NON_AGGRESSION and tier == RelationshipState.MUTUAL_DEFENSE:
            event_type = "UPGRADED"
        elif old_tier == RelationshipState.MUTUAL_DEFENSE and tier == RelationshipState.NON_AGGRESSION:
            event_type = "DOWNGRADED"
        
        world.relationship_matrix[nation_id][proposer_id] = tier
        world.relationship_matrix[proposer_id][nation_id] = tier
        
        # Check for Risky Alliance (Bidirectional) - Check BEFORE trust boost
        target_trusts_proposer = world.trust_matrix.get(nation_id, {}).get(proposer_id, 50)
        proposer_trusts_target = world.trust_matrix.get(proposer_id, {}).get(nation_id, 50)
        
        if target_trusts_proposer < 50:
            engine.logs.append(
                f"⚠️ [FOREIGN] RISKY treaty for {nation_id}: trust in {proposer_id} is low ({target_trusts_proposer:.0f} < 50)!"
            )
            
        if proposer_trusts_target < 50:
             engine.logs.append(
                f"⚠️ [FOREIGN] RISKY treaty for {proposer_id}: trust in {nation_id} is low ({proposer_trusts_target:.0f} < 50)!"
            )

        engine.adjust_trust(nation_id, proposer_id, 10)  # 0-100 scale
        engine.adjust_trust(proposer_id, nation_id, 10)

        # Conflicting Alliance Penalty (Implicit Veto):
        # If Nation B allies with C, but B is already allied with A, and A is at war with C:
        # Nation A loses trust in Nation B.
        for ally_id, other_rel in world.relationship_matrix.get(nation_id, {}).items():
            if ally_id == proposer_id:
                continue
                
            # Check if ally_id is an actual ally
            if other_rel in [RelationshipState.NON_AGGRESSION, RelationshipState.MUTUAL_DEFENSE]:
                # Check if this ally is at war with the new partner (proposer_id)
                ally_vs_new = world.relationship_matrix.get(ally_id, {}).get(proposer_id)
                if ally_vs_new == RelationshipState.WAR:
                    penalty = -30
                    engine.adjust_trust(ally_id, nation_id, penalty)
                    engine.logs.append(
                        f"🚨 [FOREIGN] {ally_id} is OUTRAGED by {nation_id}'s alliance with its enemy {proposer_id}! Trust penalty: {penalty}"
                    )
            
        log_msg = f"🤝 [FOREIGN] {tier.value} {event_type} between {nation_id} and {proposer_id}!{msg_str}"
        engine.logs.append(log_msg)
        engine.world.global_events.append(f"[Turn {world.turn}] {log_msg}")
        
        return True, log_msg, event_type, proposer_id

    elif not accept:
         log_msg = f"📜 [FOREIGN] {nation_id} REJECTS {proposal_type} proposal from {proposer_id}.{msg_str}"
         engine.logs.append(log_msg)
         
         # Diplomatic Fatigue: Rejection damages trust slightly to discourage spam
         engine.adjust_trust(nation_id, proposer_id, -5)
         engine.adjust_trust(proposer_id, nation_id, -5)
         
         return True, log_msg, None, proposer_id
         
    return False, "Unknown error", None, None


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
        
        # Cleanup sent proposals (Retention: 1 turn after resolution)
        # Keep if:
        # 1. Status is PENDING (and not expired by time, i.e., <= 1 turn old? No, allow PENDING to stay until response or timeout)
        #    Actually, if pending proposal expired in target's inbox, we should mark it EXPIRED here too.
        #    Logic: If PENDING and age > 1 -> EXPIRED.
        # 2. Status is RESOLVED (ACCEPTED/REJECTED/EXPIRED) -> Keep for 1 turn after resolved_turn.
        
        new_sent = []
        for p in nation.sent_proposals:
            status = p.get("status", "PENDING")
            p_turn = p["turn"]
            
            # Auto-expire pending proposals older than 1 turn
            if status == "PENDING" and current_turn - p_turn > 1:
                p["status"] = "EXPIRED"
                p["resolved_turn"] = current_turn
                status = "EXPIRED"
            
            # Retention logic
            if status == "PENDING":
                 new_sent.append(p)
            else:
                # It is resolved. Keep only if current_turn <= resolved_turn + 25
                # Wait, if resolved at T, agent sees result at T+1.
                # We want history for 25 turns.
                resolved_turn = p.get("resolved_turn", current_turn)
                if current_turn - resolved_turn <= 25:
                    new_sent.append(p)
        
        nation.sent_proposals = new_sent

