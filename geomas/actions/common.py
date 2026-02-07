"""
Common Schemas for Actions Package.

Shared types and enums used across all domain-specific action handlers.
"""

from enum import Enum


class Decision(str, Enum):
    """Decision outcome for actions.
    
    Tracks whether a proposal was APPROVED (from Ministry)
    or VETOED (by President).
    """
    APPROVE = "APPROVE"
    VETO = "VETO"
