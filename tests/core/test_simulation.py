import pytest
import sys
import os
from typing import Type

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from geomas.simulation import SimulationEngine
from geomas.agents.llm_client import LLMClient
from geomas.agents.schemas import (
    CountryEnvelope, GlobalStrategy, PublicIntent, 
    MilitaryIntent, MilitaryIntentType,
    EconomicIntent, EconomicIntentType,
    ForeignIntent, ForeignIntentType,
    DefenseProposal, EconomicProposal, ForeignProposal
)
from geomas.actions.schemas import (
    ActionType, MilitaryPayload, EconomicPayload, ForeignPayload, DecisionSource
)

# --- MOCK CLIENT ---
class SimMockLLM(LLMClient):
    def __init__(self): pass
    
    def query_agent(self, system_prompt, user_prompt, response_model, max_retries=3):
        # Return valid dummy objects
        if response_model == DefenseProposal:
            return DefenseProposal(
                intent=MilitaryIntent(type=MilitaryIntentType.IDLE, reasoning="Peace"),
                payload=MilitaryPayload(source=DecisionSource.MINISTRY_ADVICE, moves=[]),
                urgency=1
            )
        elif response_model == EconomicProposal:
            return EconomicProposal(
                intent=EconomicIntent(type=EconomicIntentType.GROWTH, reasoning="Grow"),
                payload=EconomicPayload(source=DecisionSource.MINISTRY_ADVICE, action_type=ActionType.INVEST_WELFARE),
                projected_cost=10.0
            )
        elif response_model == ForeignProposal:
            return ForeignProposal(
                intent=ForeignIntent(type=ForeignIntentType.COOPERATION, reasoning="Coop"),
                payload=ForeignPayload(source=DecisionSource.MINISTRY_ADVICE, action_type=ActionType.SEND_DIPLOMATIC_MESSAGE),
                target_trust_impact=0.1
            )
        elif response_model == CountryEnvelope:
            return CountryEnvelope(
                turn=1,
                sender_id="TEST",
                global_strategy=GlobalStrategy.COALITION_BUILDER,
                public_statement="We seek peace.",
                public_intent=PublicIntent.PEACEFUL,
                military_payload=MilitaryPayload(source=DecisionSource.MINISTRY_ADVICE, moves=[]),
                military_intent=MilitaryIntent(type=MilitaryIntentType.IDLE, reasoning="Peace"),
                economic_payload=EconomicPayload(
                    source=DecisionSource.MINISTRY_ADVICE, 
                    action_type=ActionType.INVEST_WELFARE,
                    parameters={"amount": 10.0}
                ),
                economic_intent=EconomicIntent(type=EconomicIntentType.GROWTH, reasoning="Welfare"),
                foreign_payload=ForeignPayload(source=DecisionSource.MINISTRY_ADVICE),
                foreign_intent=ForeignIntent(type=ForeignIntentType.COOPERATION, reasoning="Coop")
            )
        return response_model()

def test_simulation_init():
    """Test that engine initializes world and agents."""
    mock_client = SimMockLLM()
    sim = SimulationEngine(map_seed=42, history_seed=99, llm_client=mock_client)
    
    assert len(sim.world.nations) == 10 # Default
    assert len(sim.agents) == 10
    assert sim.world.turn == 0

def test_simulation_step():
    """Test that a step advances the turn and generates logs."""
    mock_client = SimMockLLM()
    
    sim = SimulationEngine(map_seed=42, history_seed=99, llm_client=mock_client)
    
    initial_turn = sim.world.turn
    sim.step()
    
    assert sim.world.turn == initial_turn + 1
    assert len(sim.turn_logs) > 0 
    
    # Check that economy phase ran (logs should contain ECONOMY entries)
    economy_logs = [l for l in sim.turn_logs if "[ECONOMY]" in l]
    assert len(economy_logs) > 0, "Economy phase should run and generate logs"

