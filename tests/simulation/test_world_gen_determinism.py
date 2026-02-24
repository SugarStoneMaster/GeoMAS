import random
import numpy as np
from geomas.world.generation.generator import generate_world

def test_world_gen_determinism_robustness():
    """
    Verify that generate_world produces the exact same map for the same seed,
    even if the global random module state is changed between runs.
    """
    seed = 42
    
    # 1. First run
    random.seed(1)
    world1 = generate_world(seed=seed, n_cells=100, n_nations=3)
    
    # Extract some key map features
    nation_provinces1 = {nid: sorted(n.province_ids) for nid, n in world1.nations.items()}
    nation_budgets1 = {nid: n.total_budget for nid, n in world1.nations.items()}
    
    # 2. Change global random state radically
    random.seed(9999)
    for _ in range(100):
        random.random()
        
    # 3. Second run with same seed
    world2 = generate_world(seed=seed, n_cells=100, n_nations=3)
    
    nation_provinces2 = {nid: sorted(n.province_ids) for nid, n in world2.nations.items()}
    nation_budgets2 = {nid: n.total_budget for nid, n in world2.nations.items()}
    
    # 4. Compare
    assert nation_provinces1 == nation_provinces2, "Nation province assignments diverged!"
    assert nation_budgets1 == nation_budgets2, "Nation budget initialization diverged!"
    
    print("✅ World generation is stable across global random state changes.")

def test_proposal_id_determinism():
    """
    Verify that diplomatic proposal IDs are deterministic.
    """
    from geomas.actions.foreign.handler import execute_foreign
    from geomas.actions.foreign.schemas import ForeignPayload, ForeignActionType
    from geomas.actions.engine import ActionEngine
    from geomas.schemas.world import WorldState, NationState
    
    # Minimal world
    nations = {
        "A": NationState(id="A", name="A", color="red"),
        "B": NationState(id="B", name="B", color="blue")
    }
    world = WorldState(turn=1, nations=nations)
    engine = ActionEngine(world)
    
    # Propose Alliance
    payload = ForeignPayload(
        action_type=ForeignActionType.PROPOSE_ALLIANCE,
        target_nation_id="B",
        message="Hello"
    )
    
    execute_foreign(engine, "A", payload)
    
    proposal_id1 = world.nations["B"].pending_proposals[0]["id"]
    
    # Reset and run again
    world.nations["B"].pending_proposals = []
    execute_foreign(engine, "A", payload)
    proposal_id2 = world.nations["B"].pending_proposals[0]["id"]
    
    assert proposal_id1 == proposal_id2, f"Proposal IDs diverged: {proposal_id1} != {proposal_id2}"
    print(f"✅ Proposal IDs are deterministic: {proposal_id1}")

if __name__ == "__main__":
    test_world_gen_determinism_robustness()
    test_proposal_id_determinism()
