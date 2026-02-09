"""
Economy Domain Schemas.

Action types and payloads for economic operations.
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

from geomas.actions.common import Decision


class EconomicActionType(str, Enum):
    """Economic action types handled by the Economy Minister."""
    INVEST_WELFARE = "INVEST_WELFARE"
    TRADE_PROPOSAL = "TRADE_PROPOSAL"
    RAISE_WAR_TAX = "RAISE_WAR_TAX"


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
    trade_offer_give_type: Optional[str] = Field(None, description="Resource type to GIVE")
    trade_offer_give_amount: Optional[float] = Field(None, description="Amount to GIVE")
    trade_offer_want_type: Optional[str] = Field(None, description="Resource type DESIRED (food, energy, materials, budget)")


class EconomicPayload(EconomicProposalPayload):
    """
    Payload for execution (INCLUDES DECISION FIELD).
    This is what the President approves/vetoes and puts in the envelope.
    """
    decision: Decision = Field(
        default=Decision.PENDING,
        description="FOR PRESIDENT ONLY. Ministers MUST leave as PENDING."
    )

