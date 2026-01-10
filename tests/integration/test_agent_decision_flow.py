import pytest
import sys
import os
from typing import Type

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from geomas.world.map_engine import generate_world
from geomas.agents.llm_client import LLMClient
from geomas.agents.nation_agent import NationAgent
from geomas.core.rules_engine import ActionValidator
from geomas.schemas.protocol import ( 
    CountryEnvelope, GlobalStrategy, PublicIntent, 
    MilitaryIntent, MilitaryIntentType,
    EconomicIntent, EconomicIntentType,
    ForeignIntent, ForeignIntentType,
    DefenseProposal, EconomicProposal, ForeignProposal
)
from geomas.schemas.actions import ( # Updated import
    ActionType, MilitaryPayload, EconomicPayload, ForeignPayload, DecisionSource
)

# --- MOCK CLIENT (Simplified for Integration) ---
class IntegrationMockLLM(LLMClient):
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
                projected_cost=100.0
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
                # Valid Economic Action
                economic_payload=EconomicPayload(
                    source=DecisionSource.MINISTRY_ADVICE, 
                    action_type=ActionType.INVEST_WELFARE,
                    parameters={"amount": 50}
                ),
                economic_intent=EconomicIntent(type=EconomicIntentType.GROWTH, reasoning="Welfare"),
                foreign_payload=ForeignPayload(source=DecisionSource.MINISTRY_ADVICE),
                foreign_intent=ForeignIntent(type=ForeignIntentType.COOPERATION, reasoning="Coop")
            )
        return response_model()

def test_agent_to_rules_pipeline():
    """
    Ensures that the Agent's output (Envelope) contains data 
    that the Rules Engine can actually validate.
    """
    # 1. Setup World
    world = generate_world(seed=42, n_cells=100, n_nations=2)
    nation_id = list(world.nations.keys())[0]
    
    # 2. Setup Agent
    client = IntegrationMockLLM()
    agent = NationAgent(nation_id, world, client)
    
    # 3. Agent Acts
    envelope = agent.act(turn=1)
    
    # 4. Validate Action
    validator = ActionValidator(world)
    
    # Extract Economic Action from Envelope
    action_type = envelope.economic_payload.action_type
    params = envelope.economic_payload.parameters
    
    assert action_type == ActionType.INVEST_WELFARE
    
    # Check if validator has a method for this (it doesn't yet, but we check budget)
    # In Phase 3 we will map ActionType -> Validator Method
    # For now, let's manually check budget using the validator's helper
    
    cost = params.get("amount", 0)
    allowed, reason = validator.can_afford_budget(nation_id, cost)
    
    assert allowed, f"Agent proposed unaffordable action: {reason}"
    
    # 5. Check Consistency
    assert envelope.global_strategy == agent.strategy
