"""
Opinion schemas and constants.

Defines triggers, payloads, and satisfaction delta constants.
"""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
class OpinionTrigger(str, Enum):
    """Automatic triggers based on satisfaction levels."""
    GENERAL_STRIKE = "GENERAL_STRIKE"   # satisfaction < 20: -50% production
    CIVIL_UNREST = "CIVIL_UNREST"       # satisfaction < 10: provinces 0 output


class OpinionPayload(BaseModel):
    """Payload for opinion-related actions (mostly LLM-driven)."""
    multiplier_increase: float = Field(default=1.0, ge=0.1, le=2.0)
    multiplier_decrease: float = Field(default=1.0, ge=0.1, le=2.0)
    # Context provided by LLM agent explaining the multipliers
    reasoning: str = ""


# --- BASE SATISFACTION DELTAS (per turn) ---
# Applied before multipliers

DELTA_WAR_PENALTY = -3.0       # Each nation at war with
DELTA_PEACE_BONUS = 1.0        # If at peace with everyone
DELTA_RESOURCE_DEFICIT = -2.0  # Missing food/energy/materials
DELTA_RESOURCE_SURPLUS = 1.0   # Excess resources


# --- TRIGGER THRESHOLDS ---
THRESHOLD_PRODUCTION_DECAY_START = 50   # Production starts dropping below 100%
THRESHOLD_PRODUCTION_DECAY_FLOOR = 10   # Production hits minimum multiplier
THRESHOLD_GENERAL_STRIKE = 20           # Still kept for legacy/narrative triggers
THRESHOLD_CIVIL_UNREST = 10             # satisfaction < 10
THRESHOLD_UNREST_RECOVERY = 50          # satisfaction > 50 to end civil_unrest

# --- TRIGGER EFFECTS ---
MIN_PRODUCTION_MULTIPLIER = 0.5         # Minimum production before total unrest
STRIKE_PRODUCTION_PENALTY = 0.5         # Kept for compatibility if needed elsewhere
