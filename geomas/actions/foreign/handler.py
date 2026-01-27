"""
Foreign Affairs Action Handler.

Executes diplomatic actions.
"""

from typing import TYPE_CHECKING
from geomas.actions.foreign.schemas import ForeignActionType, ForeignPayload

if TYPE_CHECKING:
    from geomas.actions.engine import ActionEngine


def execute_foreign(
    engine: 'ActionEngine',
    nation_id: str, 
    payload: ForeignPayload
) -> None:
    """Execute a foreign affairs action."""
    if not payload.action_type:
        return
    
    if payload.action_type == ForeignActionType.SEND_DIPLOMATIC_MESSAGE:
        target = payload.target_nation_id
        msg = payload.parameters.get("message", "")
        engine.logs.append(f"[FOREIGN] Message to {target}: '{msg}'")
        
        # Small trust boost for friendly communication
        if target:
            engine.adjust_trust(nation_id, target, 0.01)
            engine.adjust_trust(target, nation_id, 0.01)
    
    # TODO: Add handlers for PROPOSE_ALLIANCE, DECLARATION_OF_WAR, etc.
