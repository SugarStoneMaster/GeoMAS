import pytest
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from geomas.world.map_engine import generate_world
from geomas.world.spatial_manager import SpatialManager
from geomas.world.spatial_translator import SpatialTranslator
from geomas.schemas.world import WorldState, TerrainType # Updated import

def test_determinism():
    """Test that generating the world with the same seed produces identical results."""
    world1 = generate_world(seed=42, n_cells=100, n_nations=5)
    world2 = generate_world(seed=42, n_cells=100, n_nations=5)
    
    assert len(world1.provinces) == len(world2.provinces)
    assert len(world1.nations) == len(world2.nations)
    
    first_id = list(world1.provinces.keys())[0]
    p1 = world1.provinces[first_id]
    p2 = world2.provinces[first_id]
    assert p1.coordinates == p2.coordinates
    assert p1.owner_id == p2.owner_id

def test_spatial_manager_connectivity():
    """Test that the spatial graph is built correctly."""
    world = generate_world(seed=123, n_cells=200, n_nations=5)
    manager = SpatialManager(world)
    
    assert len(manager.graph.nodes) == len(world.provinces)
    
    p_id = list(world.provinces.keys())[0]
    if world.provinces[p_id].neighbors:
        neighbor_id = world.provinces[p_id].neighbors[0]
        if neighbor_id in world.provinces:
            path = manager.get_shortest_path(p_id, neighbor_id)
            assert path == [p_id, neighbor_id]
            assert manager.get_path_length(p_id, neighbor_id) == 1

def test_spatial_translator_logic():
    """Test the semantic translation logic."""
    world = generate_world(seed=999, n_cells=300, n_nations=5)
    translator = SpatialTranslator(world)
    
    nation_id = list(world.nations.keys())[0]
    report = translator.generate_intelligence_report(nation_id)
    
    assert isinstance(report, str)
    assert "GEOGRAPHY:" in report
    assert "BORDERS & THREATS:" in report
    
    nation = world.nations[nation_id]
    manager = SpatialManager(world)
    coastal = manager.get_coastal_provinces(nation_id)
    
    if not coastal:
        assert "Landlocked" in report

def test_resource_allocation():
    """Test that resources are allocated and not zero."""
    world = generate_world(seed=55, n_cells=100, n_nations=3)
    
    for p in world.provinces.values():
        if p.terrain != TerrainType.OCEAN:
            assert p.resources.food > 0
            assert p.resources.energy > 0
            assert p.resources.materials > 0
