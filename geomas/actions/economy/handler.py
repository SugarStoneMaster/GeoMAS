"""
Execution handler for Economic actions.
"""

import math
from typing import TYPE_CHECKING
from geomas.actions.economy.schemas import EconomicActionType, EconomicPayload
from geomas.actions.validators import ActionValidators
from geomas.actions.economy.trade import TradeOffer, execute_trade, evaluate_trade

if TYPE_CHECKING:
    from geomas.actions.engine import ActionEngine


# Satisfaction scale: 0-100
WAR_TAX_SATISFACTION_PENALTY = 15  # Base penalty
WAR_TAX_BUDGET_BOOST_RATIO = 0.01  # 1% of population (Rebalanced from 0.10)

# INVEST_WELFARE constants
WELFARE_LOG_CONSTANT = 500         # Divisor for diminishing returns (rebalanced from 100)
WELFARE_MULTIPLIER = 7             # Satisfaction gain multiplier (rebalanced from 10)
WELFARE_MATERIALS_RATIO = 0.2      # 20% of budget amount must be paid in materials
WELFARE_MAX_BUDGET_RATIO = 0.25    # Max 25% of current budget per turn


def execute_economic(
    engine: 'ActionEngine',
    nation_id: str, 
    payload: EconomicPayload
) -> None:
    """Execute an economic action."""
    if not payload.action_type:
        # Fallback if None
        payload.execution_outcome.status = "SUCCESS"
        payload.execution_outcome.reason = "Minister is idle."
        return
        
    if payload.action_type == EconomicActionType.IDLE or payload.action_type == "IDLE":
        payload.execution_outcome.status = "SUCCESS"
        payload.execution_outcome.reason = "Minister is idle."
        engine.logs.append(f"💰 [ECONOMY] IDLE: {payload.message}" if payload.message else "💰 [ECONOMY] IDLE")
        return
    
    nation = engine.world.nations.get(nation_id)
    if not nation:
        return
    
    # --- INVEST_WELFARE ---
    if payload.action_type == EconomicActionType.INVEST_WELFARE:
        budget_amount = payload.amount or 100.0
        
        # Cap at 25% of current budget to prevent treasury drain
        max_welfare = nation.total_budget * WELFARE_MAX_BUDGET_RATIO
        if budget_amount > max_welfare:
            engine.logs.append(
                f"💰 [ECONOMY] INVEST_WELFARE: Clamped {budget_amount:.0f} → {max_welfare:.0f} (max 25% of budget)"
            )
            budget_amount = max_welfare
        materials_amount = budget_amount * WELFARE_MATERIALS_RATIO
        
        # Check budget and materials
        can_afford_b, reason_b = ActionValidators.can_afford_budget(engine.world, nation_id, budget_amount)
        if not can_afford_b:
            payload.execution_outcome.status = "FAILED"
            payload.execution_outcome.reason = reason_b
            engine.logs.append(f"💰 [ECONOMY] Failed INVEST_WELFARE: {reason_b}")
            return
            
        can_afford_m, reason_m = ActionValidators.can_afford_materials(engine.world, nation_id, materials_amount)
        if not can_afford_m:
            payload.execution_outcome.status = "FAILED"
            payload.execution_outcome.reason = reason_m
            engine.logs.append(f"💰 [ECONOMY] Failed INVEST_WELFARE: {reason_m}")
            return
        
        # Deduct resources
        engine.deduct_budget(nation_id, budget_amount)
        nation.total_materials -= materials_amount
        
        # Logarithmic diminishing returns: gain = K * log(1 + amount / C)
        if budget_amount > 0:
            satisfaction_gain = WELFARE_MULTIPLIER * math.log(1 + budget_amount / WELFARE_LOG_CONSTANT)
            nation.public_satisfaction = min(
                100,
                nation.public_satisfaction + satisfaction_gain
            )
            msg_str = f" Message to citizens: '{payload.message}'" if payload.message else ""
            # Success Outcome
            payload.execution_outcome.status = "SUCCESS"
            payload.execution_outcome.reason = "Welfare investment completed"
            payload.execution_outcome.details = {
                "budget_spent": budget_amount,
                "materials_spent": materials_amount,
                "satisfaction_gain": satisfaction_gain
            }

            engine.logs.append(
                f"💰 [ECONOMY] Invested {budget_amount:.0f} Budget and {materials_amount:.0f} Materials in Welfare. "
                f"Satisfaction +{satisfaction_gain:.1f} (now {nation.public_satisfaction:.0f}){msg_str}"
            )
    
    # --- RAISE_WAR_TAX ---
    elif payload.action_type == EconomicActionType.RAISE_WAR_TAX:
        allowed, reason = ActionValidators.can_raise_war_tax(engine.world, nation_id)
        if not allowed:
            payload.execution_outcome.status = "FAILED"
            payload.execution_outcome.reason = reason
            engine.logs.append(f"💰 [ECONOMY] Failed RAISE_WAR_TAX: {reason}")
            return
        
        # Calculate tax boost
        tax_boost = nation.total_population * WAR_TAX_BUDGET_BOOST_RATIO
        
        # Dynamic satisfaction penalty: taxing a miserable population is harder
        # If sat < 30, penalty increases by 50%
        final_penalty = WAR_TAX_SATISFACTION_PENALTY
        if nation.public_satisfaction < 30:
            final_penalty *= 1.5
            
        # Apply effects
        nation.total_budget += tax_boost
        nation.public_satisfaction -= final_penalty
        nation.public_satisfaction = max(0, nation.public_satisfaction)
        
        # Success Outcome
        payload.execution_outcome.status = "SUCCESS"
        payload.execution_outcome.reason = "War tax raised"
        payload.execution_outcome.details = {
            "budget_gain": tax_boost,
            "satisfaction_penalty": final_penalty
        }

        msg_str = f" Message to citizens: '{payload.message}'" if payload.message else ""
        engine.logs.append(
            f"💰 [ECONOMY] War Tax raised! Budget +{tax_boost:.0f}, "
            f"Satisfaction -{final_penalty:.0f} (now {nation.public_satisfaction:.0f}){msg_str}"
        )
    
    # --- TRADE_PROPOSAL ---
    elif payload.action_type == EconomicActionType.TRADE_PROPOSAL:
        target_id = payload.target_nation_id
        if not target_id:
            payload.execution_outcome.status = "FAILED"
            payload.execution_outcome.reason = "No target nation specified"
            engine.logs.append("📦 [ECONOMY] Failed TRADE_PROPOSAL: No target specified")
            return
        
        # 1. Extract Single-Resource Parameters
        give_type = payload.give_type.lower() if payload.give_type else None
        give_amount = payload.give_amount
        want_type = payload.want_type.lower() if payload.want_type else None
        
        if not give_type or not want_type or give_amount is None:
            payload.execution_outcome.status = "FAILED"
            payload.execution_outcome.reason = "Missing trade parameters"
            engine.logs.append(f"📦 [ECONOMY] Failed TRADE_PROPOSAL: Missing parameters (give_type, give_amount, or want_type)")
            return
            
        if give_amount <= 0:
            payload.execution_outcome.status = "FAILED"
            payload.execution_outcome.reason = "Trade amount must be positive"
            engine.logs.append(f"📦 [ECONOMY] Failed TRADE_PROPOSAL: Amount must be positive")
            return
            
        from geomas.actions.economy.trade import BASE_PRICES
        
        # Verify resource validity
        give_price = BASE_PRICES.get(give_type)
        want_price = BASE_PRICES.get(want_type)
        
        if give_price is None or want_price is None:
             payload.execution_outcome.status = "FAILED"
             payload.execution_outcome.reason = f"Invalid resource: {give_type}/{want_type}"
             engine.logs.append(f"📦 [ECONOMY] Failed TRADE_PROPOSAL: Invalid resource '{give_type}' or '{want_type}'")
             return

        # --- CLAMPING LOGIC (15% Cap) ---
        nation = engine.world.nations[nation_id]
        current_stock = getattr(nation, f"total_{give_type}", 0.0)
        
        # Max export is 15% of current stock
        # Exception: budget can be traded more freely? No, keep 15% rule for safety.
        max_export = current_stock * 0.15
        
        # Correction: If stock is very low, 15% might be tiny. Minimum 50 units floor?
        # Let's stick to strict 15% to prevent draining.
        
        original_amount = give_amount
        clamped = False
        
        if give_amount > max_export:
            engine.logs.append(f"📦 [TRADE] Clamped export {original_amount:.0f} -> {max_export:.0f} (15% of sender's {current_stock:.0f})")
            give_amount = max_export
            clamped = True
            
        if give_amount <= 0:
             payload.execution_outcome.status = "FAILED"
             payload.execution_outcome.reason = f"Export amount clamped to zero (Stock {current_stock:.0f} is too low)"
             engine.logs.append(f"📦 [ECONOMY] Failed TRADE_PROPOSAL: Stock too low to export")
             return

        # 2. Calculate Value
        total_value = give_amount * give_price
        
        # 3. Calculate Receive Amount
        receive_amount = total_value / want_price
        
        # --- RECEIVER CLAMPING (Double Protection) ---
        # Ensure target doesn't pay more than 15% of their stock
        target_nation = engine.world.nations.get(target_id)
        if target_nation:
            receiver_stock = getattr(target_nation, f"total_{want_type}", 0.0)
            max_receiver_pay = receiver_stock * 0.15
            
            if receive_amount > max_receiver_pay:
                # If receiver has 0 stock, max_pay is 0. Trade collapses to 0.
                if max_receiver_pay <= 0:
                    payload.execution_outcome.status = "FAILED"
                    payload.execution_outcome.reason = f"Target {target_id} has no {want_type} to pay with (Stock {receiver_stock:.0f})"
                    engine.logs.append(f"📦 [TRADE] Failed: Target {target_id} has insufficient {want_type}")
                    return

                scaling_factor = max_receiver_pay / receive_amount
                
                old_give = give_amount
                old_receive = receive_amount
                
                # Scale everything down
                give_amount = give_amount * scaling_factor
                receive_amount = max_receiver_pay
                
                # Recalculate total value for trust math later
                total_value = give_amount * give_price
                
                clamped = True
                engine.logs.append(f"📦 [TRADE] Clamped by RECEIVER limit ({target_id}): Scaled down to {receive_amount:.0f} {want_type} (15% cap). Give: {old_give:.0f}->{give_amount:.0f}")

        if clamped:
             # Avoid duplicate log if double clamped? 
             # Actually good to see both or just the final?
             # If sender clamped first, we saw that log. 
             # If receiver ALSO clamps, we see this second log. That's fine.
             
             # Safely check recent logs for duplication
             recent_logs = engine.logs[-5:] if engine.logs else []
             if not any("RECEIVER limit" in l for l in recent_logs): 
                 engine.logs.append(f"📦 [TRADE] Final Offer: {give_amount:.0f} {give_type} <-> {receive_amount:.0f} {want_type}")
        
        # Build strict single-resource dicts for internal TradeOffer
        give = {give_type: give_amount}
        receive = {want_type: receive_amount}
        
        # Build internal TradeOffer
        offer = TradeOffer(
            sender_id=nation_id,
            receiver_id=target_id,
            give=give,
            receive=receive
        )
        
        # Evaluate using Oracle (Trust & Balance Check)
        accepted, explanation = evaluate_trade(offer, engine.world)
        
        # Update Outcome
        payload.execution_outcome.status = "SUCCESS" if accepted else "REJECTED"
        
        final_reason = explanation
        if accepted and clamped:
            final_reason = f"{explanation} (Note: Amounts were clamped to 15% stock limits)"
            
        payload.execution_outcome.reason = final_reason
        payload.execution_outcome.details = {
            "target_id": target_id,
            "give_type": give_type,
            "give_amount": give_amount,
            "want_type": want_type,
            "total_value": total_value,
            "accepted": accepted
        }

        if accepted:
            # Execute trade: transfer resources
            execute_trade(engine.world, offer)
            
            # Boost trust dynamically
            # Base +2, plus +1 for every 500 value exchanged. Cap at +10.
            base_trust = 2.0
            bonus_trust = int(total_value / 500)
            trust_gain = min(10.0, base_trust + bonus_trust)
            
            engine.adjust_trust(nation_id, target_id, trust_gain)
            engine.adjust_trust(target_id, nation_id, trust_gain)
            
            msg_str = f" Message: '{payload.message}'" if payload.message else ""
            engine.logs.append(f"📦 [TRADE] ACCEPTED {nation_id} -> {target_id} (+{trust_gain:.0f} Trust): {explanation}{msg_str}")
        else:
            msg_str = f" Message: '{payload.message}'" if payload.message else ""
            engine.logs.append(f"📦 [TRADE] REJECTED {nation_id} -> {target_id}: {explanation}{msg_str}")

    # --- IDLE ---
    elif payload.action_type == EconomicActionType.IDLE:
        payload.execution_outcome.status = "SUCCESS"
        payload.execution_outcome.reason = "Minister is idle."
        if payload.message:
            engine.logs.append(f"💰 [ECONOMY] IDLE: {payload.message}")
