
from geomas.world import generate_world
from geomas.actions import ActionEngine
from geomas.actions.foreign import ForeignPayload, ForeignActionType, execute_foreign
from geomas.agents.context.input import ForeignInputBuilder
from geomas.schemas.world import RelationshipState

def test_missing_proposals():
    print("--- TESTING MISSING PROPOSALS ---")
    world = generate_world(seed=42, n_nations=3, n_cells=100)
    engine = ActionEngine(world)
    
    n1_id = list(world.nations.keys())[0]
    n2_id = list(world.nations.keys())[1]
    
    print(f"Nation 1: {n1_id}")
    print(f"Nation 2: {n2_id}")
    
    # ensure trust is high enough for alliance (need > 60)
    world.trust_matrix.setdefault(n1_id, {})[n2_id] = 80.0
    world.trust_matrix.setdefault(n2_id, {})[n1_id] = 80.0
    
    # 1. N1 proposes alliance to N2
    payload = ForeignPayload(
        action_type=ForeignActionType.PROPOSE_ALLIANCE,
        target_nation_id=n2_id,
        message="Let's ally"
    )
    # execute_foreign(engine, nation_id, payload)
    execute_foreign(engine, n1_id, payload)
    logs = engine.logs
    print("Logs (N1 act):", logs)
    
    # 2. Check N2 pending proposals
    n2 = world.nations[n2_id]
    print(f"N2 Pending Proposals (Raw): {n2.pending_proposals}")
    assert len(n2.pending_proposals) == 1
    assert n2.pending_proposals[0]["type"] == "ALLIANCE"
    
    # 3. Check ForeignInputBuilder for N2
    builder = ForeignInputBuilder(world)
    context = builder.build(n2_id, turn=1)
    print("--- N2 Context ---")
    print(context)
    
    if "ALLIANCE proposal from" in context:
        print("✅ SUCCESS: Proposal visible in context")
    else:
        print("❌ FAILURE: Proposal NOT visible in context")

def test_ghost_peace():
    print("\n--- TESTING GHOST PEACE ---")
    world = generate_world(seed=42, n_nations=3, n_cells=100)
    engine = ActionEngine(world)
    
    n1_id = list(world.nations.keys())[0]
    n2_id = list(world.nations.keys())[1]
    
    # Start at WAR
    world.relationship_matrix.setdefault(n1_id, {})[n2_id] = "WAR"
    world.relationship_matrix.setdefault(n2_id, {})[n1_id] = "WAR"
    
    # 1. N1 Requests Peace
    payload = ForeignPayload(
        action_type=ForeignActionType.REQUEST_PEACE,
        target_nation_id=n2_id,
        message="Peace please"
    )
    engine.logs = []
    execute_foreign(engine, n1_id, payload)
    logs = engine.logs
    print("Logs (N1 act):", logs)
    
    # Verify proposal exists
    n2 = world.nations[n2_id]
    print(f"N2 Pending: {n2.pending_proposals}")
    assert len(n2.pending_proposals) == 1
    assert n2.pending_proposals[0]["type"] == "PEACE"
    
    # 2. N2 Accepts (but specifies ALLIANCE ref type by mistake?)
    # or specifies correct ref type
    payload_accept = ForeignPayload(
        action_type=ForeignActionType.ACCEPT_PROPOSAL,
        target_nation_id=n1_id,
        proposal_ref_type="PEACE", # Correct
        message="Ok fine"
    )
    engine.logs = []
    execute_foreign(engine, n2_id, payload_accept)
    logs2 = engine.logs
    print("Logs (N2 act):", logs2)
    
    if "Peace treaty signed" in str(logs2):
        print("✅ SUCCESS: Peace signed correctly")
    else:
        print("❌ FAILURE: Peace NOT signed")

    # 3. Test ACCEPT without REQUEST (Ghost Peace)
    print("\n--- Testing ACCEPT without REQUEST ---")
    # clear proposals
    n2.pending_proposals = []
    
    payload_ghost = ForeignPayload(
        action_type=ForeignActionType.ACCEPT_PROPOSAL,
        target_nation_id=n1_id,
        proposal_ref_type="PEACE",
        message="Ghost peace"
    )
    engine.logs = []
    execute_foreign(engine, n2_id, payload_ghost)
    logs3 = engine.logs
    print("Logs (Ghost):", logs3)
    
    if "Peace treaty signed" in str(logs3):
        print("❌ FAILURE: Peace signed without request! (Ghost Bug Reproduced)")
    else:
        print("✅ SUCCESS: Ghost peace rejected")

if __name__ == "__main__":
    test_missing_proposals()
    test_ghost_peace()
