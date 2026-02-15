
import pytest
from geomas.schemas.world import WorldState, NationState
from geomas.actions.engine import ActionEngine
from geomas.actions.foreign.schemas import ForeignActionType, ForeignPayload, DiplomaticMessageType, ProposalResponse, ForeignResponseAction, TreatyTier
from geomas.actions.defense.schemas import DefensePayload
from geomas.actions.economy.schemas import EconomicPayload
from geomas.agents.context.events import ContextManager
from geomas.agents.context.input.foreign import ForeignInputBuilder
from geomas.agents.schemas import CountryEnvelope, GlobalStrategy, EconomicIntentType, ForeignIntentType, DefenseIntentType

@pytest.fixture
def world():
    w = WorldState(turn=1)
    w.nations["NAT_A"] = NationState(id="NAT_A", name="Nation A", color="blue", total_budget=1000, public_satisfaction=50)
    w.nations["NAT_B"] = NationState(id="NAT_B", name="Nation B", color="red", total_budget=1000, public_satisfaction=50)
    w.trust_matrix = {"NAT_A": {"NAT_B": 50}, "NAT_B": {"NAT_A": 50}}
    w.relationship_matrix = {"NAT_A": {"NAT_B": "PEACE"}, "NAT_B": {"NAT_A": "PEACE"}}
    return w

def create_valid_envelope(nation_id, turn, foreign_payload):
    return CountryEnvelope(
        turn=turn,
        sender_id=nation_id,
        global_strategy=GlobalStrategy.COALITION_BUILDER,
        public_statement="Test statement",
        # Foreign
        foreign_payload=foreign_payload,
        foreign_public_intent=ForeignIntentType.COOPERATION,
        foreign_private_intent=ForeignIntentType.COOPERATION,
        foreign_private_reasoning="Test reasoning",
        # Defense (Defaults)
        defense_payload=DefensePayload(),
        defense_public_intent=DefenseIntentType.IDLE,
        defense_private_intent=DefenseIntentType.IDLE,
        defense_private_reasoning="Test",
        # Economy (Defaults)
        economic_payload=EconomicPayload(),
        economic_public_intent=EconomicIntentType.GROWTH,
        economic_private_intent=EconomicIntentType.GROWTH,
        economic_private_reasoning="Test"
    )

def test_alliance_proposal_carries_message(world):
    engine = ActionEngine(world)
    payload = ForeignPayload(
        action_type=ForeignActionType.PROPOSE_ALLIANCE,
        target_nation_id="NAT_B",
        message="Let's be brothers forever!",
        treaty_tier=TreatyTier.MUTUAL_DEFENSE
    )
    
    envelope = create_valid_envelope("NAT_A", 1, payload)
    
    # 1. Execute action
    # Trust must be > 60 for alliance proposal
    world.trust_matrix["NAT_A"]["NAT_B"] = 70
    engine.execute_envelope(envelope)
    
    # Verify storage in NAT_B's pending proposals
    nat_b = world.nations["NAT_B"]
    assert len(nat_b.pending_proposals) == 1
    assert nat_b.pending_proposals[0]["message"] == "Let's be brothers forever!"
    
    # 2. Verify display in ForeignInputBuilder
    ib = ForeignInputBuilder(world)
    context = ib.build("NAT_B", 1)
    assert "**ALLIANCE [MUTUAL_DEFENSE] proposal from Nation A**" in context
    assert "> \"Let's be brothers forever!\"" in context

def test_respond_to_proposal_carries_message(world):
    # Setup pending proposal
    nat_b = world.nations["NAT_B"]
    nat_b.pending_proposals.append({
        "id": "msg_test_id",
        "type": "ALLIANCE",
        "from": "NAT_A",
        "turn": 1,
        "message": "Original proposal",
        "tier": TreatyTier.MUTUAL_DEFENSE
    })
    
    engine = ActionEngine(world)
    from geomas.actions.foreign.schemas import ForeignActionType, ForeignPayload, DiplomaticMessageType, ProposalResponse, ForeignResponseAction
    from geomas.actions.common import Decision

    # In the test function:
    payload = ForeignPayload(
        action_type=ForeignActionType.IDLE,
        decision=Decision.APPROVE,
        proposal_responses=[
            ProposalResponse(
                proposal_id="msg_test_id",
                response=ForeignResponseAction.REJECT,
                message="Too early for that."
            )
        ]
    )
    
    envelope = create_valid_envelope("NAT_B", 2, payload)
    world.turn = 2
    
    # Execute rejection
    engine.execute_envelope(envelope)
    
    # Verify log entry
    found_log = False
    for log in engine.logs:
        if "REJECTS ALLIANCE" in log and "Too early for that." in log:
            found_log = True
            break
    assert found_log, f"Message not found in engine logs: {engine.logs}"

