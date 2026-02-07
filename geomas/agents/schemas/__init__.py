"""
Agents Schemas Package.

Communication protocol models for agent decision-making.

Models:
    - GlobalStrategy: High-level nation strategy (EXPANSIONISM, ISOLATIONISM, etc.)
    - *IntentType: Intent types per domain (defense, economic, foreign)
    - *Intent: Intent with reasoning (for minister proposals)
    - *Proposal: Minister recommendations to the President
    - CabinetBriefing: All minister proposals combined
    - CountryEnvelope: Final output from NationAgent containing all layers

The CountryEnvelope is the key data structure exchanged between agents
and the ActionEngine. It contains:
    - Public layer: statement + public intents (visible to all)
    - Private layer: private intents + reasoning (hidden, for XAI)
    - Action layer: payloads (ground truth)
"""

from geomas.agents.schemas.protocol import (
    GlobalStrategy,
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
    PresidentialDecree,
    Decision,
    DefenseDecree,
    EconomicDecree,
    ForeignDecree,
)

# Re-export payloads from domain packages for convenience
from geomas.actions.defense import DefensePayload
from geomas.actions.economy import EconomicPayload
from geomas.actions.foreign import ForeignPayload

__all__ = [
    "GlobalStrategy",
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
    "PresidentialDecree",
    "Decision",
    "DefenseDecree",
    "EconomicDecree",
    "ForeignDecree",
    "DefensePayload",
    "EconomicPayload",
    "ForeignPayload"
]
