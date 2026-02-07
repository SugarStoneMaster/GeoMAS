"""
Foreign Affairs Domain Schemas.

Action types and payloads for diplomatic operations.
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

from geomas.actions.common import Decision


class ForeignActionType(str, Enum):
    """Foreign affairs action types handled by the Foreign Minister."""
    SEND_DIPLOMATIC_MESSAGE = "SEND_DIPLOMATIC_MESSAGE"
    PROPOSE_ALLIANCE = "PROPOSE_ALLIANCE"
    FORMAL_DECLARATION_OF_WAR = "FORMAL_DECLARATION_OF_WAR"
    BREAK_TREATY = "BREAK_TREATY"
    REQUEST_PEACE = "REQUEST_PEACE"
    ACCEPT_PROPOSAL = "ACCEPT_PROPOSAL"   # Accept pending alliance/peace
    REJECT_PROPOSAL = "REJECT_PROPOSAL"   # Reject pending alliance/peace


class DiplomaticMessageType(str, Enum):
    """Types of diplomatic messages with different trust impacts."""
    PRAISE = "PRAISE"    # Positive message, increases trust
    THREAT = "THREAT"    # Strong warning, decreases trust significantly
    INSULT = "INSULT"    # Mild disrespect, decreases trust slightly


# Trust impact per message type
MESSAGE_TRUST_IMPACT: dict[DiplomaticMessageType, float] = {
    DiplomaticMessageType.PRAISE: +0.1,
    DiplomaticMessageType.THREAT: -0.3,   # Stronger than insult
    DiplomaticMessageType.INSULT: -0.1,
}


class ForeignPayload(BaseModel):
    """Payload for Foreign Minister actions."""
    decision: Decision
    action_type: Optional[ForeignActionType] = None
    target_nation_id: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
