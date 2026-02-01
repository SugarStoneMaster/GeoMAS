"""
Trade Execution and Oracle.

Handles trade offers, scarcity calculations, and deterministic trade evaluation.
"""

from typing import Dict, Tuple, List, Optional
from pydantic import BaseModel, Field

from geomas.schemas.world import WorldState, NationState
from geomas import calculators as economy


# --- RESOURCE PRICING ---
BASE_PRICES = {
    "food": 1.0,
    "energy": 2.0,
    "materials": 3.0,
}

# Strategic resources (affect power projection calculation)
STRATEGIC_RESOURCES = {"energy", "materials"}


# --- TRADE OFFER SCHEMA ---
class TradeOffer(BaseModel):
    """Represents a trade proposal from one nation to another."""
    sender_id: str
    receiver_id: str
    give: Dict[str, float] = Field(default_factory=dict)  # {"food": 100, "energy": 50}
    receive: Dict[str, float] = Field(default_factory=dict)  # {"materials": 30}
    duration_turns: int = 1  # 1 = one-off, >1 = recurring contract


def execute_trade(world: WorldState, offer: TradeOffer) -> None:
    """Execute a trade by transferring resources between nations."""
    sender = world.nations.get(offer.sender_id)
    receiver = world.nations.get(offer.receiver_id)
    
    if not sender or not receiver:
        return
    
    # Sender gives resources to receiver
    for resource, amount in offer.give.items():
        sender_attr = f"total_{resource}"
        receiver_attr = f"total_{resource}"
        
        if hasattr(sender, sender_attr) and hasattr(receiver, receiver_attr):
            current_sender = getattr(sender, sender_attr)
            current_receiver = getattr(receiver, receiver_attr)
            
            # Can't give more than you have
            actual_amount = min(amount, current_sender)
            setattr(sender, sender_attr, current_sender - actual_amount)
            setattr(receiver, receiver_attr, current_receiver + actual_amount)
    
    # Receiver gives resources to sender
    for resource, amount in offer.receive.items():
        receiver_attr = f"total_{resource}"
        sender_attr = f"total_{resource}"
        
        if hasattr(receiver, receiver_attr) and hasattr(sender, sender_attr):
            current_receiver = getattr(receiver, receiver_attr)
            current_sender = getattr(sender, sender_attr)
            
            actual_amount = min(amount, current_receiver)
            setattr(receiver, receiver_attr, current_receiver - actual_amount)
            setattr(sender, sender_attr, current_sender + actual_amount)


# --- ORACLE LOGIC ---

def evaluate_trade(offer: TradeOffer, world: WorldState) -> Tuple[bool, str]:
    """
    Evaluate whether a trade should be accepted.
    Formula: TradeScore = (E_val × M_scarcity) - (R_risk × P_projection)
    Trade is accepted if TradeScore > 0
    """
    score, explanation = calculate_trade_score(offer, world)
    
    if score > 0:
        return True, f"ACCEPTED: {explanation}"
    else:
        return False, f"REJECTED: {explanation}"


def calculate_trade_score(offer: TradeOffer, world: WorldState) -> Tuple[float, str]:
    receiver = world.nations.get(offer.receiver_id)
    sender = world.nations.get(offer.sender_id)
    
    if not receiver or not sender:
        return -999.0, "Invalid nation IDs"
    
    # Get trust level (0-100 scale)
    trust = world.trust_matrix.get(offer.receiver_id, {}).get(offer.sender_id, 50)
    
    # Get consumption rates for scarcity calculation
    receiver_consumption = get_nation_consumption(receiver)
    
    # Calculate E_val (Economic Value of what receiver gets)
    e_val = 0.0
    for resource, amount in offer.give.items():
        base_price = BASE_PRICES.get(resource, 1.0)
        e_val += amount * base_price
    
    # Calculate M_scarcity (average scarcity of received resources)
    m_scarcity = 0.0
    resource_count = 0
    for resource, amount in offer.give.items():
        current_stock = getattr(receiver, f"total_{resource}", 0.0)
        consumption = receiver_consumption.get(resource, 1.0)
        scarcity = calculate_scarcity_multiplier(resource, current_stock, consumption)
        m_scarcity += scarcity
        resource_count += 1
    
    if resource_count > 0:
        m_scarcity /= resource_count
    else:
        m_scarcity = 1.0
    
    # Calculate R_risk (Relational Risk)
    r_risk = calculate_relational_risk(trust)
    
    # Calculate P_projection (Power Projection Impact)
    p_projection = 0.0
    for resource in offer.receive.keys():
        impact = calculate_power_projection_impact(
            resource,
            sender.power_projection,
            receiver.power_projection
        )
        p_projection = max(p_projection, impact)
    
    # Calculate cost of what receiver gives
    receiver_cost = 0.0
    for resource, amount in offer.receive.items():
        base_price = BASE_PRICES.get(resource, 1.0)
        receiver_cost += amount * base_price
    
    # Final score
    benefit = e_val * m_scarcity
    risk_penalty = r_risk * (1 + p_projection)
    score = benefit - receiver_cost - risk_penalty
    
    explanation = (
        f"E_val={e_val:.1f}, M_scarcity={m_scarcity:.1f}, "
        f"R_risk={r_risk:.1f}, P_proj={p_projection:.1f}, "
        f"Cost={receiver_cost:.1f} → Score={score:.1f}"
    )
    
    return score, explanation


def calculate_scarcity_multiplier(resource_type: str, current_stock: float, consumption_per_turn: float) -> float:
    if consumption_per_turn <= 0: return 1.0
    turns_of_supply = current_stock / consumption_per_turn
    
    if turns_of_supply >= 5: return 1.0
    elif turns_of_supply >= 3: return 1.5
    elif turns_of_supply >= 1: return 2.5
    elif turns_of_supply > 0: return 4.0
    else: return 5.0


def get_nation_consumption(nation: NationState) -> Dict[str, float]:
    food = economy.calculate_food_consumption(nation.total_population)
    energy = economy.calculate_energy_consumption(nation.total_population)
    materials = economy.calculate_materials_consumption(
        nation.total_soldiers, nation.total_aircraft, nation.total_navy
    )
    return {"food": food, "energy": energy, "materials": materials}


def calculate_relational_risk(trust: float) -> float:
    trust_normalized = trust * 100
    if trust_normalized >= 50: return 0.0
    else: return (50 - trust_normalized) / 10


def calculate_power_projection_impact(resource_type: str, receiver_power: float, sender_power: float) -> float:
    if resource_type not in STRATEGIC_RESOURCES: return 0.0
    
    if sender_power <= 0: power_ratio = 2.0
    else: power_ratio = receiver_power / sender_power
    
    if power_ratio <= 0.5: return 0.0
    elif power_ratio <= 1.0: return 0.5
    elif power_ratio <= 1.5: return 1.0
    else: return 2.0
