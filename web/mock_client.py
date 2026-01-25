"""
Mock LLM Client for UI Testing.

Returns deterministic, valid responses for the Streamlit dashboard.
"""

from geomas.agents.llm_client import LLMClient
from geomas.agents.schemas import (
    CountryEnvelope, GlobalStrategy, PublicIntent,
    MilitaryPayload, MilitaryIntent, MilitaryIntentType,
    EconomicPayload, EconomicIntent, EconomicIntentType,
    ForeignPayload, ForeignIntent, ForeignIntentType,
    DefenseProposal, EconomicProposal, ForeignProposal
)
from geomas.actions.schemas import ActionType, DecisionSource


class UIMockLLM(LLMClient):
    """Mock LLM that returns valid dummy objects for UI testing."""
    
    def __init__(self):
        pass  # Skip parent initialization
    
    def query_agent(self, system_prompt, user_prompt, response_model, max_retries=3):
        """Returns deterministic responses based on the requested model type."""
        
        if response_model == DefenseProposal:
            return DefenseProposal(
                intent=MilitaryIntent(type=MilitaryIntentType.IDLE, reasoning="Peace is good"),
                payload=MilitaryPayload(source=DecisionSource.MINISTRY_ADVICE, moves=[]),
                urgency=1
            )
        
        elif response_model == EconomicProposal:
            return EconomicProposal(
                intent=EconomicIntent(type=EconomicIntentType.GROWTH, reasoning="We need to grow"),
                payload=EconomicPayload(
                    source=DecisionSource.MINISTRY_ADVICE, 
                    action_type=ActionType.INVEST_WELFARE
                ),
                projected_cost=50.0
            )
        
        elif response_model == ForeignProposal:
            return ForeignProposal(
                intent=ForeignIntent(type=ForeignIntentType.COOPERATION, reasoning="Friends are good"),
                payload=ForeignPayload(
                    source=DecisionSource.MINISTRY_ADVICE, 
                    action_type=ActionType.SEND_DIPLOMATIC_MESSAGE
                ),
                target_trust_impact=0.1
            )
        
        elif response_model == CountryEnvelope:
            return CountryEnvelope(
                turn=1,
                sender_id="TEST",
                global_strategy=GlobalStrategy.COALITION_BUILDER,
                public_statement="We are investing in our people and seeking peace.",
                public_intent=PublicIntent.PEACEFUL,
                military_payload=MilitaryPayload(source=DecisionSource.MINISTRY_ADVICE, moves=[]),
                military_intent=MilitaryIntent(type=MilitaryIntentType.IDLE, reasoning="No threats detected."),
                economic_payload=EconomicPayload(
                    source=DecisionSource.MINISTRY_ADVICE,
                    action_type=ActionType.INVEST_WELFARE,
                    parameters={"amount": 50.0}
                ),
                economic_intent=EconomicIntent(type=EconomicIntentType.GROWTH, reasoning="Boosting satisfaction."),
                foreign_payload=ForeignPayload(source=DecisionSource.MINISTRY_ADVICE),
                foreign_intent=ForeignIntent(type=ForeignIntentType.COOPERATION, reasoning="Maintaining status quo.")
            )
        
        # Fallback
        return response_model()
