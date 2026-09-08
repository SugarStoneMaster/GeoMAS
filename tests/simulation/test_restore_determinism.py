import pytest
import os
from geomas.simulation.engine import SimulationEngine
from geomas.agents.schemas import GlobalStrategy

def test_restore_determinism(tmp_path):
    """
    Verify that restoring a simulation from DB preserves the original 
    strategic assignments and nuclear weapon counts, regardless of 
    current power projection rankings.
    """
    db_path = str(tmp_path / "test_sim.duckdb")
    
    # 1. Initialize Simulation (Turn 1)
    sim = SimulationEngine(
        map_seed=123,
        history_seed=456,
        n_cells=300,
        n_nations=4,
        db_path=db_path
    )
    
    # Store initial assignments
    initial_strategies = {nid: n.global_strategy for nid, n in sim.world.nations.items()}
    initial_nukes = {nid: n.nukes for nid, n in sim.world.nations.items()}
    
    # Ensure some nukes were assigned
    assert sum(initial_nukes.values()) > 0, "No nukes assigned during initialization"
    
    # 2. Advance to Turn 2 and save
    sim.world.turn = 2
    from geomas.db.serialization import serialize_world_snapshot
    snapshot = serialize_world_snapshot(sim.world, sim.context_manager)
    sim.db.save_snapshot(sim.simulation_id, 2, **snapshot)
    
    # 3. Simulate "Drift": Modify power projection significantly
    # Force a nation with low ranking to have massive resources
    # and a top nation to have zero.
    ranked = sorted(
        sim.world.nations.keys(),
        key=lambda nid: sim.world.nations[nid].power_projection,
        reverse=True
    )
    top_nation = ranked[0]
    bottom_nation = ranked[-1]
    
    sim.world.nations[top_nation].total_budget = 0
    sim.world.nations[bottom_nation].total_budget = 999999
    
    # 4. Reload Turn 2
    # This triggers _init_agents()
    sim.load_state(2)
    
    # 5. Verify Constancy
    for nid, nation in sim.world.nations.items():
        # Strategy must be identical to Turn 1
        assert nation.global_strategy == initial_strategies[nid], f"Strategy changed for {nid} after load"
        
        # Nukes must be identical to Turn 1 (since they weren't used)
        assert nation.nukes == initial_nukes[nid], f"Nukes changed for {nid} after load"
        
    print("[SUCCESS] Strategy and Nukes preserved across load_state despite power ranking shift.")

def test_nuclear_consumption_persistence(tmp_path):
    """
    Verify that if nukes are USED, they remain used after a reload 
    (no resurrection bug).
    """
    db_path = str(tmp_path / "test_nuke_use.duckdb")
    sim = SimulationEngine(map_seed=1, history_seed=1, n_nations=4, db_path=db_path)
    
    # Find a nation with nukes
    nuke_nation_id = next(nid for nid, n in sim.world.nations.items() if n.nukes > 0)
    original_count = sim.world.nations[nuke_nation_id].nukes
    
    # Consume one nuke manually
    sim.world.nations[nuke_nation_id].nukes -= 1
    
    # Save at Turn 2
    sim.world.turn = 2
    from geomas.db.serialization import serialize_world_snapshot
    snapshot = serialize_world_snapshot(sim.world, sim.context_manager)
    sim.db.save_snapshot(sim.simulation_id, 2, **snapshot)
    
    # Reload Turn 2
    sim.load_state(2)
    
    # Verify it didn't reset to original_count
    assert sim.world.nations[nuke_nation_id].nukes == original_count - 1, "Nukes resurrected after reload!"
    print("[SUCCESS] Nuclear consumption is persistent across reloads.")
