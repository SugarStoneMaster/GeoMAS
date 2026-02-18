from enum import Enum
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from geomas.actions.common import Decision
from geomas.actions.defense import DefensePayload, DefenseProposalPayload
from geomas.actions.economy import EconomicPayload, EconomicProposalPayload
from geomas.actions.foreign import ForeignPayload, ForeignProposalPayload

# --- ENUMS ---

class GlobalStrategy(str, Enum):
    """High-level strategic orientation of a nation."""
    TOTAL_EXPANSIONISM = "TOTAL_EXPANSIONISM"
    ARMED_ISOLATIONISM = "ARMED_ISOLATIONISM"
    COALITION_BUILDER = "COALITION_BUILDER"
    SCORCHED_EARTH = "SCORCHED_EARTH"


class GovernmentType(str, Enum):
    """Form of government, orthogonal to GlobalStrategy. Affects narrative/rhetoric only."""
    DEMOCRACY = "DEMOCRACY"
    AUTHORITARIAN = "AUTHORITARIAN"
    THEOCRACY = "THEOCRACY"


class DefenseIntentType(str, Enum):
    """Defense/military strategic intent types."""
    DETERRENCE = "DETERRENCE"       # Build up to prevent attack
    CONQUEST = "CONQUEST"           # Offensive expansion
    DEFENSE = "DEFENSE"             # Protect existing territory
    IDLE = "IDLE"                   # No significant military activity
    # Governance-specific intents (restricted by GovernmentType)
    EXPORT_DEMOCRACY = "EXPORT_DEMOCRACY"  # Democracy only: military intervention framed as liberation
    HOLY_WAR = "HOLY_WAR"                  # Theocracy only: military action framed as religious duty



class ForeignIntentType(str, Enum):
    """Foreign affairs strategic intent types."""
    COOPERATION = "COOPERATION"     # Genuine partnership
    COERCION = "COERCION"          # Force compliance through threats
    APPEASEMENT = "APPEASEMENT"    # Avoid conflict at cost
    IDLE = "IDLE"                  # No significant diplomatic action
    # Governance-specific intents (restricted by GovernmentType)
    EXPORT_DEMOCRACY = "EXPORT_DEMOCRACY"  # Democracy only: diplomacy framed as spreading freedom
    DIVINE_MANDATE = "DIVINE_MANDATE"      # Theocracy only: diplomacy framed as divine duty


# --- INTENT OBJECTS (For Minister Proposals) ---

class DefenseIntent(BaseModel):
    """Defense/military strategic intent with reasoning."""
    public_intent: DefenseIntentType
    private_intent: DefenseIntentType
    reasoning: str = Field(..., description="Explanation of strategy and any divergence (Public vs Private).")



class ForeignIntent(BaseModel):
    """Foreign affairs strategic intent with reasoning."""
    public_intent: ForeignIntentType
    private_intent: ForeignIntentType
    reasoning: str = Field(..., description="Explanation of strategy and any divergence (Public vs Private).")


# --- INTERMEDIATE PROPOSALS (Minister to President) ---

class DefenseProposal(BaseModel):
    """Defense minister's proposal to the president."""
    intent: DefenseIntent
    payload: DefenseProposalPayload

class EconomicProposal(BaseModel):
    """Economy minister's proposal to the president."""
    payload: EconomicProposalPayload

class ForeignProposal(BaseModel):
    """Foreign minister's proposal to the president."""
    intent: ForeignIntent
    payload: ForeignProposalPayload


class CabinetBriefing(BaseModel):
    """Container for all minister proposals passed to the President."""
    defense: DefenseProposal
    economy: EconomicProposal
    foreign: ForeignProposal


# --- PRESIDENTIAL DECREES ---



class PresidentialDecision(str, Enum):
    """Restricted decision set for President (cannot be PENDING)."""
    APPROVE = "APPROVE"
    VETO = "VETO"


class DefenseDecree(BaseModel):
    """President's decision on Defense."""
    action: PresidentialDecision
    reasoning: str

class EconomicDecree(BaseModel):
    """President's decision on Economy."""
    action: PresidentialDecision
    reasoning: str

class ForeignDecree(BaseModel):
    """President's decision on Foreign Affairs."""
    action: PresidentialDecision
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
    government_type: Optional[str] = None  # GovernmentType value for analysis
    
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
    
    # ═══════════════════════════════════════════════════════════════
    # PROMPT PERSISTENCE (Internal Use)
    # ═══════════════════════════════════════════════════════════════
    # ═══════════════════════════════════════════════════════════════
    # PROMPT PERSISTENCE (Internal Use)
    # ═══════════════════════════════════════════════════════════════
    last_system_prompt: Optional[str] = Field(
        None, exclude=True, description="The system prompt used for this decision."
    )
    last_input_prompt: Optional[str] = Field(
        None, exclude=True, description="The user/input prompt used for this decision."
    )
    
    # Minister Prompts
    defense_system_prompt: Optional[str] = Field(None, exclude=True)
    defense_input_prompt: Optional[str] = Field(None, exclude=True)
    economic_system_prompt: Optional[str] = Field(None, exclude=True)
    economic_input_prompt: Optional[str] = Field(None, exclude=True)
    foreign_system_prompt: Optional[str] = Field(None, exclude=True)
    foreign_input_prompt: Optional[str] = Field(None, exclude=True)
    
    opinion_system_prompt: Optional[str] = Field(None, exclude=True)
    opinion_input_prompt: Optional[str] = Field(None, exclude=True)

    # Original Proposals (Minister recommendations)
    original_defense_proposal: Optional[Any] = Field(None, exclude=True)
    original_economic_proposal: Optional[Any] = Field(None, exclude=True)
    original_foreign_proposal: Optional[Any] = Field(None, exclude=True)

    # Opinion Detailed Metrics
    opinion_multiplier_increase: Optional[float] = Field(None, exclude=True)
    opinion_multiplier_decrease: Optional[float] = Field(None, exclude=True)
    opinion_mood: Optional[str] = Field(None, exclude=True)
    opinion_reasoning: Optional[str] = Field(None, exclude=True)

    # RAW JSON AUDIT (Identity check)
    raw_president_response: Optional[Any] = Field(None, exclude=True)
    raw_defense_response: Optional[Any] = Field(None, exclude=True)
    raw_economic_response: Optional[Any] = Field(None, exclude=True)
    raw_foreign_response: Optional[Any] = Field(None, exclude=True)
    raw_opinion_response: Optional[Any] = Field(None, exclude=True)
