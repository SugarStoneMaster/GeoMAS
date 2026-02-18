"""
Shared Strategy & Governance Descriptions.

Centralized descriptions for GlobalStrategy and GovernmentType values,
shared across all agent prompts. Single source of truth.
"""

from geomas.agents.schemas import GlobalStrategy
from geomas.agents.schemas.protocol import GovernmentType


# Strategy descriptions shared by all agents (Defense, Economy, Foreign, President)
STRATEGY_DESCRIPTIONS: dict[GlobalStrategy, str] = {
    GlobalStrategy.ARMED_ISOLATIONISM: (
        "prioritizing self-sufficiency, military deterrence, and avoiding foreign entanglements"
    ),
    GlobalStrategy.COALITION_BUILDER: (
        "building alliances, investing in relationships, and seeking collective security"
    ),
    GlobalStrategy.TOTAL_EXPANSIONISM: (
        "aggressive territorial growth through military dominance"
    ),
    GlobalStrategy.SCORCHED_EARTH: (
        "deterrence through unpredictability and willingness to deny resources to enemies"
    ),
}


# Governance descriptions shared by all agents
GOVERNANCE_DESCRIPTIONS: dict[GovernmentType, str] = {
    GovernmentType.DEMOCRACY: (
        "a democratic republic that values popular mandate, civil liberties, "
        "and humanitarian principles. Public statements must be framed through "
        "values of freedom, rights, and collective self-determination"
    ),
    GovernmentType.AUTHORITARIAN: (
        "an authoritarian state that values national strength, order, stability, "
        "and decisive leadership. Public statements must be framed through "
        "values of power, discipline, and national greatness"
    ),
    GovernmentType.THEOCRACY: (
        "a theocratic state that values moral duty, divine mandate, "
        "and ideological purity. Public statements must be framed through "
        "values of faith, righteousness, and sacred obligation"
    ),
}


def get_strategy_description(strategy: GlobalStrategy) -> str:
    """Get the shared description for a strategy."""
    return STRATEGY_DESCRIPTIONS.get(strategy, "balanced approach to governance")


def get_governance_description(government_type: GovernmentType) -> str:
    """Get the shared description for a government type."""
    return GOVERNANCE_DESCRIPTIONS.get(
        government_type,
        "a balanced government with no specific ideological framing"
    )

