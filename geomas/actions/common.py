"""
Common Schemas for Actions Package.

Shared types and enums used across all domain-specific action handlers.
"""

from enum import Enum


class DecisionSource(str, Enum):
    """Source of the decision for audit trail.
    
    Used to track whether an action came from the AI minister's recommendation
    or was overridden by the president/leader.
    """
    MINISTRY_ADVICE = "MINISTRY_ADVICE"
    PRESIDENT_OVERRIDE = "PRESIDENT_OVERRIDE"
