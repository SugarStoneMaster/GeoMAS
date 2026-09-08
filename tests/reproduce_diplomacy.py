
from geomas.world import generate_world
from geomas.actions import ActionEngine
from geomas.actions.foreign import ForeignPayload, ForeignActionType, execute_foreign
from geomas.agents.context.events.context_manager import ContextManager
from geomas.agents.context.events.schemas import EventType

def test_duplicate_proposals():
    print("--- TESTING DUPLICATE PROPOSALS ---")
    world = generate_world(seed=42, n_nations=3, n_cells=100)
    engine = ActionEngine(world)
    
    n1_id = list(world.nations.keys())[0]
    n2_id = list(world.nations.keys())[1]
    
    # High trust
    world.trust_matrix.setdefault(n1_id, {})[n2_id] = 80.0
    
    # 1. First Proposal
    payload = ForeignPayload(
        action_type=ForeignActionType.PROPOSE_ALLIANCE,
        target_nation_id=n2_id,
        message="Ally?"
    )
    execute_foreign(engine, n1_id, payload)
    print("Logs 1:", engine.logs)
    assert len(world.nations[n2_id].pending_proposals) == 1
    
    # 2. Second Proposal (Should be blocked)
    engine.logs = []
    execute_foreign(engine, n1_id, payload)
    print("Logs 2:", engine.logs)
    
    # Assert logs contain blocking message
    if any("already pending" in log for log in engine.logs):
        print("✅ SUCCESS: Duplicate proposal blocked")
    else:
        print("❌ FAILURE: Duplicate proposal NOT blocked")
        
    # Assert still only 1 pending
    assert len(world.nations[n2_id].pending_proposals) == 1

def test_ghost_peace_event_mapping():
    print("\n--- TESTING EVENT MAPPING (GHOST PEACE FIX) ---")
    world = generate_world(seed=42, n_nations=3, n_cells=100)
    cm = ContextManager()
    cm.initialize_from_world(world)
    
    n1_id = list(world.nations.keys())[0]
    n2_id = list(world.nations.keys())[1]
    
    # Simulate an ACCEPT_PROPOSAL action with MISSING proposal_ref_type
    # This was causing "PEACE_SIGNED" previously
    class MockBehavior:
        action_type = "ACCEPT_PROPOSAL"
        target_nation_id = n2_id
        proposal_ref_type = None # MISSING!
        message = "Ok"
    
    behavior = MockBehavior()
    
    event = cm._behavior_to_event(turn=1, nation_id=n1_id, behavior=behavior, world=world)
    
    print(f"Generated Event: {event.event_type} - {event.summary}")
    
    if event.event_type == EventType.PEACE_SIGNED:
        print("❌ FAILURE: Mapped to PEACE_SIGNED (Ghost Peace persists)")
    elif event.event_type == EventType.ALLIANCE_FORMED:
        print("✅ SUCCESS: Mapped to ALLIANCE_FORMED (Default safely)")
    else:
        print(f"❓ UNEXPECTED: {event.event_type}")

if __name__ == "__main__":
    test_duplicate_proposals()
    test_ghost_peace_event_mapping()
