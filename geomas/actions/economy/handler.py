"""
Execution handler for Economic actions.
"""

import math
from typing import TYPE_CHECKING
from geomas.actions.schemas import ActionType, EconomicPayload
from geomas.actions.validators import ActionValidators
from geomas.actions.economy.trade import TradeOffer, execute_trade, evaluate_trade

if TYPE_CHECKING:
    from geomas.actions.engine import ActionEngine


WAR_TAX_SATISFACTION_PENALTY = 0.15
WAR_TAX_BUDGET_BOOST_RATIO = 0.10


def execute_economic(
    engine: 'ActionEngine',
    nation_id: str, 
    payload: EconomicPayload
) -> None:
    if not payload.action_type:
        return
    
    nation = engine.world.nations.get(nation_id)
    if not nation:
        return
    
    # --- INVEST_WELFARE ---
    if payload.action_type == ActionType.INVEST_WELFARE:
        amount = payload.parameters.get("amount", 100.0)
        
        # Check budget
        allowed, reason = ActionValidators.can_afford_budget(engine.world, nation_id, amount)
        if not allowed:
            engine.logs.append(f"[ECONOMIC] Failed INVEST_WELFARE: {reason}")
            return
        
        # Deduct budget
        engine.deduct_budget(nation_id, amount)
        
        # Diminishing returns: satisfaction += log(amount) * 0.1
        if amount > 0:
            satisfaction_gain = math.log(amount) * 0.02
            nation.public_satisfaction = min(
                1.0,
                nation.public_satisfaction + satisfaction_gain
            )
            engine.logs.append(
                f"[ECONOMIC] Invested {amount:.0f} in Welfare. "
                f"Satisfaction +{satisfaction_gain:.3f} (now {nation.public_satisfaction:.2f})"
            )
    
    # --- RAISE_WAR_TAX ---
    elif payload.action_type == ActionType.RAISE_WAR_TAX:
        allowed, reason = ActionValidators.can_raise_war_tax(engine.world, nation_id)
        if not allowed:
            engine.logs.append(f"[ECONOMIC] Failed RAISE_WAR_TAX: {reason}")
            return
        
        # Calculate tax boost based on population
        tax_boost = nation.total_population * WAR_TAX_BUDGET_BOOST_RATIO
        
        # Apply effects
        nation.total_budget += tax_boost
        nation.public_satisfaction -= WAR_TAX_SATISFACTION_PENALTY
        nation.public_satisfaction = max(0.0, nation.public_satisfaction)
        
        engine.logs.append(
            f"[ECONOMIC] War Tax raised! Budget +{tax_boost:.0f}, "
            f"Satisfaction -{WAR_TAX_SATISFACTION_PENALTY:.2f} (now {nation.public_satisfaction:.2f})"
        )
    
    # --- TRADE_PROPOSAL ---
    elif payload.action_type == ActionType.TRADE_PROPOSAL:
        target_id = payload.target_nation_id
        if not target_id:
            engine.logs.append("[ECONOMIC] Failed TRADE_PROPOSAL: No target specified")
            return
        
        # Build TradeOffer from parameters
        give = payload.parameters.get("give", {})
        receive = payload.parameters.get("receive", {})
        
        offer = TradeOffer(
            sender_id=nation_id,
            receiver_id=target_id,
            give=give,
            receive=receive
        )
        
        # Evaluate trade using Trade Oracle
        accepted, explanation = evaluate_trade(offer, engine.world)
        
        if accepted:
            # Execute trade: transfer resources
            execute_trade(engine.world, offer)
            
            # Boost trust slightly
            engine.adjust_trust(nation_id, target_id, 0.02)
            engine.adjust_trust(target_id, nation_id, 0.02)
            
            engine.logs.append(f"[TRADE] {nation_id} -> {target_id}: {explanation}")
        else:
            engine.logs.append(f"[TRADE] {nation_id} -> {target_id}: {explanation}")
