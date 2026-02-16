
import pytest
from geomas.world.generation.generator import generate_world
from geomas.schemas.world import TerrainType

def test_initial_units_distribution():
    """
    Verify that nations start with a mix of unit types, not just soldiers.
    """
    # Use a large enough map to ensure coastal provinces exist
    world = generate_world(seed=42, n_cells=300, n_nations=4)
    
    for nation_id, nation in world.nations.items():
        print(f"Checking {nation_id}: Soldiers {nation.total_soldiers}, Air {nation.total_aircraft}, Navy {nation.total_navy}")
        
        # 1. Soldiers must exist
        assert nation.total_soldiers > 0, f"{nation_id} started with 0 soldiers!"
        
        # 2. Aircraft must exist (approx 5% of soldiers logic)
        # Even small nations should have some if they have enough soldiers
        if nation.total_soldiers > 50:
             assert nation.total_aircraft > 0, f"{nation_id} has soldiers but 0 aircraft!"
             
        # 3. Navy check
        # Check if nation has any coastal provinces
        has_coast = any(
            world.provinces[p_id].terrain == TerrainType.COASTAL 
            for p_id in nation.province_ids
        )
        
        if has_coast and nation.total_soldiers > 50:
            assert nation.total_navy > 0, f"{nation_id} is coastal but has 0 navy!"
        elif not has_coast:
            assert nation.total_navy == 0, f"{nation_id} is landlocked but has navy!"

def test_province_unit_assignment():
    """Verify units are assigned at province level."""
    world = generate_world(seed=123, n_cells=100, n_nations=2)
    
    for p_id, province in world.provinces.items():
        if province.owner_id is None:
            continue
            
        # If soldiers present, check consistent ratios
        if province.soldiers > 0:
            # Aircraft check
            expected_aircraft = int(province.soldiers * 0.05)
            assert province.aircraft == expected_aircraft
            
            # Navy check
            if province.terrain == TerrainType.COASTAL:
                expected_navy = int(province.soldiers * 0.10)
                assert province.navy == expected_navy
            else:
                assert province.navy == 0
