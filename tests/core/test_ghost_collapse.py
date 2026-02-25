import pytest
import random
from geomas.simulation.engine import SimulationEngine
from geomas.actions.defense.combat import _conquer_province

def test_ghost_nation_collapse():
    # 1. Setup engine and world
    engine = SimulationEngine(map_seed=42, n_cells=100)
    world = engine.world
    
    nation_ids = sorted(list(world.nations.keys()))
    attacker_id = nation_ids[0]
    victim_id = nation_ids[1]
    
    attacker = world.nations[attacker_id]
    victim = world.nations[victim_id]
    
    # 2. Preparation: Victim has exactly 3 provinces
    # First, strip all provinces
    for pid in list(victim.province_ids):
        world.provinces[pid].owner_id = None
    victim.province_ids = []
    
    # Assign 3 fresh ones
    all_pids = list(world.provinces.keys())
    random.seed(42)
    selected = random.sample(all_pids, 3)
    
    for pid in selected:
        prov = world.provinces[pid]
        prov.owner_id = victim_id
        victim.province_ids.append(pid)
        
    p1_id, p2_id, p3_id = selected
    p1, p2, p3 = world.provinces[p1_id], world.provinces[p2_id], world.provinces[p3_id]
    
    # Setup population: P1 has people, P2 and P3 are ghosts (uninhabited)
    p1.population = 1000
    p2.population = 0
    p3.population = 0
    
    # Initial state check
    assert len(victim.province_ids) == 3
    assert victim.is_active
    
    # 3. Action: Conquer P1 (the only province with population)
    # This should trigger the collapse of the rest of the nation
    _conquer_province(world, attacker_id, p1, engine=engine)
    
    # 4. Verifications
    # Victim should be marked inactive
    assert not victim.is_active, "Victim nation should be inactive after losing last populated province"
    assert len(victim.province_ids) == 0, "Victim should have 0 provinces left"
    
    # Attacker should have inherited ALL of them
    assert p1.owner_id == attacker_id
    assert p2.owner_id == attacker_id
    assert p3.owner_id == attacker_id
    
    assert p1_id in attacker.province_ids
    assert p2_id in attacker.province_ids
    assert p3_id in attacker.province_ids
    
    # Verify cleanup (budgets, etc)
    assert victim.total_budget == 0
    assert victim.total_soldiers == 0

if __name__ == "__main__":
    pytest.main([__file__])
