"""
Economy Domain Schemas.

Action types and payloads for economic operations.
"""

from enum import Enum
from pydantic import BaseModel, Field, model_validator
from typing import Dict, Any, Optional

from geomas.actions.common import Decision


class EconomicActionType(str, Enum):
    """Economic action types handled by the Economy Minister."""
    INVEST_WELFARE = "INVEST_WELFARE"
    TRADE_PROPOSAL = "TRADE_PROPOSAL"
    RAISE_WAR_TAX = "RAISE_WAR_TAX"
    IDLE = "IDLE"


class EconomicProposalPayload(BaseModel):
    """
    Payload for Economy Minister proposals (NO DECISION FIELD).
    This is what the Minister generates.
    """
    action_type: Optional[EconomicActionType] = None
    target_nation_id: Optional[str] = None
    
    # Explicit fields for strong typing
    amount: Optional[float] = Field(None, description="Amount for INVEST_WELFARE")
    message: Optional[str] = Field(None, description="Public message to citizens or diplomatic message to trade partner")
    give_type: Optional[str] = Field(None, description="Resource type to GIVE (food, energy, materials, budget)")
    give_amount: Optional[float] = Field(None, description="Amount to GIVE (must be positive)")
    want_type: Optional[str] = Field(None, description="Resource type DESIRED (food, energy, materials, budget)")

    @model_validator(mode='after')
    def validate_trade_proposal(self) -> 'EconomicProposalPayload':
        if self.action_type == EconomicActionType.TRADE_PROPOSAL:
            if not self.target_nation_id:
                raise ValueError("TRADE_PROPOSAL requires 'target_nation_id' (Who are you trading with?)")
            
            if not self.give_type:
                raise ValueError("TRADE_PROPOSAL requires 'give_type' (What resource act you GIVING? e.g. 'food', 'budget', 'energy', 'materials')")
            
            if self.give_amount is None:
                raise ValueError("TRADE_PROPOSAL requires 'give_amount' (How much are you giving? Must be a number > 0)")
            
            if self.give_amount <= 0:
                raise ValueError("'give_amount' must be positive")
            
            if not self.want_type:
                raise ValueError("TRADE_PROPOSAL requires 'want_type' (What resource do you WANT in return?)")
                
        return self


class EconomicPayload(EconomicProposalPayload):
    """
    Payload for execution (INCLUDES DECISION FIELD).
    This is what the President approves/vetoes and puts in the envelope.
    """
    decision: Decision = Field(
        default=Decision.PENDING,
        description="FOR PRESIDENT ONLY. Ministers MUST leave as PENDING."
    )

