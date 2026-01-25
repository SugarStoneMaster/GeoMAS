"""
Execution handler for Military actions.
"""

from typing import List, TYPE_CHECKING
from geomas.schemas.actions import ActionType, MilitaryPayload
from geomas.actions.validators import ActionValidators

if TYPE_CHECKING:
    from geomas.actions.engine import ActionEngine


def execute_military_waterfall(
    engine: 'ActionEngine',
    nation_id: str, 
    payload: MilitaryPayload
) -> None:
    # Sort by priority (1 is highest)
    moves = sorted(payload.moves, key=lambda x: x.priority)
    
    for move in moves:
        cost = engine.COSTS.get(move.action_type, 0.0)
        
        # Check Budget
        allowed, reason = ActionValidators.can_afford_budget(engine.world, nation_id, cost)
        if not allowed:
            engine.logs.append(f"[MILITARY] Skipped {move.action_type}: {reason}")
            continue
        
        # Execute
        if move.action_type == ActionType.CREATE_UNIT:
            engine.deduct_budget(nation_id, cost)
            # TODO: Add actual unit to province in Phase 4
            engine.logs.append(f"[MILITARY] Created unit. Cost: {cost}")
            
        # TODO: Add MOVE_TROOPS, NUCLEAR_OPTION in Phase 4
