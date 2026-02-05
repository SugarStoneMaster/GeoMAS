"""
System Prompts Package.

Contains static system prompts for all agent types.
These define identity, role, and output format expectations.
"""

from geomas.agents.context.system.president import PresidentSystemPrompt
from geomas.agents.context.system.defense import DefenseSystemPrompt
from geomas.agents.context.system.economy import EconomySystemPrompt
from geomas.agents.context.system.foreign import ForeignSystemPrompt
from geomas.agents.context.system.opinion import OpinionSystemPrompt

__all__ = [
    "PresidentSystemPrompt",
    "DefenseSystemPrompt",
    "EconomySystemPrompt",
    "ForeignSystemPrompt",
    "OpinionSystemPrompt",
]
