"""
Foreign Affairs Package.

Handles diplomatic actions: alliances, treaties, war declarations, peace.
"""

from geomas.actions.foreign.schemas import (
    ForeignActionType,
    ForeignPayload,
    ForeignProposalPayload,
    ForeignResponseAction,  # New
    ProposalResponse,       # New
    DiplomaticMessageType,
    MESSAGE_TRUST_IMPACT,
)
from geomas.actions.foreign.handler import (
    execute_foreign,
    respond_to_proposal,
    clear_expired_proposals,
    MESSAGE_COOLDOWN_TURNS,
)

__all__ = [
    "ForeignActionType",
    "ForeignPayload",
    "ForeignProposalPayload",
    "ForeignResponseAction",
    "ProposalResponse",
    "DiplomaticMessageType",
    "MESSAGE_TRUST_IMPACT",
    "execute_foreign",
    "respond_to_proposal",
    "clear_expired_proposals",
    "MESSAGE_COOLDOWN_TURNS",
]
