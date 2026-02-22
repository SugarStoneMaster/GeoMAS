import pytest
import sys
import os
import json
import numpy as np
from geomas.world import generate_world
from geomas.schemas.world import WorldState # Updated import
from geomas.db.serialization import (
    convert_numpy,
    serialize_provinces,
    serialize_nations,
    serialize_trust_matrix,
    serialize_relationship_matrix,
    serialize_envelope,
    serialize_world_snapshot,
    deserialize_provinces,
    deserialize_nations,
    deserialize_trust_matrix,
    deserialize_relationship_matrix,
    deserialize_world_snapshot,
)

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


# --- DB SERIALIZATION MODULE TESTS ---

class TestConvertNumpy:
    """Tests for convert_numpy function."""
    
    def test_converts_int64(self):
        """Converts numpy int64 to Python int."""
        result = convert_numpy(np.int64(42))
        assert result == 42
        assert isinstance(result, int)
    
    def test_converts_float64(self):
        """Converts numpy float64 to Python float."""
        result = convert_numpy(np.float64(3.14))
        assert result == pytest.approx(3.14)
        assert isinstance(result, float)
    
    def test_converts_array(self):
        """Converts numpy array to list."""
        arr = np.array([1, 2, 3])
        result = convert_numpy(arr)
        assert result == [1, 2, 3]
        assert isinstance(result, list)
    
    def test_converts_nested_dict(self):
        """Recursively converts nested structures."""
        data = {"a": np.int64(1), "b": {"c": np.float64(2.5)}}
        result = convert_numpy(data)
        assert result == {"a": 1, "b": {"c": 2.5}}
    
    def test_preserves_regular_types(self):
        """Preserves non-numpy types."""
        data = {"x": 10, "y": "hello", "z": [1, 2, 3]}
        result = convert_numpy(data)
        assert result == data


class TestSerializeProvinces:
    """Tests for serialize_provinces function."""
    
    def test_returns_json_string(self):
        """Returns valid JSON string."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        result = serialize_provinces(world.provinces)
        assert isinstance(result, str)
        # Should be valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, list)
    
    def test_all_provinces_serialized(self):
        """All provinces are in the output."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        result = serialize_provinces(world.provinces)
        parsed = json.loads(result)
        assert len(parsed) == len(world.provinces)


class TestSerializeNations:
    """Tests for serialize_nations function."""
    
    def test_returns_json_string(self):
        """Returns valid JSON string."""
        world = generate_world(seed=42, n_cells=50, n_nations=3)
        result = serialize_nations(world.nations)
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 3


class TestSerializeTrustMatrix:
    """Tests for serialize_trust_matrix function."""
    
    def test_returns_json_string(self):
        """Returns valid JSON string."""
        matrix = {"A": {"B": 0.5}, "B": {"A": 0.7}}
        result = serialize_trust_matrix(matrix)
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["A"]["B"] == 0.5


class TestSerializeRelationshipMatrix:
    """Tests for serialize_relationship_matrix function."""
    
    def test_handles_enum_values(self):
        """Converts enum values to strings."""
        from geomas.schemas.world import RelationshipState
        matrix = {"A": {"B": RelationshipState.PEACE}}
        result = serialize_relationship_matrix(matrix)
        parsed = json.loads(result)
        assert parsed["A"]["B"] == "PEACE"


class TestDeserializeProvinces:
    """Tests for deserialize_provinces function."""
    
    def test_roundtrip(self):
        """Can serialize and deserialize back."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        json_str = serialize_provinces(world.provinces)
        result = deserialize_provinces(json_str)
        
        assert len(result) == len(world.provinces)
        for p_id in world.provinces:
            assert result[p_id].terrain == world.provinces[p_id].terrain


class TestDeserializeNations:
    """Tests for deserialize_nations function."""
    
    def test_roundtrip(self):
        """Can serialize and deserialize back."""
        world = generate_world(seed=42, n_cells=50, n_nations=3)
        json_str = serialize_nations(world.nations)
        result = deserialize_nations(json_str)
        
        assert len(result) == len(world.nations)
        for n_id in world.nations:
            assert result[n_id].name == world.nations[n_id].name


class TestDeserializeWorldSnapshot:
    """Tests for deserialize_world_snapshot function."""
    
    def test_full_roundtrip(self):
        """Full world serialize/deserialize roundtrip."""
        world = generate_world(seed=42, n_cells=50, n_nations=3)
        world.turn = 5
        event_dict_1 = {"turn": 5, "event_type": "DIPLOMATIC_MESSAGE", "actors": [], "summary": "Event 1"}
        event_dict_2 = {"turn": 5, "event_type": "DIPLOMATIC_MESSAGE", "actors": [], "summary": "Event 2"}
        world.global_events = [event_dict_1, event_dict_2]
        
        # Serialize
        snapshot = serialize_world_snapshot(world)
        
        # Deserialize
        restored = deserialize_world_snapshot(
            provinces_json=snapshot['provinces_json'],
            nations_json=snapshot['nations_json'],
            trust_matrix_json=snapshot['trust_matrix_json'],
            relationship_matrix_json=snapshot['relationship_matrix_json'],
            turn=world.turn,
            global_events=world.global_events
        )
        
        assert len(restored.provinces) == len(world.provinces)
        assert len(restored.nations) == len(world.nations)
        assert restored.turn == 5
        assert restored.global_events == [event_dict_1, event_dict_2]

