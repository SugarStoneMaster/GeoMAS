"""
Tests for SimulationEngine.

Validates simulation step execution and agent interactions.
"""

import pytest
import sys
import os
from typing import Type

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from geomas.simulation import SimulationEngine
from geomas.agents.llm_client import LLMClient
from geomas.agents.schemas import (
    CountryEnvelope, GlobalStrategy, 
    DefenseIntent, DefenseIntentType,
    EconomicIntent, EconomicIntentType,
    ForeignIntent, ForeignIntentType,
    DefenseProposal, EconomicProposal, ForeignProposal
)
from geomas.actions.defense import DefensePayload, Decision
from geomas.actions.economy import EconomicPayload, EconomicActionType
from geomas.actions.foreign import ForeignPayload, ForeignActionType


# --- MOCK CLIENT ---
class SimMockLLM(LLMClient):
    def __init__(self): pass
    
    def query_agent(self, system_prompt, user_prompt, response_model, max_retries=3):
        # Return valid dummy objects
        if response_model == DefenseProposal:
            return DefenseProposal(
                intent=DefenseIntent(
                    public_intent=DefenseIntentType.IDLE, 
                    private_intent=DefenseIntentType.IDLE,
                    reasoning="Peace"
                ),
                payload=DefensePayload(decision=Decision.APPROVE, moves=[])
            )
        elif response_model == EconomicProposal:
            return EconomicProposal(
                intent=EconomicIntent(
                    public_intent=EconomicIntentType.GROWTH,
                    private_intent=EconomicIntentType.GROWTH,
                    reasoning="Grow"
                ),
                payload=EconomicPayload(decision=Decision.APPROVE, action_type=EconomicActionType.INVEST_WELFARE)
            )
        elif response_model == ForeignProposal:
            return ForeignProposal(
                intent=ForeignIntent(
                    public_intent=ForeignIntentType.COOPERATION,
                    private_intent=ForeignIntentType.COOPERATION,
                    reasoning="Coop"
                ),
                payload=ForeignPayload(decision=Decision.APPROVE, action_type=ForeignActionType.SEND_DIPLOMATIC_MESSAGE)
            )
        elif response_model == CountryEnvelope:
            return CountryEnvelope(
                turn=1,
                sender_id="TEST",
                global_strategy=GlobalStrategy.COALITION_BUILDER,
                public_statement="[DEFENSE] Peaceful. [ECONOMY] Growing. [FOREIGN] Cooperative.",
                # Defense
                defense_payload=DefensePayload(decision=Decision.APPROVE, moves=[]),
                defense_public_intent=DefenseIntentType.DEFENSE,
                defense_private_intent=DefenseIntentType.IDLE,
                defense_private_reasoning="Peace is best.",
                # Economic
                economic_payload=EconomicPayload(
                    decision=Decision.APPROVE, 
                    action_type=EconomicActionType.INVEST_WELFARE,
                    amount=10.0
                ),
                economic_public_intent=EconomicIntentType.GROWTH,
                economic_private_intent=EconomicIntentType.GROWTH,
                economic_private_reasoning="Welfare investment.",
                # Foreign
                foreign_payload=ForeignPayload(decision=Decision.APPROVE),
                foreign_public_intent=ForeignIntentType.COOPERATION,
                foreign_private_intent=ForeignIntentType.COOPERATION,
                foreign_private_reasoning="Maintain good relations."
            )
        return response_model()


def test_simulation_init():
    """Test that engine initializes world and agents."""
    mock_client = SimMockLLM()
    sim = SimulationEngine(map_seed=42, history_seed=99, llm_client=mock_client)
    
    assert len(sim.world.nations) == 10 # Default
    assert len(sim.agents) == 10
    assert sim.world.turn == 1


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
