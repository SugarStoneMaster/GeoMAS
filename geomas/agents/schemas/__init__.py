"""
Agents Schemas Package.

Contains protocol models for agent communication.
"""

from geomas.agents.schemas.protocol import (
    GlobalStrategy,
    PublicIntent,
    MilitaryIntentType,
    EconomicIntentType,
    ForeignIntentType,
    MilitaryIntent,
    EconomicIntent,
    ForeignIntent,
    DefenseProposal,
    EconomicProposal,
    ForeignProposal,
    CabinetBriefing,
    CountryEnvelope,
    MilitaryPayload,
    EconomicPayload,
    ForeignPayload
)

__all__ = [
    "GlobalStrategy",
    "PublicIntent",
    "MilitaryIntentType",
    "EconomicIntentType",
    "ForeignIntentType",
    "MilitaryIntent",
    "EconomicIntent",
    "ForeignIntent",
    "DefenseProposal",
    "EconomicProposal",
    "ForeignProposal",
    "CabinetBriefing",
    "CountryEnvelope",
    "MilitaryPayload",
    "EconomicPayload",
    "ForeignPayload"
]
