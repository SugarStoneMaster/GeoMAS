
import pytest
from geomas.schemas.world import WorldState, NationState, TerrainType
from geomas.actions.engine import ActionEngine
from geomas.actions.economy.schemas import EconomicActionType, EconomicPayload
from geomas.actions.defense.schemas import DefensePayload
from geomas.actions.foreign.schemas import ForeignPayload
from geomas.agents.context.events import ContextManager
from geomas.simulation.phases import run_opinion_phase
from geomas.agents.schemas import (
    CountryEnvelope, GlobalStrategy, 
    ForeignIntentType, DefenseIntentType
)

@pytest.fixture
def world():
    w = WorldState(turn=1)
    w.nations["NAT_A"] = NationState(id="NAT_A", name="Nation A", color="blue", total_budget=1000, total_materials=500, total_food=500, total_energy=500, public_satisfaction=50)
    w.nations["NAT_B"] = NationState(id="NAT_B", name="Nation B", color="red", total_budget=1000, total_materials=500, total_food=500, total_energy=500, public_satisfaction=50)
    return w

def create_valid_envelope(nation_id, turn, economic_payload):
    return CountryEnvelope(
        turn=turn,
        sender_id=nation_id,
        global_strategy=GlobalStrategy.COALITION_BUILDER,
        public_statement="Test statement",
        # Economy
        economic_payload=economic_payload,
        economic_private_reasoning="Test reasoning",
        # Defense (Defaults)
        defense_payload=DefensePayload(),
        defense_public_intent=DefenseIntentType.IDLE,
        defense_private_intent=DefenseIntentType.IDLE,
        defense_private_reasoning="Test reasoning",
        # Foreign (Defaults)
        foreign_payload=ForeignPayload(),
        foreign_public_intent=ForeignIntentType.IDLE,
        foreign_private_intent=ForeignIntentType.IDLE,
        foreign_private_reasoning="Test reasoning"
    )

def test_invest_welfare_message_in_opinion_context(world):
    engine = ActionEngine(world)
    payload = EconomicPayload(
        action_type=EconomicActionType.INVEST_WELFARE,
        amount=100,
        message="Prosperity for everyone!"
    )
    
    envelope = create_valid_envelope("NAT_A", 1, payload)
    
    # Execute action
    engine.execute_envelope(envelope)
    
    # Mock Opinion Agent to capture context
    class MockOpinionAgent:
        def __init__(self):
            self.captured_government_actions = []
        def react(self, events, government_actions, current_satisfaction, at_war, turn):
            self.captured_government_actions = government_actions
            from geomas.agents.opinion import OpinionResponse
            return OpinionResponse(multiplier_increase=1.0, multiplier_decrease=1.0, mood="CONTENT", reasoning="Test")
            
    opinion_agents = {"NAT_A": MockOpinionAgent()}
    
    run_opinion_phase(
        world=world,
        turn_logs=[],
        opinion_agents=opinion_agents,
        envelopes=[envelope],
        turn=1
    )
    
    # Verify message is in captured actions
    found = False
    for action in opinion_agents["NAT_A"].captured_government_actions:
        if "Prosperity for everyone!" in action:
            found = True
            break
    assert found, f"Message not found in government actions: {opinion_agents['NAT_A'].captured_government_actions}"

def test_trade_proposal_message_in_context_manager(world):
    cm = ContextManager()
    cm.initialize_from_world(world)
    
    payload = EconomicPayload(
        action_type=EconomicActionType.TRADE_PROPOSAL,
        target_nation_id="NAT_B",
        give_type="food",
        give_amount=100,
        want_type="energy",
        message="Friendship through trade"
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
        if "Friendship through trade" in event.summary:
            found_event = True
            break
    assert found_event, "Message not found in global events"
    
    # 2. Check Nation Actions — verify descriptive summary
    found_action = False
    for action in cm.nation_actions["NAT_A"]:
        if "Trade with" in action.action_summary and "food" in action.action_summary:
            found_action = True
            break
    assert found_action, f"Trade action not found in nation actions: {[a.action_summary for a in cm.nation_actions['NAT_A']]}"
