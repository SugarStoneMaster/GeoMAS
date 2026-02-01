"""
Mock LLM Client for UI Testing.

Returns deterministic, valid responses for the Streamlit dashboard.
"""

from geomas.agents.llm_client import LLMClient
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


class UIMockLLM(LLMClient):
    """Mock LLM that returns valid dummy objects for UI testing."""
    
    def __init__(self):
        pass  # Skip parent initialization
    
    def query_agent(self, system_prompt, user_prompt, response_model, max_retries=3):
        """Returns deterministic responses based on the requested model type."""
        
        if response_model == DefenseProposal:
            return DefenseProposal(
                intent=DefenseIntent(type=DefenseIntentType.IDLE, reasoning="Peace is good"),
                payload=DefensePayload(source=DecisionSource.MINISTRY_ADVICE, moves=[]),
                urgency=1
            )
        
        elif response_model == EconomicProposal:
            return EconomicProposal(
                intent=EconomicIntent(type=EconomicIntentType.GROWTH, reasoning="We need to grow"),
                payload=EconomicPayload(
                    source=DecisionSource.MINISTRY_ADVICE, 
                    action_type=EconomicActionType.INVEST_WELFARE
                ),
                projected_cost=50.0
            )
        
        elif response_model == ForeignProposal:
            return ForeignProposal(
                intent=ForeignIntent(type=ForeignIntentType.COOPERATION, reasoning="Friends are good"),
                payload=ForeignPayload(
                    source=DecisionSource.MINISTRY_ADVICE, 
                    action_type=ForeignActionType.SEND_DIPLOMATIC_MESSAGE
                ),
                target_trust_impact=0.1
            )
        
        elif response_model == CountryEnvelope:
            return CountryEnvelope(
                turn=1,
                sender_id="TEST",
                global_strategy=GlobalStrategy.COALITION_BUILDER,
                public_statement="[DEFENSE] Maintaining peace. [ECONOMY] Investing in welfare. [FOREIGN] Open to cooperation.",
                # Defense
                defense_payload=DefensePayload(source=DecisionSource.MINISTRY_ADVICE, moves=[]),
                defense_public_intent=DefenseIntentType.DEFENSE,
                defense_private_intent=DefenseIntentType.IDLE,
                defense_private_reasoning="No threats detected, maintaining defensive posture.",
                # Economic
                economic_payload=EconomicPayload(
                    source=DecisionSource.MINISTRY_ADVICE,
                    action_type=EconomicActionType.INVEST_WELFARE,
                    parameters={"amount": 50.0}
                ),
                economic_public_intent=EconomicIntentType.GROWTH,
                economic_private_intent=EconomicIntentType.GROWTH,
                economic_private_reasoning="Boosting public satisfaction through welfare.",
                # Foreign
                foreign_payload=ForeignPayload(source=DecisionSource.MINISTRY_ADVICE),
                foreign_public_intent=ForeignIntentType.COOPERATION,
                foreign_private_intent=ForeignIntentType.COOPERATION,
                foreign_private_reasoning="Maintaining status quo with neighbors."
            )
        
        # Fallback
        return response_model()
