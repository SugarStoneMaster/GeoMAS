
import pytest
from geomas.schemas.world import WorldState, NationState
from geomas.actions.engine import ActionEngine
from geomas.actions.foreign.schemas import ForeignActionType, ForeignPayload, DiplomaticMessageType
from geomas.actions.defense.schemas import DefensePayload
from geomas.actions.economy.schemas import EconomicPayload
from geomas.agents.context.memory import ContextManager
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
        message="Let's be brothers forever!"
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
    assert "**ALLIANCE proposal from Nation A**" in context
    assert "> \"Let's be brothers forever!\"" in context

def test_respond_to_proposal_carries_message(world):
    # Setup pending proposal
    nat_b = world.nations["NAT_B"]
    nat_b.pending_proposals.append({
        "type": "ALLIANCE",
        "from": "NAT_A",
        "turn": 1,
        "message": "Original proposal"
    })
    
    engine = ActionEngine(world)
    payload = ForeignPayload(
        action_type=ForeignActionType.REJECT_PROPOSAL,
        target_nation_id="NAT_A",
        proposal_ref_type="ALLIANCE",
        message="Too early for that."
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
    
    # Update context manager
    cm.update_after_turn(turn=1, envelopes=[envelope], world=world)
    
    # 1. Check Global Events
    found_event = False
    for event in cm.global_events:
        if "Your mountains are beautiful." in event.summary:
            found_event = True
            break
    assert found_event, "Message not found in global events"
    
    # 2. Check Nation Actions
    found_action = False
    for action in cm.nation_actions["NAT_A"]:
        if "Your mountains are beautiful." in action.action_summary:
            found_action = True
            break
    assert found_action, "Message not found in nation actions"
