"""
Opinion Package.

Handles public opinion dynamics and population LLM agent for satisfaction modifiers.
"""

from geomas.actions.opinion.schemas import (
    OpinionPayload,
    OpinionTrigger,
)
from geomas.actions.opinion.handler import (
    execute_opinion,
    apply_satisfaction_deltas,
    check_triggers,
    get_production_multiplier,
    get_province_production_multiplier,
)
from geomas.actions.opinion.traits import generate_cultural_traits

__all__ = [
    "OpinionPayload",
    "OpinionTrigger",
    "execute_opinion",
    "apply_satisfaction_deltas",
    "check_triggers",
    "generate_cultural_traits",
    "get_production_multiplier",
    "get_province_production_multiplier",
]
