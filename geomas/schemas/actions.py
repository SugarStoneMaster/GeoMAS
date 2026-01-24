from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

class ActionType(str, Enum):
    # --- DEFENSE ACTIONS ---
    CREATE_UNIT = "CREATE_UNIT"
    MOVE_TROOPS = "MOVE_TROOPS" # Could trigger war
    NUCLEAR_OPTION = "NUCLEAR_OPTION"

    # --- ECONOMIC ACTIONS ---
    INVEST_WELFARE = "INVEST_WELFARE"
    TRADE_PROPOSAL = "TRADE_PROPOSAL"
    RAISE_WAR_TAX = "RAISE_WAR_TAX"

    # --- FOREIGN AFFAIRS ACTIONS ---
    SEND_DIPLOMATIC_MESSAGE = "SEND_DIPLOMATIC_MESSAGE"
    PROPOSE_ALLIANCE = "PROPOSE_ALLIANCE"
    FORMAL_DECLARATION_OF_WAR = "FORMAL_DECLARATION_OF_WAR"
    BREAK_TREATY = "BREAK_TREATY"
    REQUEST_PEACE = "REQUEST_PEACE"

    # --- PUBLIC OPINION EVENTS (Triggers) ---
    GENERAL_STRIKE = "GENERAL_STRIKE"
    CIVIL_UNREST = "CIVIL_UNREST"
    RALLY_EFFECT = "RALLY_EFFECT"

class DecisionSource(str, Enum):
    MINISTRY_ADVICE = "MINISTRY_ADVICE"
    PRESIDENT_OVERRIDE = "PRESIDENT_OVERRIDE"


class UnitType(str, Enum):
    """Military unit types that can be created and deployed."""
    SOLDIER = "SOLDIER"   # Ground troops, can be on LAND/COASTAL/MOUNTAIN or transported by NAVY
    NAVY = "NAVY"         # Naval vessels, can only be on OCEAN (territorial waters)
    AIRCRAFT = "AIRCRAFT" # Air units, can be on LAND/COASTAL/MOUNTAIN, have extended range


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
