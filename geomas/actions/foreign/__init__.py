"""
Foreign Affairs Package.

Handles diplomatic actions: alliances, treaties, war declarations, peace.
"""

from geomas.actions.foreign.schemas import (
    ForeignActionType,
    ForeignPayload,
    DecisionSource
)
from geomas.actions.foreign.handler import execute_foreign

__all__ = [
    "ForeignActionType",
    "ForeignPayload",
    "DecisionSource",
    "execute_foreign"
]
