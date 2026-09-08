"""
Foreign Affairs Domain Schemas.

Action types and payloads for diplomatic operations.
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

from geomas.actions.common import Decision, ExecutionOutcome


class ForeignActionType(str, Enum):
    """Foreign affairs action types handled by the Foreign Minister."""
    SEND_DIPLOMATIC_MESSAGE = "SEND_DIPLOMATIC_MESSAGE"
    PROPOSE_ALLIANCE = "PROPOSE_ALLIANCE"
    FORMAL_DECLARATION_OF_WAR = "FORMAL_DECLARATION_OF_WAR"
    BREAK_TREATY = "BREAK_TREATY"
    REQUEST_PEACE = "REQUEST_PEACE"
    IDLE = "IDLE"                         # No diplomatic action this turn


class ForeignResponseAction(str, Enum):
    """Actions for responding to pending proposals."""
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"


class DiplomaticMessageType(str, Enum):
    """Types of diplomatic messages with different trust impacts."""
    PRAISE = "PRAISE"    # Positive message, increases trust
    THREAT = "THREAT"    # Strong warning, decreases trust significantly
    INSULT = "INSULT"    # Mild disrespect, decreases trust slightly
    NUCLEAR_THREAT = "NUCLEAR_THREAT" # Diplomatic communication referencing nuclear capabilities


# Trust impact per message type
MESSAGE_TRUST_IMPACT: dict[DiplomaticMessageType, float] = {
    DiplomaticMessageType.PRAISE: +10.0,
    DiplomaticMessageType.THREAT: -30.0,
    DiplomaticMessageType.INSULT: -10.0,
    DiplomaticMessageType.NUCLEAR_THREAT: -50.0,
}


class ProposalResponse(BaseModel):
    """Response to a specific pending proposal."""
    proposal_id: str = Field(..., description="Unique ID of the proposal being responded to.")
    response: ForeignResponseAction = Field(..., description="ACCEPT or REJECT.")
    message: Optional[str] = Field(None, description="Explanation for the response.")


class TreatyTier(str, Enum):
    """Levels of commitment for an alliance."""
    NON_AGGRESSION = "NON_AGGRESSION"
    MUTUAL_DEFENSE = "MUTUAL_DEFENSE"


class ForeignProposalPayload(BaseModel):
    """
    Payload for Foreign Minister proposals (NO DECISION FIELD).
    This is what the Minister generates.
    """
    # 1. Responses to Incoming Proposals (Inbox)
    proposal_responses: List[ProposalResponse] = Field(
        default_factory=list,
        description="List of responses to pending proposals. Can be empty."
    )

    # 2. Active Statistic Measure (Agenda)
    action_type: Optional[ForeignActionType] = None
    target_nation_id: Optional[str] = None
    message: Optional[str] = Field(None, description="Diplomatic message to the target nation.")
    
    # Explicit fields for strong typing
    diplomatic_message_type: Optional[DiplomaticMessageType] = Field(
        None, 
        description="Required for SEND_DIPLOMATIC_MESSAGE. Enum: PRAISE, THREAT, INSULT, NUCLEAR_THREAT."
    )
    treaty_tier: Optional[TreatyTier] = Field(
        None,
        description="Required for PROPOSE_ALLIANCE. Enum: NON_AGGRESSION, MUTUAL_DEFENSE."
    )


class ForeignPayload(ForeignProposalPayload):
    """
    Payload for execution (INCLUDES DECISION FIELD).
    This is what the President approves/vetoes and puts in the envelope.
    """
    decision: Decision = Field(
        default=Decision.PENDING,
        description="FOR PRESIDENT ONLY. Ministers MUST leave as PENDING."
    )

    # Internal execution field (not visible to LLM)
    execution_outcome: ExecutionOutcome = Field(
        default_factory=ExecutionOutcome,
        exclude=True,
        description="INTERNAL USE ONLY. Tracks success/failure of this specific action."
    )
