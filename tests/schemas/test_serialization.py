import pytest
import sys
import os
import json
from geomas.world import generate_world
from geomas.schemas.world import WorldState # Updated import

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

def test_world_state_serialization():
    """Test that WorldState can be saved to JSON and reloaded."""
    world = generate_world(seed=42, n_cells=50, n_nations=2)
    
    # 1. Serialize to JSON string (Pydantic v2 syntax)
    json_str = world.model_dump_json()
    assert isinstance(json_str, str)
    assert "provinces" in json_str
    assert "trust_matrix" in json_str
    
    # 2. Deserialize back to Object (Pydantic v2 syntax)
    loaded_world = WorldState.model_validate_json(json_str)
    
    # 3. Verify Integrity
    assert len(loaded_world.nations) == len(world.nations)
    assert loaded_world.turn == world.turn
    
    # Check deep structure
    n_id = list(world.nations.keys())[0]
    assert loaded_world.nations[n_id].name == world.nations[n_id].name
    
    # Check Enum serialization
    p_id = list(world.provinces.keys())[0]
    assert loaded_world.provinces[p_id].terrain == world.provinces[p_id].terrain

def test_file_io(tmp_path):
    """Test saving to a real file."""
    world = generate_world(seed=99, n_cells=50, n_nations=2)
    file_path = tmp_path / "world_save.json"
    
    # Save
    with open(file_path, "w") as f:
        f.write(world.model_dump_json())
        
    # Load
    with open(file_path, "r") as f:
        loaded_world = WorldState.model_validate_json(f.read())
        
    assert loaded_world.nations.keys() == world.nations.keys()
