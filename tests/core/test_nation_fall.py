import pytest
import random
from geomas.simulation.engine import SimulationEngine
from geomas.schemas.world import WorldState, NationState, ProvinceState, TerrainType, RelationshipState
from geomas.agents.context.events.schemas import EventType

def test_nation_fall_persistence_and_cleanup():
    # 1. Setup minimal world
    engine = SimulationEngine(map_seed=42, n_cells=100)
    world = engine.world
    
    # Ensure at least 3 nations
    nation_ids = list(world.nations.keys())
    if len(nation_ids) < 3:
        pytest.skip("Need at least 3 nations for this test")
    
    attacker_id = nation_ids[0]
    victim_id = nation_ids[1]
    observer_id = nation_ids[2]
    
    attacker = world.nations[attacker_id]
    victim = world.nations[victim_id]
    observer = world.nations[observer_id]
    
    # 2. Setup guest troops
    # Put victim's troops in attacker's province
    attacker_province_id = attacker.province_ids[0]
    attacker_province = world.provinces[attacker_province_id]
    attacker_province.guest_troops = {victim_id: {"soldiers": 50, "aircraft": 10}}
    victim.total_soldiers += 50
    victim.total_aircraft += 10
    
    # Setup a proposal involving the victim
    observer_nation = world.nations[observer_id]
    observer_nation.pending_proposals.append({
        "id": "test_prop",
        "type": "ALLIANCE",
        "from": victim_id,
        "turn": world.turn,
        "message": "Friendship?"
    })
    
    # 3. Simulate Conquest of Victim's last province
    from geomas.actions.defense.combat import _conquer_province
    
    # Get victim's last province
    victim_provinces = [world.provinces[pid] for pid in victim.province_ids]
    for prov in victim_provinces:
        _conquer_province(world, attacker_id, prov, engine=engine)
    
    # 4. Verifications
    # A. Victim is inactive
    assert not victim.is_active
    
    # B. Resources zeroed
    assert victim.total_soldiers == 0
    assert victim.total_budget == 0
    
    # C. Guest Troops Cleaned up
    assert victim_id not in (attacker_province.guest_troops or {})
    
    # D. Proposals Cleaned up
    assert not any(p["id"] == "test_prop" for p in observer_nation.pending_proposals)
    
    # E. Event Pinned
    fallen_events = [e for e in engine.context_manager.global_events if e.event_type == EventType.NATION_FALLEN]
    assert len(fallen_events) >= 1
    assert fallen_events[0].is_pinned
    assert victim_id in fallen_events[0].actors
    
    # F. Persistence in Prompt (Check Observer's prompt)
    # We simulate many turns to ensure salience aging would normally prune it
    current_turn = world.turn + 20 
    prompt_events = engine.context_manager.get_events_for(observer_id, current_turn=current_turn, use_salience=True)
    
    # The fallen event should be there because it's pinned (salience = 99999)
    assert any("[NATION FALLEN]" in e and victim.name in e for e in prompt_events)
    
    # G. Filtered out from relationships
    from geomas.agents.context.input.base import BaseInputBuilder
    builder = BaseInputBuilder(world)
    rel_section = builder._build_relationships(observer_id)
    assert victim.name not in rel_section
    assert attacker.name in rel_section

if __name__ == "__main__":
    pytest.main([__file__])
