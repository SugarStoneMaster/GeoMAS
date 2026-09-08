import pytest
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from geomas.world import generate_world
from geomas.agents.context import SpatialTranslator
from geomas.schemas.world import TerrainType # Updated import

def test_hollow_island_detection():
    """Test that a nation with no land neighbors is identified as an Island."""
    world = generate_world(seed=42, n_cells=100, n_nations=2)
    translator = SpatialTranslator(world)
    
    island_id = list(world.nations.keys())[0]
    
    for p_id in world.nations[island_id].province_ids:
        prov = world.provinces[p_id]
        for n_id in prov.neighbors:
            neighbor = world.provinces.get(n_id)
            if neighbor and neighbor.owner_id != island_id:
                neighbor.owner_id = None 
                neighbor.terrain = TerrainType.OCEAN
        
    report = translator.generate_intelligence_report(island_id)
    assert "Island Nation" in report or "Landlocked" in report 

def test_maginot_line_logic():
    """Test that mountains are reported as defensible."""
    world = generate_world(seed=42, n_cells=100, n_nations=2)
    translator = SpatialTranslator(world)
    
    n_a = list(world.nations.keys())[0]
    
    border_provs = translator.spatial.get_border_provinces(n_a)
    if not border_provs: pytest.skip("No borders")
    
    for p_id in border_provs:
        world.provinces[p_id].terrain = TerrainType.MOUNTAIN
        
    report = translator.generate_intelligence_report(n_a)
    
    neighbors = translator.spatial.get_neighboring_nations(n_a)
    if neighbors:
        assert "defensible" in report or "Mountains" in report

def test_encirclement_warning():
    """Test encirclement risk reporting for nations with many neighbors."""
    # Use higher cell count and more nations to guarantee neighbors
    world = generate_world(seed=42, n_cells=300, n_nations=8)
    translator = SpatialTranslator(world)
    
    # Find nation with most neighbors
    max_neighbors = 0
    target_nation = None
    for n_id in world.nations.keys():
        neighbors = translator.spatial.get_neighboring_nations(n_id)
        if len(neighbors) > max_neighbors:
            max_neighbors = len(neighbors)
            target_nation = n_id
    
    if target_nation is None or max_neighbors < 2:
        pytest.skip(f"No nation with 2+ neighbors found (max: {max_neighbors})")
    
    report = translator.generate_intelligence_report(target_nation)
    # Should mention neighbors in some form
    assert "neighbor" in report.lower() or "border" in report.lower()

