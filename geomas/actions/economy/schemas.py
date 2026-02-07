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


class EconomicPayload(BaseModel):
    """Payload for Economy Minister actions."""
    decision: Decision = Field(
        default=Decision.PENDING,
        description="FOR PRESIDENT ONLY. Ministers MUST leave as PENDING."
    )
    action_type: Optional[EconomicActionType] = None
    target_nation_id: Optional[str] = None
    
    # Explicit fields for strong typing
    amount: Optional[float] = Field(None, description="Amount for INVEST_WELFARE")
    trade_offer_give: Optional[Dict[str, float]] = Field(None, description="Resources to GIVE in TRADE_PROPOSAL")
    trade_offer_receive: Optional[Dict[str, float]] = Field(None, description="Resources to RECEIVE in TRADE_PROPOSAL")

