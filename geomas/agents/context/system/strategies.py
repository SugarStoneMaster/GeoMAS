"""
Shared Strategy Descriptions.

Centralized descriptions for GlobalStrategy values, shared across all agent prompts.
This reduces maintenance by having a single source of truth for what each strategy means.
"""

from geomas.agents.schemas import GlobalStrategy


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


def get_strategy_description(strategy: GlobalStrategy) -> str:
    """Get the shared description for a strategy."""
    return STRATEGY_DESCRIPTIONS.get(strategy, "balanced approach to governance")
