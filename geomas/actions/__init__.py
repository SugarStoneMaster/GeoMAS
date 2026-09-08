"""
Actions Package — The Deterministic Rules Oracle.

Action validation and execution engine for agent decisions. This package
is the "referee" layer: agent intent (CountryEnvelope) passes through
validation and execution before modifying the WorldState. No agent can
bypass these rules.

Architecture:
    ActionEngine is a thin facade that delegates to domain-specific handlers.
    The execution order within a single envelope is: Defense → Economy → Foreign.
    Each domain handler receives the engine reference for shared state access
    (world, spatial graph, trust matrix, logs).

Subpackages:
    - defense/: Military actions (CREATE_UNIT, MOVE_TROOPS, NUCLEAR_OPTION)
        Handler (985 lines): Waterfall priority resolver — actions are sorted
        by priority number and executed sequentially. Nuclear strikes are
        processed first, then land/sea/air attacks, then peaceful movements
        and unit creation. Combat resolution uses binary outcomes with
        terrain defense bonuses (MOUNTAIN=1.5x) and deterministic RNG.
        Naval landings follow a multi-stage flow: naval combat → coastal
        landing → crew conversion (10 soldiers per ship).
        Combat module: calculate_force(), resolve_land_combat(),
        resolve_naval_combat(), resolve_air_strike(), execute_naval_landing().
        Schemas: DefenseActionItem with typed fields (unit_type, quantity,
        source/target province), UNIT_COSTS, TERRAIN_DEFENSE_MULTIPLIER,
        MOVEMENT_RANGE constants.

    - economy/: Economic actions (INVEST_WELFARE, RAISE_WAR_TAX, TRADE_PROPOSAL)
        Welfare: Logarithmic diminishing returns: Gain = 7 × log(1 + Amount/500).
        Capped at 25% of current budget per turn. Requires 20% materials cost.
        War Tax: +1% of population as budget, -15 satisfaction penalty
        (scaled to -22 if satisfaction < 30). Requires satisfaction ≥ 20.
        Trade: Evaluated by a Trade Oracle formula:
        TradeScore = (E_val × M_scarcity) - (R_risk × P_projection).
        Stock caps at 15% of sender's current stock per resource.

    - foreign/: Diplomatic actions (one per turn)
        DECLARE_WAR: Sets relationship to WAR, generates WarStats,
        triggers Call to Arms for victim's mutual defense allies.
        PROPOSE_ALLIANCE: Creates pending proposal (NON_AGGRESSION or
        MUTUAL_DEFENSE tier). Requires trust ≥ 40.
        RESPOND_TO_PROPOSAL: Accept/reject pending alliance/peace proposals.
        REQUEST_PEACE: Creates pending peace proposal for war resolution.
        SEND_DIPLOMATIC_MESSAGE: Trust impact by message type (TRADE_INTEREST
        +3, THREAT -5, PRAISE +5, WARNING -3, etc.). 5-turn cooldown per pair.
        BREAK_TREATY: Ends alliance, trust penalty -30.

    - opinion/: Public satisfaction dynamics
        Centralized satisfaction delta calculation combining events, government
        actions, and state-based modifiers. Cultural traits generate LLM
        multipliers (0.1-2.0) for positive/negative satisfaction changes.
        Triggers: General Strike (satisfaction < 20, -30% production),
        Civil Unrest (satisfaction < 10, production halted, province revolts),
        Recovery (satisfaction > 50 clears unrest). Production multiplier
        follows linear decay from 100% at satisfaction=60 to MIN_PRODUCTION
        at satisfaction=0.

Modules:
    - engine.py: ActionEngine facade (validates + executes, delegates to handlers)
    - validators.py: Pure validation functions — can_move_troops (contiguous
      pathfinding via NetworkX subgraph), can_attack (adjacency check),
      can_afford_budget/materials, can_raise_war_tax (satisfaction threshold),
      validate_target_is_not_self.
    - common.py: Shared enums (Decision: PENDING/APPROVED/REJECTED/VETOED,
      ExecutionOutcome).

Classes:
    - ActionEngine: Main orchestrator that validates and executes actions

The ActionEngine processes CountryEnvelopes from agents and:
    1. Validates actions against game rules
    2. Executes valid actions by modifying the WorldState
    3. Returns logs describing what happened
"""

from geomas.actions.engine import ActionEngine

# Re-export domain packages for convenience
from geomas.actions.defense import (
    DefenseActionType,
    DefensePayload,
    DefenseActionItem,
    UnitType
)
from geomas.actions.economy import (
    EconomicActionType,
    EconomicPayload,
    TradeOffer,
    evaluate_trade
)
from geomas.actions.foreign import (
    ForeignActionType,
    ForeignPayload
)

__all__ = [
    "ActionEngine",
    # Defense
    "DefenseActionType",
    "DefensePayload",
    "DefenseActionItem",
    "UnitType",
    # Economy
    "EconomicActionType",
    "EconomicPayload",
    "TradeOffer",
    "evaluate_trade",
    # Foreign
    "ForeignActionType",
    "ForeignPayload"
]
