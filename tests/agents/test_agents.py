import pytest
import sys
import os
from typing import Type

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from geomas.world.map_engine import generate_world
from geomas.agents.llm_client import LLMClient
from geomas.agents.nation_agent import NationAgent
from geomas.agents.ministers import DefenseMinister
from geomas.schemas.protocol import ( 
    DefenseProposal, MilitaryIntent, MilitaryIntentType,
    CountryEnvelope, GlobalStrategy, PublicIntent, EconomicIntent, EconomicPayload, 
    ForeignIntent, ForeignPayload, EconomicIntentType, ForeignIntentType,
    EconomicProposal, ForeignProposal
)
from geomas.schemas.actions import MilitaryPayload, ActionType, DecisionSource # Updated import

# --- MOCK INFRASTRUCTURE ---

class MockLLMClient(LLMClient):
    """Mocks the LLM to return deterministic Pydantic objects."""
    
    def __init__(self):
        pass # Skip super init

    def query_agent(self, system_prompt: str, user_prompt: str, response_model: Type, max_retries: int = 3):
        # Return a valid dummy object based on the requested model
        if response_model == DefenseProposal:
            return DefenseProposal(
                intent=MilitaryIntent(type=MilitaryIntentType.DEFENSE, reasoning="Mock Defense"),
                payload=MilitaryPayload(source=DecisionSource.MINISTRY_ADVICE, moves=[]),
                urgency=5
            )
        elif response_model == EconomicProposal:
            return EconomicProposal(
                intent=EconomicIntent(type=EconomicIntentType.GROWTH, reasoning="Mock Eco"),
                payload=EconomicPayload(source=DecisionSource.MINISTRY_ADVICE),
                projected_cost=100.0
            )
        elif response_model == ForeignProposal:
            return ForeignProposal(
                intent=ForeignIntent(type=ForeignIntentType.COOPERATION, reasoning="Mock Foreign"),
                payload=ForeignPayload(source=DecisionSource.MINISTRY_ADVICE),
                target_trust_impact=0.1
            )
        elif response_model == CountryEnvelope:
            return CountryEnvelope(
                turn=1,
                sender_id="TEST",
                global_strategy=GlobalStrategy.COALITION_BUILDER,
                public_statement="Mock Statement",
                public_intent=PublicIntent.PEACEFUL,
                military_payload=MilitaryPayload(source=DecisionSource.MINISTRY_ADVICE, moves=[]),
                military_intent=MilitaryIntent(type=MilitaryIntentType.IDLE, reasoning="Mock"),
                economic_payload=EconomicPayload(source=DecisionSource.MINISTRY_ADVICE),
                economic_intent=EconomicIntent(type=EconomicIntentType.IDLE, reasoning="Mock"),
                foreign_payload=ForeignPayload(source=DecisionSource.MINISTRY_ADVICE),
                foreign_intent=ForeignIntent(type=ForeignIntentType.IDLE, reasoning="Mock")
            )
        
        # Fallback for unexpected models
        try:
            return response_model()
        except:
            raise ValueError(f"MockLLMClient cannot handle {response_model}")

# --- TESTS ---

def test_minister_prompt_construction():
    """Test that ministers build prompts with correct context."""
    world = generate_world(seed=42, n_cells=100, n_nations=2)
    nation_id = list(world.nations.keys())[0]
    
    client = MockLLMClient()
    minister = DefenseMinister(nation_id, world, client)
    
    proposal = minister.propose(GlobalStrategy.TOTAL_EXPANSIONISM)
    
    assert isinstance(proposal, DefenseProposal)
    assert proposal.intent.reasoning == "Mock Defense"

def test_nation_agent_flow():
    """Test the full perceive-propose-decide loop."""
    world = generate_world(seed=42, n_cells=100, n_nations=2)
    nation_id = list(world.nations.keys())[0]
    client = MockLLMClient()
    
    agent = NationAgent(nation_id, world, client)
    
    # Run the act loop
    envelope = agent.act(turn=1)
    
    assert isinstance(envelope, CountryEnvelope)
    assert envelope.public_statement == "Mock Statement"
    
    # Check memory update
    assert len(agent.memory) == 1
    assert "Mock Statement" in agent.memory[0]

def test_context_injection():
    """Verify that context (Trust, Resources) is actually retrieved."""
    world = generate_world(seed=42, n_cells=100, n_nations=2)
    nation_id = list(world.nations.keys())[0]
    client = MockLLMClient()
    minister = DefenseMinister(nation_id, world, client)
    
    trust_summary = minister._get_trust_summary()
    assert "I Trust Them" in trust_summary
    assert "They Trust Me" in trust_summary
    
    res_summary = minister._get_resource_summary()
    assert "Food:" in res_summary
