
import pytest
import re
from geomas.schemas.world import WorldState, NationState, ProvinceState, TerrainType
from geomas.world.genesis import GenesisEngine
from geomas.agents.context.events import ContextManager
from geomas.agents.context.events.schemas import EventType

def test_genesis_mini_fixes():
    # Setup world
    world = WorldState()
    world.nations["N1"] = NationState(id="N1", name="Nation 1", color="#FF0000")
    world.nations["N2"] = NationState(id="N2", name="Nation 2", color="#0000FF")
    # Add dummy coordinates and other required fields for Pydantic satisfaction
    world.provinces[1] = ProvinceState(id=1, owner_id="N1", terrain=TerrainType.LAND, neighbors=[2], coordinates=(0,0))
    world.provinces[2] = ProvinceState(id=2, owner_id="N2", terrain=TerrainType.LAND, neighbors=[1], coordinates=(1,1))
    world.nations["N1"].province_ids = [1]
    world.nations["N2"].province_ids = [2]
    
    # Run Genesis
    genesis = GenesisEngine(world, seed=42)
    genesis.initialize_history(years=100) # Mor history to ensure enough events
    
    # Verify events in world
    assert len(world.global_events) > 0
    print(f"Total Genesis events: {len(world.global_events)}")
    
    for e in world.global_events:
        assert "[History Year" in e["summary"]
             
    # Verify context manager selection
    cm = ContextManager()
    cm.initialize_from_world(world)
    
    # Ask for events at Turn 1, limited to 5
    max_ev = 5
    events = cm.get_events_for("N1", current_turn=1, max_events=max_ev)
    
    print("\nSelected Events in Prompt:")
    years_in_prompt = []
    for e in events:
        print(f"  {e}")
        match = re.search(r"Year (\d+)", e)
        if match:
            years_in_prompt.append(int(match.group(1)))
            
    # Get all possible years from the world
    all_years = []
    for e in world.global_events:
        match = re.search(r"Year (\d+)", e["summary"])
        if match:
            all_years.append(int(match.group(1)))
    
    # Selection should prioritize higher indices (ties on Turn 0)
    # The actual events in prompt should correspond to the LATEST arrivals in global_events
    all_years_sorted = all_years[-max_ev:] # LAST ones added
    
    print(f"Expected latest years: {all_years_sorted}")
    print(f"Actual years in prompt: {years_in_prompt}")
    
    # The prompt returns them sorted chronologically ASCENDING
    assert years_in_prompt == sorted(all_years_sorted)
    print("\nSUCCESS: Genesis Mini-Fixes Verified!")

if __name__ == "__main__":
    test_genesis_mini_fixes()