def test_foreign_message_in_context_manager(world):
    cm = ContextManager()
    cm.initialize_from_world(world)
    
    payload = ForeignPayload(
        action_type=ForeignActionType.SEND_DIPLOMATIC_MESSAGE,
        target_nation_id="NAT_B",
        diplomatic_message_type=DiplomaticMessageType.PRAISE,
        message="Your mountains are beautiful."
    )
    
    envelope = create_valid_envelope("NAT_A", 1, payload)
    
    # Execute action through engine to set outcome to SUCCESS
    engine = ActionEngine(world)
    engine.execute_envelope(envelope)
    
    # Update context manager
    cm.update_after_turn(turn=1, envelopes=[envelope], world=world)
    
    # 1. Check Global Events
    found_event = False
    for event in cm.global_events:
        if "Your mountains are beautiful." in event.summary:
            found_event = True
            break
    assert found_event, "Message not found in global events"
    
    # 2. Check Nation Actions — verify descriptive summary
    found_action = False
    for action in cm.nation_actions["NAT_A"]:
        if "Sent" in action.action_summary and "NAT_B" in action.action_summary:
            found_action = True
            break
    assert found_action, f"Diplomatic action not found in nation actions: {[a.action_summary for a in cm.nation_actions['NAT_A']]}"
    
    # 3. Check Input Builder INBOX
    ib = ForeignInputBuilder(world)
    context = ib.build("NAT_B", 1, context_manager=cm)
    
    assert "## Inbox" in context
    assert "Your mountains are beautiful" in context

def test_message_soft_cooldown(world):
    """
    Test Soft Cooldown behavior:
    1. Valid message -> Trust gain, Cooldown set.
    2. Cooldown message -> No Trust gain, Cooldown NOT reset, Message allowed.
    3. Post-cooldown message -> Trust gain, Cooldown reset.
    """
    engine = ActionEngine(world)
    sender = "NAT_A"
    target = "NAT_B"
    
    # 1. First Message (Turn 1)
    payload1 = ForeignPayload(
        action_type=ForeignActionType.SEND_DIPLOMATIC_MESSAGE,
        target_nation_id=target,
        diplomatic_message_type=DiplomaticMessageType.PRAISE,
        message="Message 1"
    )
    envelope1 = create_valid_envelope(sender, 1, payload1)
    engine.execute_envelope(envelope1)
    
    # Verify trust increase (+10 for Praise from 50)
    assert world.trust_matrix[sender][target] == 60.0
    # Verify cooldown set to turn 1
    assert world.nations[sender].message_cooldown[target] == 1
    
    # 2. Second Message (Turn 2 - Cooldown Active)
    world.turn = 2
    # Clear logs to check for new ones
    engine.logs = []
    
    payload2 = ForeignPayload(
        action_type=ForeignActionType.SEND_DIPLOMATIC_MESSAGE,
        target_nation_id=target,
        diplomatic_message_type=DiplomaticMessageType.PRAISE,
        message="Message 2 (Spam)"
    )
    envelope2 = create_valid_envelope(sender, 2, payload2)
    engine.execute_envelope(envelope2)
    
    # Verify NO trust increase (still 60)
    assert world.trust_matrix[sender][target] == 60.0
    # Verify cooldown NOT reset (still 1)
    assert world.nations[sender].message_cooldown[target] == 1
    
    # Verify specific log
    assert any("Cooldown active" in log for log in engine.logs)
    assert any("No trust impact" in log for log in engine.logs)
    
    # 3. Third Message (Turn 6 - Cooldown Expired: 1 + 5 = 6)
    world.turn = 6
    payload3 = ForeignPayload(
        action_type=ForeignActionType.SEND_DIPLOMATIC_MESSAGE,
        target_nation_id=target,
        diplomatic_message_type=DiplomaticMessageType.PRAISE,
        message="Message 3 (Valid)"
    )
    envelope3 = create_valid_envelope(sender, 6, payload3)
    engine.execute_envelope(envelope3)
    
    # Verify trust increase (+10 -> 70)
    assert world.trust_matrix[sender][target] == 70.0
    # Verify cooldown reset to turn 6
    assert world.nations[sender].message_cooldown[target] == 6

