"""
Trade Oracle - Deterministic trade acceptance/rejection logic.

The Trade Oracle evaluates trade proposals without LLM involvement,
using a formula-based approach to ensure determinism.

Formula: TradeScore = (E_val × M_scarcity) - (R_risk × P_projection)
Trade is accepted if TradeScore > 0
"""

from typing import Dict, Tuple
from pydantic import BaseModel, Field

from geomas.schemas.world import WorldState, NationState


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
    """
    Represents a trade proposal from one nation to another.
    """
    sender_id: str
    receiver_id: str
    give: Dict[str, float] = Field(default_factory=dict)  # {"food": 100, "energy": 50}
    receive: Dict[str, float] = Field(default_factory=dict)  # {"materials": 30}
    duration_turns: int = 1  # 1 = one-off, >1 = recurring contract


# --- SCARCITY CALCULATION ---

def calculate_scarcity_multiplier(
    resource_type: str,
    current_stock: float,
    consumption_per_turn: float
) -> float:
    """
    Calculate scarcity multiplier based on how many turns of supply remain.
    
    Args:
        resource_type: "food", "energy", or "materials"
        current_stock: Current stockpile of the resource
        consumption_per_turn: How much is consumed per turn
        
    Returns:
        Multiplier: 1.0 (abundant) to 5.0 (critical shortage)
    """
    if consumption_per_turn <= 0:
        return 1.0
    
    turns_of_supply = current_stock / consumption_per_turn
    
    if turns_of_supply >= 5:
        return 1.0  # Abundant: 5+ turns of supply
    elif turns_of_supply >= 3:
        return 1.5  # Comfortable: 3-5 turns
    elif turns_of_supply >= 1:
        return 2.5  # Tight: 1-3 turns
    elif turns_of_supply > 0:
        return 4.0  # Critical: less than 1 turn
    else:
        return 5.0  # Zero stock


def get_nation_consumption(nation: NationState) -> Dict[str, float]:
    """
    Estimate per-turn consumption for each resource type.
    """
    from geomas.core import economy
    
    food_consumption = economy.calculate_food_consumption(nation.total_population)
    energy_consumption = economy.calculate_energy_consumption(nation.total_population)
    materials_consumption = economy.calculate_materials_consumption(
        nation.total_soldiers,
        nation.total_aircraft,
        nation.total_navy
    )
    
    return {
        "food": food_consumption,
        "energy": energy_consumption,
        "materials": materials_consumption,
    }


# --- RISK CALCULATION ---

def calculate_relational_risk(trust: float) -> float:
    """
    Calculate risk factor based on trust level.
    
    Args:
        trust: Trust value between 0.0 and 1.0 (normalized to 0-100 for formula)
        
    Returns:
        Risk factor (0.0 if trust >= 50, scales up to 5.0 if trust is 0)
    """
    trust_normalized = trust * 100  # Convert to 0-100 scale
    
    if trust_normalized >= 50:
        return 0.0
    else:
        return (50 - trust_normalized) / 10


def calculate_power_projection_impact(
    resource_type: str,
    receiver_power: float,
    sender_power: float
) -> float:
    """
    Calculate power projection impact for strategic resources.
    
    Higher impact if trading strategic resources to a militarily stronger nation.
    
    Args:
        resource_type: Type of resource being received
        receiver_power: Receiver's power projection
        sender_power: Sender's power projection
        
    Returns:
        Impact factor (0.0 to 2.0)
    """
    if resource_type not in STRATEGIC_RESOURCES:
        return 0.0
    
    # Power ratio (how much stronger is receiver?)
    if sender_power <= 0:
        power_ratio = 2.0  # Very weak sender
    else:
        power_ratio = receiver_power / sender_power
    
    if power_ratio <= 0.5:
        return 0.0  # Receiver is much weaker, no concern
    elif power_ratio <= 1.0:
        return 0.5  # Receiver is comparable
    elif power_ratio <= 1.5:
        return 1.0  # Receiver is stronger
    else:
        return 2.0  # Receiver is much stronger


# --- MAIN TRADE SCORE CALCULATION ---

def calculate_trade_score(
    offer: TradeOffer,
    world: WorldState
) -> Tuple[float, str]:
    """
    Calculate the trade score for a given offer.
    
    Formula: TradeScore = (E_val × M_scarcity) - (R_risk × P_projection)
    
    Args:
        offer: The trade proposal
        world: Current world state
        
    Returns:
        Tuple of (score, explanation)
    """
    receiver = world.nations.get(offer.receiver_id)
    sender = world.nations.get(offer.sender_id)
    
    if not receiver or not sender:
        return -999.0, "Invalid nation IDs"
    
    # Get trust level
    trust = world.trust_matrix.get(offer.receiver_id, {}).get(offer.sender_id, 0.5)
    
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
    # Consider what the receiver gives (what sender gets)
    p_projection = 0.0
    for resource in offer.receive.keys():
        impact = calculate_power_projection_impact(
            resource,
            sender.power_projection,
            receiver.power_projection
        )
        p_projection = max(p_projection, impact)  # Take worst case
    
    # Calculate cost of what receiver gives
    receiver_cost = 0.0
    for resource, amount in offer.receive.items():
        base_price = BASE_PRICES.get(resource, 1.0)
        receiver_cost += amount * base_price
    
    # Final score: benefit - cost - risk
    benefit = e_val * m_scarcity
    risk_penalty = r_risk * (1 + p_projection)
    
    # Net value = what I get - what I give - risk adjustment
    score = benefit - receiver_cost - risk_penalty
    
    explanation = (
        f"E_val={e_val:.1f}, M_scarcity={m_scarcity:.1f}, "
        f"R_risk={r_risk:.1f}, P_proj={p_projection:.1f}, "
        f"Cost={receiver_cost:.1f} → Score={score:.1f}"
    )
    
    return score, explanation


def evaluate_trade(offer: TradeOffer, world: WorldState) -> Tuple[bool, str]:
    """
    Evaluate whether a trade should be accepted.
    
    Args:
        offer: The trade proposal
        world: Current world state
        
    Returns:
        Tuple of (accepted: bool, explanation: str)
    """
    score, explanation = calculate_trade_score(offer, world)
    
    if score > 0:
        return True, f"ACCEPTED: {explanation}"
    else:
        return False, f"REJECTED: {explanation}"
