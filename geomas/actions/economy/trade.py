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
    "budget": 1.0,  # Standard currency
}

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
    Evaluate whether a trade should be accepted based on deterministic rules.
    
    Rules:
    1. Trust Threshold: Receiver must have Trust >= 40 (Neutral or better) towards Sender.
    2. Receiver Balance: Receiver must have enough resources to fulfill the 'receive' part (which they give).
    3. Sender Balance: Sender must have enough resources to fulfill the 'give' part.
    """
    receiver = world.nations.get(offer.receiver_id)
    sender = world.nations.get(offer.sender_id)
    
    if not receiver or not sender:
        return False, "Invalid nation IDs"
    
    # 1. Trust Check
    # Trust is 0-100. Default 50.
    trust = world.trust_matrix.get(offer.receiver_id, {}).get(offer.sender_id, 50)
    if trust < 40:
        return False, f"Trust too low ({trust:.0f} < 40)"
        
    # 2. Sender Balance Check (Does sender have what they offered?)
    for res, amount in offer.give.items():
        current = getattr(sender, f"total_{res}", 0.0)
        if current < amount:
            return False, f"Sender insufficiency: {res} ({current:.1f} < {amount:.1f})"

    # 3. Receiver Balance Check (Does receiver have what they need to give back?)
    for res, amount in offer.receive.items():
        current = getattr(receiver, f"total_{res}", 0.0)
        if current < amount:
            return False, f"Receiver insufficiency: {res} ({current:.1f} < {amount:.1f})"
            
    return True, "Conditions met (Trust >= 40, Balances sufficient)"
