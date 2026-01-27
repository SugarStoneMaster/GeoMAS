"""
Foreign Affairs Domain Schemas.

Action types and payloads for diplomatic operations.
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

from geomas.actions.common import DecisionSource


class ForeignActionType(str, Enum):
    """Foreign affairs action types handled by the Foreign Minister."""
    SEND_DIPLOMATIC_MESSAGE = "SEND_DIPLOMATIC_MESSAGE"
    PROPOSE_ALLIANCE = "PROPOSE_ALLIANCE"
    FORMAL_DECLARATION_OF_WAR = "FORMAL_DECLARATION_OF_WAR"
    BREAK_TREATY = "BREAK_TREATY"
    REQUEST_PEACE = "REQUEST_PEACE"


class ForeignPayload(BaseModel):
    """Payload for Foreign Minister actions."""
    source: DecisionSource
    action_type: Optional[ForeignActionType] = None
    target_nation_id: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)

