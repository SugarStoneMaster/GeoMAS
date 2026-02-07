"""
Tests for Agent System.

Validates LLM agent interactions and NationAgent flow.
"""

import pytest
import sys
import os
from typing import Type

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from geomas.world import generate_world
from geomas.agents.llm_client import LLMClient
from geomas.agents.nation_agent import NationAgent
from geomas.agents.ministers import DefenseMinister
from geomas.agents.schemas import ( 
    DefenseProposal, DefenseIntent, DefenseIntentType,
    CountryEnvelope, GlobalStrategy, EconomicIntent,
    ForeignIntent, EconomicIntentType, ForeignIntentType,
    EconomicProposal, ForeignProposal,
    PresidentialDecree, DecreeAction, DefenseDecree, EconomicDecree, ForeignDecree
)
from geomas.actions.defense import DefensePayload, DecisionSource
from geomas.actions.economy import EconomicPayload
from geomas.actions.foreign import ForeignPayload


# --- MOCK INFRASTRUCTURE ---

class MockLLMClient(LLMClient):
    """Mocks the LLM to return deterministic Pydantic objects."""
    
    def __init__(self):
        pass # Skip super init

    def query_agent(self, system_prompt: str, user_prompt: str, response_model: Type, max_retries: int = 3):
        # Return a valid dummy object based on the requested model
        if response_model == DefenseProposal:
            return DefenseProposal(
                intent=DefenseIntent(type=DefenseIntentType.DEFENSE, reasoning="Mock Defense"),
                payload=DefensePayload(source=DecisionSource.MINISTRY_ADVICE, moves=[]),
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
        elif response_model == PresidentialDecree:
            return PresidentialDecree(
                defense=DefenseDecree(action=DecreeAction.APPROVE, reasoning="Approved"),
                economy=EconomicDecree(action=DecreeAction.APPROVE, reasoning="Approved"),
                foreign=ForeignDecree(action=DecreeAction.APPROVE, reasoning="Approved"),
                public_statement="We stand united.",
                defense_public_intent=DefenseIntentType.DEFENSE,
                defense_private_intent=DefenseIntentType.DEFENSE,
                economic_public_intent=EconomicIntentType.GROWTH,
                economic_private_intent=EconomicIntentType.GROWTH,
                foreign_public_intent=ForeignIntentType.COOPERATION,
                foreign_private_intent=ForeignIntentType.COOPERATION,
                defense_private_reasoning="R",
                economic_private_reasoning="R",
                foreign_private_reasoning="R"
            )
        elif response_model == CountryEnvelope:
            # Still kept for legacy tests if any call directly
            return CountryEnvelope(
                turn=1,
                sender_id="TEST",
                global_strategy=GlobalStrategy.COALITION_BUILDER,
                public_statement="[DEFENSE] Peaceful. [ECONOMY] Growing. [FOREIGN] Cooperative.",
                defense_payload=DefensePayload(source=DecisionSource.MINISTRY_ADVICE, moves=[]),
                defense_public_intent=DefenseIntentType.DEFENSE,
                defense_private_intent=DefenseIntentType.IDLE,
                defense_private_reasoning="Mock defense reasoning",
                economic_payload=EconomicPayload(source=DecisionSource.MINISTRY_ADVICE),
                economic_public_intent=EconomicIntentType.GROWTH,
                economic_private_intent=EconomicIntentType.IDLE,
                economic_private_reasoning="Mock economic reasoning",
                foreign_payload=ForeignPayload(source=DecisionSource.MINISTRY_ADVICE),
                foreign_public_intent=ForeignIntentType.COOPERATION,
                foreign_private_intent=ForeignIntentType.IDLE,
                foreign_private_reasoning="Mock foreign reasoning"
            )
        
        # Fallback for unexpected models
        try:
            return response_model()
        except:
            raise ValueError(f"MockLLMClient cannot handle {response_model}")


# --- TESTS ---

def test_mock_llm_client_defense():
    """Mock returns a valid DefenseProposal."""
    mock = MockLLMClient()
    result = mock.query_agent("", "", DefenseProposal)
    assert isinstance(result, DefenseProposal)
    assert result.intent.type == DefenseIntentType.DEFENSE


def test_defense_minister_proposal():
    """DefenseMinister generates a proposal using the mock LLM."""
    world = generate_world(seed=42, n_cells=100, n_nations=2)
    nation_id = list(world.nations.keys())[0]
    client = MockLLMClient()
    
    minister = DefenseMinister(nation_id, world, client)
    proposal = minister.propose(strategy=GlobalStrategy.COALITION_BUILDER)
    
    assert isinstance(proposal, DefenseProposal)
    assert proposal.intent is not None
    assert proposal.urgency >= 1 and proposal.urgency <= 10


def test_nation_agent_flow():
    """Test the full perceive-propose-decide loop."""
    world = generate_world(seed=42, n_cells=100, n_nations=2)
    nation_id = list(world.nations.keys())[0]
    client = MockLLMClient()
    
    agent = NationAgent(nation_id, world, client)
    
    # Run the act loop
    envelope = agent.act(turn=1)
    
    # Check output format
    assert isinstance(envelope, CountryEnvelope)
    assert envelope.sender_id == nation_id
    assert envelope.turn == 1
    assert envelope.global_strategy in GlobalStrategy
    assert envelope.public_statement != ""


def test_envelope_payloads_valid():
    """The produced envelope's payloads should be valid."""
    world = generate_world(seed=42, n_cells=100, n_nations=2)
    nation_id = list(world.nations.keys())[0]
    client = MockLLMClient()
    
    agent = NationAgent(nation_id, world, client)
    envelope = agent.act(turn=1)
    
    # Check that payloads are present
    assert envelope.defense_payload is not None
    assert envelope.economic_payload is not None
    assert envelope.foreign_payload is not None
