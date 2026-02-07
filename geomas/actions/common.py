"""
Common Schemas for Actions Package.

Shared types and enums used across all domain-specific action handlers.
"""

from enum import Enum


class Decision(str, Enum):
    """Decision outcome for actions.
    
    Tracks whether a proposal is still PENDING, 
    was APPROVED (By president), or VETOED (by President).
    """
    PENDING = "PENDING"
    APPROVE = "APPROVE"
    VETO = "VETO"