def test_proposal_tracking_lifecycle(world):
    """
    Test Proposal Tracking:
    1. Send Proposal -> Saved in sent_proposals (PENDING).
    2. Input Builder -> Shows PENDING.
    3. Respond (Accept) -> Saved as ACCEPTED.
    4. Input Builder -> Shows ACCEPTED.
    5. Cleanup -> Removed after 1 turn.
    """
    engine = ActionEngine(world)
    sender = "NAT_A"
    target = "NAT_B"
    
    # 1. Send Proposal (Turn 10)
    world.turn = 10
    payload = ForeignPayload(
        action_type=ForeignActionType.PROPOSE_ALLIANCE,
        target_nation_id=target,
        message="Ally?",
        treaty_tier=TreatyTier.MUTUAL_DEFENSE
    )
    # Ensure trust is high enough
    world.trust_matrix[sender][target] = 80
    envelope = create_valid_envelope(sender, 10, payload)
    engine.execute_envelope(envelope)
    
    # Check sent_proposals
    sent = world.nations[sender].sent_proposals
    assert len(sent) == 1
    assert sent[0]["status"] == "PENDING"
    assert sent[0]["to"] == target
    
    # 2. Check Input Builder
    ib = ForeignInputBuilder(world)
    context = ib.build(sender, 10)
    assert "## Sent proposals" in context
    assert "⏳ **ALLIANCE (MUTUAL_DEFENSE) to Nation B**" in context
    assert "Status: **PENDING**" in context
    
    # 3. Respond (Turn 11)
    world.turn = 11
    # Target responds ACCEPT
    proposal_id = sent[0]["id"]
    from geomas.actions.foreign.schemas import ProposalResponse, ForeignResponseAction
    
    # Simulate valid response payload from Target
    response_payload = ForeignPayload(
        proposal_responses=[
            ProposalResponse(
                proposal_id=proposal_id,
                response=ForeignResponseAction.ACCEPT,
                message="Yes!"
            )
        ]
    )
    # Response usually happens via execute_foreign -> respond_to_proposal
    # We call respond_to_proposal directly or via engine?
    # Let's use handler directly to simulate target action
    from geomas.actions.foreign.handler import respond_to_proposal
    respond_to_proposal(engine, target, response_payload.proposal_responses[0])
    
    # Check status updated
    assert sent[0]["status"] == "ACCEPTED"
    assert sent[0]["resolved_turn"] == 11
    
    # 4. Check Input Builder again (Sender sees result)
    context_resolved = ib.build(sender, 11)
    assert "✅ **ALLIANCE (MUTUAL_DEFENSE) to Nation B**" in context_resolved
    assert ": **ACCEPTED**" in context_resolved
    
    # 5. Cleanup (Turn 13 - >1 turn after resolution)
    # Turn 12: Still visible (11 + 1 >= 12)
    world.turn = 12
    from geomas.actions.foreign.handler import clear_expired_proposals
    clear_expired_proposals(world)
    assert len(world.nations[sender].sent_proposals) == 1 
    
    # Check updated Input Builder (History Section)
    context_history = ib.build(sender, 12)
    assert "## Proposal history" in context_history
    assert "✅ **ALLIANCE (MUTUAL_DEFENSE) to Nation B**" in context_history
    
    # Turn 35: Still visible (11 + 24 <= 35)
    world.turn = 35
    clear_expired_proposals(world)
    assert len(world.nations[sender].sent_proposals) == 1

    # Turn 38: Removed (11 + 25 < 38) -> Wait, condition is current - resolved <= 25.
    # If resolved=11. 36 - 11 = 25 (Keep). 37 - 11 = 26 (Remove).
    
    world.turn = 37
    clear_expired_proposals(world)
    assert len(world.nations[sender].sent_proposals) == 0
