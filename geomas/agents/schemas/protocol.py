from enum import Enum
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from geomas.actions.common import Decision
from geomas.actions.defense import DefensePayload
from geomas.actions.economy import EconomicPayload
from geomas.actions.foreign import ForeignPayload

# --- ENUMS ---

class GlobalStrategy(str, Enum):
    """High-level strategic orientation of a nation."""
    TOTAL_EXPANSIONISM = "TOTAL_EXPANSIONISM"
    ARMED_ISOLATIONISM = "ARMED_ISOLATIONISM"
    SHADOW_SUBVERSION = "SHADOW_SUBVERSION"
    MERCANTILE_HEGEMONY = "MERCANTILE_HEGEMONY"
    DOMESTIC_RECOVERY = "DOMESTIC_RECOVERY"
    COALITION_BUILDER = "COALITION_BUILDER"
    SCORCHED_EARTH = "SCORCHED_EARTH"


class DefenseIntentType(str, Enum):
    """Defense/military strategic intent types."""
    DETERRENCE = "DETERRENCE"       # Build up to prevent attack
    CONQUEST = "CONQUEST"           # Offensive expansion
    DEFENSE = "DEFENSE"             # Protect existing territory
    PUNISHMENT = "PUNISHMENT"       # Retaliate for past actions
    IDLE = "IDLE"                   # No significant military activity


class EconomicIntentType(str, Enum):
    """Economic strategic intent types."""
    GROWTH = "GROWTH"               # Develop economy
    SABOTAGE = "SABOTAGE"           # Undermine others economically
    SUPPORT = "SUPPORT"             # Aid allies economically
    SURVIVAL = "SURVIVAL"           # Emergency measures to stay afloat
    IDLE = "IDLE"                   # No significant economic action


class ForeignIntentType(str, Enum):
    """Foreign affairs strategic intent types."""
    COOPERATION = "COOPERATION"     # Genuine partnership
    COERCION = "COERCION"          # Force compliance through threats
    DECEPTION = "DECEPTION"        # Mislead other nations
    APPEASEMENT = "APPEASEMENT"    # Avoid conflict at cost
    IDLE = "IDLE"                  # No significant diplomatic action


# --- INTENT OBJECTS (For Minister Proposals) ---

class DefenseIntent(BaseModel):
    """Defense/military strategic intent with reasoning."""
    type: DefenseIntentType
    reasoning: str = Field(..., description="Explanation of the defense strategy.")


class EconomicIntent(BaseModel):
    """Economic strategic intent with reasoning."""
    type: EconomicIntentType
    reasoning: str = Field(..., description="Explanation of the economic strategy.")


class ForeignIntent(BaseModel):
    """Foreign affairs strategic intent with reasoning."""
    type: ForeignIntentType
    reasoning: str = Field(..., description="Explanation of the foreign affairs strategy.")


# --- INTERMEDIATE PROPOSALS (Minister to President) ---

class DefenseProposal(BaseModel):
    """Defense minister's proposal to the president."""
    intent: DefenseIntent
    payload: DefensePayload
    urgency: int = Field(..., ge=1, le=10, description="1=Routine, 10=Existential Threat")

class EconomicProposal(BaseModel):
    """Economy minister's proposal to the president."""
    intent: EconomicIntent
    payload: EconomicPayload
    projected_cost: float

class ForeignProposal(BaseModel):
    """Foreign minister's proposal to the president."""
    intent: ForeignIntent
    payload: ForeignPayload
    target_trust_impact: float


class CabinetBriefing(BaseModel):
    """Container for all minister proposals passed to the President."""
    defense: DefenseProposal
    economy: EconomicProposal
    foreign: ForeignProposal


# --- PRESIDENTIAL DECREES ---



class DefenseDecree(BaseModel):
    """President's decision on Defense."""
    action: Decision
    reasoning: str

class EconomicDecree(BaseModel):
    """President's decision on Economy."""
    action: Decision
    reasoning: str

class ForeignDecree(BaseModel):
    """President's decision on Foreign Affairs."""
    action: Decision
    reasoning: str

class PresidentialDecree(BaseModel):
    """
    The final decision structure from the President.
    Determines whether to accept minister proposals or veto them.
    """
    defense: DefenseDecree
    economy: EconomicDecree
    foreign: ForeignDecree
    
    # Metadata for the final envelope
    public_statement: str = Field(..., description="Address to the nation/world.")
    
    # Intents for alignment/misalignment tracking
    defense_public_intent: DefenseIntentType
    defense_private_intent: DefenseIntentType
    economic_public_intent: EconomicIntentType
    economic_private_intent: EconomicIntentType
    foreign_public_intent: ForeignIntentType
    foreign_private_intent: ForeignIntentType
    
    # Explanations
    defense_private_reasoning: str
    economic_private_reasoning: str
    foreign_private_reasoning: str


# --- THE ENVELOPE ---

class CountryEnvelope(BaseModel):
    """
    The complete action envelope sent by a nation each turn.
    
    Structure:
    - Strategic Layer: GlobalStrategy (orientation)
    - Public Layer: statement + public intents (visible to all)
    - Private Layer: private intents + reasoning (hidden, for XAI)
    - Action Layer: payloads (ground truth of what actually happens)
    
    Deception is measured by comparing public_intent vs private_intent per domain.
    """
    turn: int
    sender_id: str
    
    # ═══════════════════════════════════════════════════════════════
    # STRATEGIC LAYER
    # ═══════════════════════════════════════════════════════════════
    global_strategy: GlobalStrategy
    
    # ═══════════════════════════════════════════════════════════════
    # PUBLIC LAYER (Broadcast to all nations)
    # ═══════════════════════════════════════════════════════════════
    public_statement: str = Field(
        ..., 
        description="Single public message with sections for defense/economy/foreign."
    )
    
    # ═══════════════════════════════════════════════════════════════
    # DEFENSE DOMAIN
    # ═══════════════════════════════════════════════════════════════
    defense_payload: DefensePayload
    defense_public_intent: DefenseIntentType = Field(
        ..., description="What we claim publicly about our military actions."
    )
    defense_private_intent: DefenseIntentType = Field(
        ..., description="Our true military objective (hidden from others)."
    )
    defense_private_reasoning: str = Field(
        ..., description="Internal reasoning for defense decisions (XAI)."
    )
    
    # ═══════════════════════════════════════════════════════════════
    # ECONOMIC DOMAIN
    # ═══════════════════════════════════════════════════════════════
    economic_payload: EconomicPayload
    economic_public_intent: EconomicIntentType = Field(
        ..., description="What we claim publicly about our economic actions."
    )
    economic_private_intent: EconomicIntentType = Field(
        ..., description="Our true economic objective (hidden from others)."
    )
    economic_private_reasoning: str = Field(
        ..., description="Internal reasoning for economic decisions (XAI)."
    )
    
    # ═══════════════════════════════════════════════════════════════
    # FOREIGN DOMAIN
    # ═══════════════════════════════════════════════════════════════
    foreign_payload: ForeignPayload
    foreign_public_intent: ForeignIntentType = Field(
        ..., description="What we claim publicly about our diplomatic actions."
    )
    foreign_private_intent: ForeignIntentType = Field(
        ..., description="Our true diplomatic objective (hidden from others)."
    )
    foreign_private_reasoning: str = Field(
        ..., description="Internal reasoning for foreign decisions (XAI)."
    )
