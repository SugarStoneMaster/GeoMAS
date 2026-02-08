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
    DefenseProposal, EconomicProposal, ForeignProposal,
    PresidentialDecree, Decision, DefenseDecree, EconomicDecree, ForeignDecree
)
from geomas.actions.defense import DefensePayload, Decision
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
                intent=DefenseIntent(
                    public_intent=DefenseIntentType.IDLE,
                    private_intent=DefenseIntentType.IDLE,
                    reasoning="Peace is good"
                ),
                payload=DefensePayload(decision=Decision.APPROVE, moves=[])
            )
        
        elif response_model == EconomicProposal:
            return EconomicProposal(
                intent=EconomicIntent(
                    public_intent=EconomicIntentType.GROWTH,
                    private_intent=EconomicIntentType.GROWTH,
                    reasoning="We need to grow"
                ),
                payload=EconomicPayload(
                    decision=Decision.APPROVE, 
                    action_type=EconomicActionType.INVEST_WELFARE
                )
            )
        
        elif response_model == ForeignProposal:
            return ForeignProposal(
                intent=ForeignIntent(
                    public_intent=ForeignIntentType.COOPERATION,
                    private_intent=ForeignIntentType.COOPERATION,
                    reasoning="Friends are good"
                ),
                payload=ForeignPayload(
                    decision=Decision.APPROVE, 
                    action_type=ForeignActionType.SEND_DIPLOMATIC_MESSAGE
                )
            )
        
        elif response_model == PresidentialDecree:
            return PresidentialDecree(
                defense=DefenseDecree(action=Decision.APPROVE, reasoning="Peace"),
                economy=EconomicDecree(action=Decision.APPROVE, reasoning="Growth"),
                foreign=ForeignDecree(action=Decision.APPROVE, reasoning="Coop"),
                public_statement="Peace and Prosperity."
            )
        
        elif response_model == CountryEnvelope:
            return CountryEnvelope(
                turn=1,
                sender_id="TEST",
                global_strategy=GlobalStrategy.COALITION_BUILDER,
                public_statement="[DEFENSE] Maintaining peace. [ECONOMY] Investing in welfare. [FOREIGN] Open to cooperation.",
                # Defense
                defense_payload=DefensePayload(decision=Decision.APPROVE, moves=[]),
                defense_public_intent=DefenseIntentType.DEFENSE,
                defense_private_intent=DefenseIntentType.IDLE,
                defense_private_reasoning="No threats detected, maintaining defensive posture.",
                # Economic
                economic_payload=EconomicPayload(
                    decision=Decision.APPROVE,
                    action_type=EconomicActionType.INVEST_WELFARE,
                    amount=50.0
                ),
                economic_public_intent=EconomicIntentType.GROWTH,
                economic_private_intent=EconomicIntentType.GROWTH,
                economic_private_reasoning="Boosting public satisfaction through welfare.",
                # Foreign
                foreign_payload=ForeignPayload(decision=Decision.APPROVE),
                foreign_public_intent=ForeignIntentType.COOPERATION,
                foreign_private_intent=ForeignIntentType.COOPERATION,
                foreign_private_reasoning="Maintaining status quo with neighbors."
            )
        
        # Fallback
        return response_model()
