from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

class ActionType(str, Enum):
    # --- DEFENSE ACTIONS ---
    MOBILIZE_UNIT = "MOBILIZE_UNIT"
    FORTIFY_PROVINCE = "FORTIFY_PROVINCE"
    DEPLOY_TROOPS = "DEPLOY_TROOPS"
    NUCLEAR_OPTION = "NUCLEAR_OPTION"
    COVERT_ESPIONAGE = "COVERT_ESPIONAGE"

    # --- ECONOMIC ACTIONS ---
    INVEST_WELFARE = "INVEST_WELFARE"
    TRADE_PROPOSAL = "TRADE_PROPOSAL"
    IMPOSE_SANCTIONS = "IMPOSE_SANCTIONS"
    RAISE_WAR_TAX = "RAISE_WAR_TAX"
    DEVELOP_TECH = "DEVELOP_TECH"

    # --- FOREIGN AFFAIRS ACTIONS ---
    SEND_DIPLOMATIC_MESSAGE = "SEND_DIPLOMATIC_MESSAGE"
    PROPOSE_ALLIANCE = "PROPOSE_ALLIANCE"
    FORMAL_DECLARATION_OF_WAR = "FORMAL_DECLARATION_OF_WAR"
    BREAK_TREATY = "BREAK_TREATY"
    REQUEST_PEACE = "REQUEST_PEACE"
    FUND_INSURGENCY = "FUND_INSURGENCY"

    # --- PUBLIC OPINION EVENTS (Triggers) ---
    GENERAL_STRIKE = "GENERAL_STRIKE"
    CIVIL_UNREST = "CIVIL_UNREST"
    RALLY_EFFECT = "RALLY_EFFECT"

class DecisionSource(str, Enum):
    MINISTRY_ADVICE = "MINISTRY_ADVICE"
    PRESIDENT_OVERRIDE = "PRESIDENT_OVERRIDE"

# --- PAYLOADS ---

class MilitaryActionItem(BaseModel):
    priority: int
    action_type: ActionType
    target_nation_id: Optional[str] = None
    target_province_id: Optional[int] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)

class MilitaryPayload(BaseModel):
    source: DecisionSource
    moves: List[MilitaryActionItem] = Field(default_factory=list, description="Ordered list of actions (Waterfall Logic)")

class EconomicPayload(BaseModel):
    source: DecisionSource
    action_type: Optional[ActionType] = None
    target_nation_id: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)

class ForeignPayload(BaseModel): 
    source: DecisionSource
    action_type: Optional[ActionType] = None
    target_nation_id: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
