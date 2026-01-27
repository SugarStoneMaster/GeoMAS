"""
Economy Domain Schemas.

Action types and payloads for economic operations.
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

from geomas.actions.common import DecisionSource


class EconomicActionType(str, Enum):
    """Economic action types handled by the Economy Minister."""
    INVEST_WELFARE = "INVEST_WELFARE"
    TRADE_PROPOSAL = "TRADE_PROPOSAL"
    RAISE_WAR_TAX = "RAISE_WAR_TAX"


class EconomicPayload(BaseModel):
    """Payload for Economy Minister actions."""
    source: DecisionSource
    action_type: Optional[EconomicActionType] = None
    target_nation_id: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)

