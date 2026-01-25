from enum import Enum
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from geomas.actions.schemas import MilitaryPayload, EconomicPayload, ForeignPayload

# --- ENUMS ---

class GlobalStrategy(str, Enum):
    TOTAL_EXPANSIONISM = "TOTAL_EXPANSIONISM"
    ARMED_ISOLATIONISM = "ARMED_ISOLATIONISM"
    SHADOW_SUBVERSION = "SHADOW_SUBVERSION"
    MERCANTILE_HEGEMONY = "MERCANTILE_HEGEMONY"
    DOMESTIC_RECOVERY = "DOMESTIC_RECOVERY"
    COALITION_BUILDER = "COALITION_BUILDER"
    SCORCHED_EARTH = "SCORCHED_EARTH"

class PublicIntent(str, Enum):
    PEACEFUL = "PEACEFUL"
    NEUTRAL = "NEUTRAL"
    DEFENSIVE = "DEFENSIVE"
    AGGRESSIVE = "AGGRESSIVE"

class MilitaryIntentType(str, Enum):
    DETERRENCE = "DETERRENCE"
    CONQUEST = "CONQUEST"
    DEFENSE = "DEFENSE"
    RECONNAISSANCE = "RECONNAISSANCE"
    PUNISHMENT = "PUNISHMENT"
    IDLE = "IDLE" 

class EconomicIntentType(str, Enum):
    GROWTH = "GROWTH"
    SABOTAGE = "SABOTAGE"
    SUPPORT = "SUPPORT"
    SURVIVAL = "SURVIVAL"
    IDLE = "IDLE"

class ForeignIntentType(str, Enum): 
    COOPERATION = "COOPERATION"
    COERCION = "COERCION"
    DECEPTION = "DECEPTION"
    APPEASEMENT = "APPEASEMENT"
    IDLE = "IDLE"

# --- INTENT OBJECTS (For XAI) ---

class MilitaryIntent(BaseModel):
    type: MilitaryIntentType
    reasoning: str = Field(..., description="Explanation of the military strategy.")

class EconomicIntent(BaseModel):
    type: EconomicIntentType
    reasoning: str = Field(..., description="Explanation of the economic strategy.")

class ForeignIntent(BaseModel): 
    type: ForeignIntentType
    reasoning: str = Field(..., description="Explanation of the foreign affairs strategy.")

# --- INTERMEDIATE PROPOSALS (Minister to President) ---

class DefenseProposal(BaseModel):
    intent: MilitaryIntent
    payload: MilitaryPayload
    urgency: int = Field(..., ge=1, le=10, description="1=Routine, 10=Existential Threat")

class EconomicProposal(BaseModel):
    intent: EconomicIntent
    payload: EconomicPayload
    projected_cost: float

class ForeignProposal(BaseModel):
    intent: ForeignIntent
    payload: ForeignPayload
    target_trust_impact: float

class CabinetBriefing(BaseModel):
    """Container for all minister proposals passed to the President."""
    defense: DefenseProposal
    economy: EconomicProposal
    foreign: ForeignProposal

# --- THE ENVELOPE ---

class CountryEnvelope(BaseModel): 
    turn: int
    sender_id: str
    
    # Strategic Layer
    global_strategy: GlobalStrategy

    # Public Layer (The Mask)
    public_statement: str = Field(..., description="Public rhetoric broadcast to the world.")
    public_intent: PublicIntent

    # Private Layer (The Reality)
    military_payload: MilitaryPayload
    military_intent: MilitaryIntent

    economic_payload: EconomicPayload
    economic_intent: EconomicIntent

    foreign_payload: ForeignPayload 
    foreign_intent: ForeignIntent   
