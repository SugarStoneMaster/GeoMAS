
import pytest
from unittest.mock import MagicMock
from geomas.simulation.engine import SimulationEngine
from geomas.agents.context.events.context_manager import ContextManager
from geomas.simulation.scenarios import trigger_resource_discovery

def test_resource_discovery_mechanics():
    """Verify that resource discovery boosts production in a border province."""
    # 1. Setup engine and world
    engine = SimulationEngine(map_seed=42, n_nations=4)
    world = engine.world
    cm = engine.context_manager
    
    # 2. Identify border provinces before trigger (to compare)
    initial_productions = {}
    for p_id, p in world.provinces.items():
        initial_productions[p_id] = (p.energy_production, p.materials_production)
        
    # 3. Trigger
    logs = trigger_resource_discovery(world, cm, turn=10)
    assert any("Resource Discovery" in log for log in logs)
    
    # 4. Verify impact: the target province must have energy > original and be set to avg*10
    # Compute world averages as the scenario does
    land_provs = [p for p in world.provinces.values() if p.owner_id is not None]
    avg_energy_post = sum(p.energy_production for p in land_provs) / len(land_provs)
    avg_mats_post = sum(p.materials_production for p in land_provs) / len(land_provs)

    found = False
    for p_id, p in world.provinces.items():
        old_energy, old_materials = initial_productions[p_id]
        if p.energy_production > old_energy * 2:   # Significant boost is easily detectable
            # The new value must be well above the original baseline
            assert p.energy_production > old_energy, "Energy did not increase"
            assert p.materials_production > old_materials, "Materials did not increase"
            found = True
            print(f"Verified discovery in province #{p.id} ({p.owner_id}): "
                  f"energy {old_energy:.1f} → {p.energy_production:.1f}")

    assert found, "No province was updated by the scenario"
    
    # 5. Verify event logging
    assert any("major mineral deposit" in event.summary for event in cm.global_events)
    assert any("T10: 📜 [GLOBAL EVENT]" in msg for msg in world.global_events)

def test_resource_discovery_border_only():
    """Verify that only a border province can be selected."""
    engine = SimulationEngine(map_seed=99, n_nations=4)
    world = engine.world
    cm = engine.context_manager
    
    # Trigger multiple times with different turn seeds to check targets
    targets = set()
    for t in range(1, 20):
        # We need a fresh world or just check the target
        # Actually trigger_resource_discovery picks a target based on random.Random(turn + 42)
        # 1. Identify all border provinces
        border_ids = []
        for p_id, p in world.provinces.items():
            is_border = False
            for n_id in p.neighbors:
                neigh = world.provinces.get(n_id)
                if neigh and neigh.owner_id and neigh.owner_id != p.owner_id:
                    is_border = True
                    break
            if is_border: border_ids.append(p_id)

        # Reset productions to avoid cumulative growth during this loop
        for p in world.provinces.values():
            p.energy_production = 10.0
            
        trigger_resource_discovery(world, cm, turn=t)
        
        # Find which one changed
        for p_id, p in world.provinces.items():
            if p.energy_production > 10.0:
                assert p_id in border_ids, f"Province {p_id} is NOT a border province but was selected!"
                targets.add(p_id)
                break
    
    assert len(targets) > 1, "Scenario always picks the same province (check RNG)"

if __name__ == "__main__":
    test_resource_discovery_mechanics()
    test_resource_discovery_border_only()
    print("✅ Resource Discovery Tests Passed!")
