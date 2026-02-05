"""
Input Prompts Package.

Contains dynamic input/context builders for all agent types.
These generate turn-specific context from world state.
"""

from geomas.agents.context.input.president import PresidentInputBuilder
from geomas.agents.context.input.defense import DefenseInputBuilder
from geomas.agents.context.input.economy import EconomyInputBuilder
from geomas.agents.context.input.foreign import ForeignInputBuilder
from geomas.agents.context.input.opinion import OpinionInputBuilder

__all__ = [
    "PresidentInputBuilder",
    "DefenseInputBuilder",
    "EconomyInputBuilder",
    "ForeignInputBuilder",
    "OpinionInputBuilder",
]
