"""
Actions Package.

Contains the ActionEngine and all logic related to:
- Validation: checking if actions are permissible
- Execution: modifying the WorldState based on actions
- Handlers: specialized logic for Military, Economic, Foreign domains
"""

from geomas.actions.engine import ActionEngine
from geomas.actions.economy import TradeOffer, evaluate_trade

__all__ = ["ActionEngine", "TradeOffer", "evaluate_trade"]
