"""
Common Schemas for Actions Package.

Shared types and enums used across all domain-specific action handlers.
"""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class Decision(str, Enum):
    """Decision outcome for actions.
    
    Tracks whether a proposal is still PENDING, 
    was APPROVED (By president), or VETOED (by President).
    """
    PENDING = "PENDING"
    APPROVE = "APPROVE"
    VETO = "VETO"


class ExecutionOutcome(BaseModel):
    """
    Result of an action execution.
    Stored in envelopes to allow synchronization with ContextManager and DB.
    """
    status: str = Field("PENDING", description="SUCCESS, FAILED, or PARTIAL")
    reason: Optional[str] = Field(None, description="Explanation for results (e.g., failure reason)")
    details: Dict[str, Any] = Field(default_factory=dict, description="Technical data or metrics")
