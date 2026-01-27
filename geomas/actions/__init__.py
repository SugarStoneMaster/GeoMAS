"""
Actions Package.

Action validation and execution engine for agent decisions.

Subpackages:
    - defense/: Military actions (CREATE_UNIT, MOVE_TROOPS, NUCLEAR_OPTION)
    - economy/: Economic actions (INVEST_WELFARE, TRADE_PROPOSAL, RAISE_WAR_TAX)
    - foreign/: Diplomatic actions (SEND_DIPLOMATIC_MESSAGE, PROPOSE_ALLIANCE, etc.)

Classes:
    - ActionEngine: Main orchestrator that validates and executes actions

The ActionEngine processes CountryEnvelopes from agents and:
    1. Validates actions against game rules
    2. Executes valid actions by modifying the WorldState
    3. Returns logs describing what happened
"""

from geomas.actions.engine import ActionEngine

# Re-export domain packages for convenience
from geomas.actions.defense import (
    DefenseActionType,
    DefensePayload,
    DefenseActionItem,
    UnitType
)
from geomas.actions.economy import (
    EconomicActionType,
    EconomicPayload,
    TradeOffer,
    evaluate_trade
)
from geomas.actions.foreign import (
    ForeignActionType,
    ForeignPayload
)

__all__ = [
    "ActionEngine",
    # Defense
    "DefenseActionType",
    "DefensePayload",
    "DefenseActionItem",
    "UnitType",
    # Economy
    "EconomicActionType",
    "EconomicPayload",
    "TradeOffer",
    "evaluate_trade",
    # Foreign
    "ForeignActionType",
    "ForeignPayload"
]
