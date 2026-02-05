"""
Context Package for LLM Agents.

Provides translators, generators, and prompt builders that convert world state
into natural language suitable for LLM agent consumption.

Subpackages:
    - system/: Static system prompts for each agent type
    - input/: Dynamic input builders for each agent type
    - memory/: Memory management (ContextManager, schemas)

Modules:
    - spatial: Geographic/strategic intelligence (SpatialTranslator)
    - profile: Nation identity and relationships (NationProfileGenerator)
    - military: Dynamic military state (MilitaryTranslator)

Usage:
    # System prompts (static)
    from geomas.agents.context.system import PresidentSystemPrompt
    
    # Input builders (dynamic)
    from geomas.agents.context.input import DefenseInputBuilder
    
    # Memory/Context management
    from geomas.agents.context.memory import ContextManager
    
    # Translators (utilities)
    from geomas.agents.context import MilitaryTranslator
"""

from geomas.agents.context.spatial import SpatialTranslator
from geomas.agents.context.profile import NationProfileGenerator
from geomas.agents.context.military import MilitaryTranslator

# System prompts
from geomas.agents.context.system import (
    PresidentSystemPrompt,
    DefenseSystemPrompt,
    EconomySystemPrompt,
    ForeignSystemPrompt,
    OpinionSystemPrompt,
)

# Input builders
from geomas.agents.context.input import (
    PresidentInputBuilder,
    DefenseInputBuilder,
    EconomyInputBuilder,
    ForeignInputBuilder,
    OpinionInputBuilder,
)

# Memory management
from geomas.agents.context.memory import (
    ContextManager,
    RelationshipSummary,
    NotableEvent,
    MyAction,
    EventType,
)

__all__ = [
    # Translators
    "SpatialTranslator",
    "NationProfileGenerator",
    "MilitaryTranslator",
    # System prompts
    "PresidentSystemPrompt",
    "DefenseSystemPrompt",
    "EconomySystemPrompt",
    "ForeignSystemPrompt",
    "OpinionSystemPrompt",
    # Input builders
    "PresidentInputBuilder",
    "DefenseInputBuilder",
    "EconomyInputBuilder",
    "ForeignInputBuilder",
    "OpinionInputBuilder",
    # Memory
    "ContextManager",
    "RelationshipSummary",
    "NotableEvent",
    "MyAction",
    "EventType",
]


