"""
Execution handler for Diplomatic actions.
"""

from typing import TYPE_CHECKING
from geomas.actions.schemas import ActionType, ForeignPayload

if TYPE_CHECKING:
    from geomas.actions.engine import ActionEngine


def execute_foreign(
    engine: 'ActionEngine',
    nation_id: str, 
    payload: ForeignPayload
) -> None:
    if not payload.action_type:
        return
    
    if payload.action_type == ActionType.SEND_DIPLOMATIC_MESSAGE:
        target = payload.target_nation_id
        msg = payload.parameters.get("message", "")
        engine.logs.append(f"[DIPLOMACY] Message to {target}: '{msg}'")
        
        # Small trust boost for friendly communication
        if target:
            engine.adjust_trust(nation_id, target, 0.01)
            engine.adjust_trust(target, nation_id, 0.01)


def adjust_trust(engine: 'ActionEngine', nation_a: str, nation_b: str, delta: float) -> None:
    """Adjust trust between two nations."""
    if nation_a not in engine.world.trust_matrix:
        engine.world.trust_matrix[nation_a] = {}
    
    current = engine.world.trust_matrix[nation_a].get(nation_b, 0.5)
    new_trust = max(0.0, min(1.0, current + delta))
    engine.world.trust_matrix[nation_a][nation_b] = new_trust
