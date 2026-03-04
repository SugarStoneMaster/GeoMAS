from geomas.actions.engine import ActionEngine
from geomas.actions.foreign.schemas import ForeignPayload, ForeignActionType
from geomas.actions.common import Decision
from geomas.world import generate_world

def test_idle_status():
    world = generate_world(seed=42, n_cells=50, n_nations=2)
    engine = ActionEngine(world)
    
    payload = ForeignPayload(
        decision=Decision.APPROVE,
        action_type=ForeignActionType.IDLE
    )
    
    from geomas.actions.defense.schemas import DefensePayload
    from geomas.actions.economy.schemas import EconomicPayload
    
    class MockEnvelope:
        sender_id = list(world.nations.keys())[0]
        defense_payload = DefensePayload(decision=Decision.APPROVE, moves=[])
        economic_payload = EconomicPayload(decision=Decision.APPROVE, action_type=None)
        foreign_payload = payload
    
    envelope = MockEnvelope()
    
    print(f"\\nBEFORE: {payload.execution_outcome.status}")
    engine.execute_envelope(envelope)
    print(f"AFTER: {payload.execution_outcome.status}")
    
    assert payload.execution_outcome.status == "SUCCESS"
