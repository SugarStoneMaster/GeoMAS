"""
Actions Package.

Action validation and execution engine for agent decisions.

Classes:
    - ActionEngine: Main orchestrator that validates and executes actions

Subpackages:
    - schemas/: Action type enums and payload models
    - economy/: Economic action handlers and trade logic

The ActionEngine processes CountryEnvelopes from agents and:
    1. Validates actions against game rules (can_attack, has_resources, etc.)
    2. Executes valid actions by modifying the WorldState
    3. Returns logs describing what happened

Domains:
    - Military: Unit creation, movement, combat
    - Economic: Welfare investment, war taxes, trade
    - Foreign: Diplomacy, alliances, declarations
"""

from geomas.actions.engine import ActionEngine
from geomas.actions.economy import TradeOffer, evaluate_trade

__all__ = ["ActionEngine", "TradeOffer", "evaluate_trade"]
