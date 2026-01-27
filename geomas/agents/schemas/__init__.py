"""
Agents Schemas Package.

Communication protocol models for agent decision-making.

Models:
    - GlobalStrategy: High-level nation strategy (EXPANSIONISM, ISOLATIONISM, etc.)
    - PublicIntent: What the nation claims publicly (PEACEFUL, AGGRESSIVE, etc.)
    - *IntentType: Private intentions per domain (defense, economic, foreign)
    - *Intent: Intent with reasoning (for explainability)
    - *Proposal: Minister recommendations to the President
    - CabinetBriefing: All minister proposals combined
    - CountryEnvelope: Final output from NationAgent containing all layers

The CountryEnvelope is the key data structure exchanged between agents
and the ActionEngine, containing both public facade and private reality.
"""

from geomas.agents.schemas.protocol import (
    GlobalStrategy,
    PublicIntent,
    DefenseIntentType,
    EconomicIntentType,
    ForeignIntentType,
    DefenseIntent,
    EconomicIntent,
    ForeignIntent,
    DefenseProposal,
    EconomicProposal,
    ForeignProposal,
    CabinetBriefing,
    CountryEnvelope,
)

# Re-export payloads from domain packages for convenience
from geomas.actions.defense import DefensePayload
from geomas.actions.economy import EconomicPayload
from geomas.actions.foreign import ForeignPayload

__all__ = [
    "GlobalStrategy",
    "PublicIntent",
    "DefenseIntentType",
    "EconomicIntentType",
    "ForeignIntentType",
    "DefenseIntent",
    "EconomicIntent",
    "ForeignIntent",
    "DefenseProposal",
    "EconomicProposal",
    "ForeignProposal",
    "CabinetBriefing",
    "CountryEnvelope",
    "DefensePayload",
    "EconomicPayload",
    "ForeignPayload"
]

