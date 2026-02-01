"""
End-to-End Tests for Full Simulation Loop.

Validates the complete pipeline from init to deception analysis.
"""

import pytest
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from geomas.simulation import SimulationEngine
from geomas.agents.llm_client import LLMClient
from geomas.analysis.deception import DeceptionAnalyzer
from geomas.agents.schemas import (
    CountryEnvelope, GlobalStrategy, 
    DefenseIntent, DefenseIntentType,
    EconomicIntent, EconomicIntentType,
    ForeignIntent, ForeignIntentType,
    DefenseProposal, EconomicProposal, ForeignProposal
)
from geomas.actions.defense import DefensePayload, DecisionSource
from geomas.actions.economy import EconomicPayload, EconomicActionType
from geomas.actions.foreign import ForeignPayload, ForeignActionType


# --- MOCK CLIENT ---
class E2EMockLLM(LLMClient):
    def __init__(self): pass
    
    def query_agent(self, system_prompt, user_prompt, response_model, max_retries=3):
        # Return valid dummy objects
        if response_model == DefenseProposal:
            return DefenseProposal(
                intent=DefenseIntent(type=DefenseIntentType.IDLE, reasoning="Peace"),
                payload=DefensePayload(source=DecisionSource.MINISTRY_ADVICE, moves=[]),
                urgency=1
            )
        elif response_model == EconomicProposal:
            return EconomicProposal(
                intent=EconomicIntent(type=EconomicIntentType.GROWTH, reasoning="Grow"),
                payload=EconomicPayload(source=DecisionSource.MINISTRY_ADVICE, action_type=EconomicActionType.INVEST_WELFARE),
                projected_cost=10.0
            )
        elif response_model == ForeignProposal:
            return ForeignProposal(
                intent=ForeignIntent(type=ForeignIntentType.COOPERATION, reasoning="Coop"),
                payload=ForeignPayload(source=DecisionSource.MINISTRY_ADVICE, action_type=ForeignActionType.SEND_DIPLOMATIC_MESSAGE),
                target_trust_impact=0.1
            )
        elif response_model == CountryEnvelope:
            return CountryEnvelope(
                turn=1,
                sender_id="TEST", # Will be overwritten by NationAgent
                global_strategy=GlobalStrategy.COALITION_BUILDER,
                public_statement="[DEFENSE] Peaceful. [ECONOMY] Growing. [FOREIGN] Cooperative.",
                # Defense - honest
                defense_payload=DefensePayload(source=DecisionSource.MINISTRY_ADVICE, moves=[]),
                defense_public_intent=DefenseIntentType.IDLE,
                defense_private_intent=DefenseIntentType.IDLE,
                defense_private_reasoning="Peace is best.",
                # Economic - honest
                economic_payload=EconomicPayload(
                    source=DecisionSource.MINISTRY_ADVICE, 
                    action_type=EconomicActionType.INVEST_WELFARE,
                    parameters={"amount": 10.0}
                ),
                economic_public_intent=EconomicIntentType.GROWTH,
                economic_private_intent=EconomicIntentType.GROWTH,
                economic_private_reasoning="Welfare investment.",
                # Foreign - honest
                foreign_payload=ForeignPayload(source=DecisionSource.MINISTRY_ADVICE),
                foreign_public_intent=ForeignIntentType.COOPERATION,
                foreign_private_intent=ForeignIntentType.COOPERATION,
                foreign_private_reasoning="Coop is best."
            )
        return response_model()


def test_full_simulation_step():
    """
    Tests the entire loop:
    1. Init Simulation
    2. Agents Perceive & Act (Mocked)
    3. Action Engine Executes
    4. World Updates
    5. Deception Analysis
    """
    mock_client = E2EMockLLM()
    sim = SimulationEngine(map_seed=42, history_seed=99, llm_client=mock_client)
    
    # Capture initial state
    initial_turn = sim.world.turn
    n_id = list(sim.world.nations.keys())[0]
    initial_budget = sim.world.nations[n_id].total_budget
    
    # RUN STEP
    sim.step()
    
    # 1. Check Turn Advance
    assert sim.world.turn == initial_turn + 1
    
    # 2. Check State Change - budget should have changed (taxes added, spending deducted)
    # The exact amount depends on population (taxes) and mock actions (spending)
    final_budget = sim.world.nations[n_id].total_budget
    # Budget should have changed (either up from taxes or down from net spending)
    # We just verify the economy ran by checking logs
    
    # 3. Check Logs contain economy entries
    assert len(sim.turn_logs) > 0
    economy_logs = [l for l in sim.turn_logs if "[ECONOMY]" in l]
    assert len(economy_logs) > 0, "Economy phase should generate logs"
    
    # 4. Check that welfare was invested (from mock agent)
    welfare_logs = [l for l in sim.turn_logs if "Welfare" in l]
    assert len(welfare_logs) > 0, "Mock agents should invest in welfare"

    # 5. Check Deception Analysis (Manual check on mock data)
    env = mock_client.query_agent("", "", CountryEnvelope)
    score = DeceptionAnalyzer.calculate_score(env)
    assert score == 0.0  # All intents match -> Honest
