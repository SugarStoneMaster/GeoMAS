"""
Foreign Affairs Package.

Handles diplomatic actions: alliances, treaties, war declarations, peace.
"""

from geomas.actions.foreign.schemas import (
    ForeignActionType,
    ForeignPayload,
    DiplomaticMessageType,
    MESSAGE_TRUST_IMPACT,
)
from geomas.actions.foreign.handler import execute_foreign

__all__ = [
    "ForeignActionType",
    "ForeignPayload",
    "DiplomaticMessageType",
    "MESSAGE_TRUST_IMPACT",
    "execute_foreign",
]
