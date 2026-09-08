"""
Economy Actions Package.

Economic action handlers and trade system.

Modules:
    - schemas: EconomicActionType, EconomicPayload, Decision
    - handler: Execution logic for INVEST_WELFARE, RAISE_WAR_TAX, TRADE_PROPOSAL
    - trade: Trade offer schema and evaluation oracle

Trade System:
    The Trade Oracle (evaluate_trade) uses a formula to decide if trades are accepted:
    TradeScore = (E_val × M_scarcity) - (R_risk × P_projection)
    
    Where:
    - E_val: Economic value of offered resources
    - M_scarcity: How much receiver needs the resources
    - R_risk: Relational risk based on trust level
    - P_projection: Power shift from trade
"""

from geomas.actions.economy.schemas import (
    EconomicActionType,
    EconomicPayload,
    EconomicProposalPayload,
    Decision
)
from geomas.actions.economy.handler import execute_economic
from geomas.actions.economy.trade import (
    TradeOffer,
    execute_trade,
    evaluate_trade,
    BASE_PRICES
)

__all__ = [
    "EconomicActionType", 
    "EconomicPayload",
    "EconomicProposalPayload",
    "execute_economic",
    "TradeOffer",
    "execute_trade",
    "evaluate_trade",
    "BASE_PRICES"
]
