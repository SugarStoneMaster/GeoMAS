"""
Tests for Database Package.

Validates DuckDB persistence, serialization, and query operations.
"""

import pytest
import tempfile
import os
from pathlib import Path

from geomas.db import SimulationDB
from geomas.db.serialization import (
    serialize_provinces,
    serialize_nations,
    serialize_trust_matrix,
    serialize_relationship_matrix,
    serialize_world_snapshot,
    serialize_envelope,
    convert_numpy
)
from geomas.world import generate_world
from conftest import create_test_envelope
from geomas.agents.schemas import GlobalStrategy


class TestSimulationDB:
    """Tests for SimulationDB connection and CRUD operations."""
    
    @pytest.fixture
    def db_path(self):
        """Create a temporary database file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield os.path.join(tmpdir, "test_simulation.duckdb")
    
    @pytest.fixture
    def initialized_db(self, db_path):
        """Create and initialize a test database."""
        db = SimulationDB(db_path)
        db.initialize(genesis_seed=42, simulation_seed=99, n_cells=100)
        yield db
        db.close()
    
    def test_create_database(self, db_path):
        """Database file is created on first connection."""
        db = SimulationDB(db_path)
        db.initialize(genesis_seed=42, simulation_seed=99, n_cells=100)
        
        assert Path(db_path).exists()
        db.close()
    
    def test_simulation_metadata(self, initialized_db):
        """Simulation metadata is stored correctly."""
        info = initialized_db.get_simulation_info()
        
        assert info is not None
        assert info["genesis_seed"] == 42
        assert info["simulation_seed"] == 99
        assert info["n_cells"] == 100
        assert info["total_turns"] == 0
    
    def test_save_and_load_snapshot(self, initialized_db):
        """Snapshots can be saved and loaded."""
        provinces_json = '[{"id": 1, "owner_id": "nation_1"}]'
        nations_json = '[{"id": "nation_1", "name": "Test Nation"}]'
        trust_json = '{"nation_1:nation_2": 50}'
        relations_json = '{"nation_1:nation_2": "PEACE"}'
        world_events_json = '["Event 1"]'
        memory_json = '{"relationship_summaries": {}}'
        
        initialized_db.save_snapshot(
            turn=1,
            provinces_json=provinces_json,
            nations_json=nations_json,
            trust_matrix_json=trust_json,
            relationship_matrix_json=relations_json,
            world_events_json=world_events_json,
            memory_json=memory_json
        )
        
        snapshot = initialized_db.load_snapshot(1)
        
        assert snapshot is not None
        assert snapshot["provinces_json"] is not None
        assert snapshot["nations_json"] is not None
        assert snapshot["world_events_json"] == '["Event 1"]'
        assert snapshot["memory_json"] == '{"relationship_summaries": {}}'
    
    def test_save_and_load_envelope(self, initialized_db):
        """Envelopes can be saved and loaded."""
        envelope_json = '{"turn": 1, "sender_id": "nation_1"}'
        
        initialized_db.save_envelope(turn=1, nation_id="nation_1", envelope_json=envelope_json)
        
        envelopes = initialized_db.load_envelopes(1)
        
        assert len(envelopes) == 1
        assert envelopes[0][0] == "nation_1"
    
    def test_save_and_load_behavior(self, initialized_db):
        """Behavior metrics can be saved and loaded."""
        initialized_db.save_behavior(
            turn=1,
            nation_id="nation_1",
            deception_total=0.5,
            deception_defense=0.3,
            deception_economic=0.6,
            deception_foreign=0.4,
            coherence_score=0.8,
            global_strategy="COALITION_BUILDER"
        )
        
        behaviors = initialized_db.load_behaviors(1)
        
        assert len(behaviors) == 1
        assert behaviors[0]["nation_id"] == "nation_1"
        assert behaviors[0]["deception_total"] == pytest.approx(0.5)
        assert behaviors[0]["coherence_score"] == pytest.approx(0.8)
    
    def test_behavior_timeline(self, initialized_db):
        """Behavior timeline query returns DataFrame."""
        # Insert multiple turns
        for turn in range(1, 4):
            initialized_db.save_behavior(
                turn=turn,
                nation_id="nation_1",
                deception_total=0.1 * turn,
                deception_defense=0.0,
                deception_economic=0.0,
                deception_foreign=0.0,
                coherence_score=0.9,
                global_strategy="COALITION_BUILDER"
            )
        
        df = initialized_db.get_behavior_timeline("nation_1")
        
        assert len(df) == 3
        assert list(df["turn"]) == [1, 2, 3]
    
    def test_context_manager(self, db_path):
        """Database works as context manager."""
        with SimulationDB(db_path) as db:
            db.initialize(genesis_seed=1, simulation_seed=2, n_cells=50)
            info = db.get_simulation_info()
            assert info["genesis_seed"] == 1
    
    def test_load_nonexistent_snapshot(self, initialized_db):
        """Loading nonexistent snapshot returns None."""
        snapshot = initialized_db.load_snapshot(999)
        assert snapshot is None

    def test_token_usage(self, initialized_db):
        """Token usage can be saved and retrieved as DataFrame."""
        initialized_db.save_token_usage(
            turn=1,
            nation_id="nation_1",
            agent_type="President",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            model="gpt-4",
            cost=0.005
        )
        
        df = initialized_db.get_token_timeline("nation_1")
        assert len(df) == 1
        assert df.iloc[0]["total_tokens"] == 150
        assert df.iloc[0]["cost"] == pytest.approx(0.005)
        
        # Test global timeline
        df_all = initialized_db.get_token_timeline()
        assert len(df_all) == 1
        assert df_all.iloc[0]["total_cost"] == pytest.approx(0.005)


class TestSerialization:
    """Tests for serialization helpers."""
    
    def test_convert_numpy_integer(self):
        """Numpy integers are converted to Python int."""
        import numpy as np
        assert convert_numpy(np.int64(42)) == 42
        assert isinstance(convert_numpy(np.int64(42)), int)
    
    def test_convert_numpy_float(self):
        """Numpy floats are converted to Python float."""
        import numpy as np
        assert convert_numpy(np.float64(3.14)) == pytest.approx(3.14)
        assert isinstance(convert_numpy(np.float64(3.14)), float)
    
    def test_convert_numpy_nested(self):
        """Nested structures with numpy types are converted."""
        import numpy as np
        data = {
            "list": [np.int64(1), np.int64(2)],
            "nested": {"value": np.float64(3.14)}
        }
        result = convert_numpy(data)
        
        assert result["list"] == [1, 2]
        assert result["nested"]["value"] == pytest.approx(3.14)
    
    def test_serialize_world_snapshot(self):
        """WorldState can be serialized to JSON strings."""
        world = generate_world(seed=42, n_cells=50)
        
        snapshot = serialize_world_snapshot(world)
        
        assert "provinces_json" in snapshot
        assert "nations_json" in snapshot
        assert "trust_matrix_json" in snapshot
        assert "relationship_matrix_json" in snapshot
        
        # Verify valid JSON
        import json
        json.loads(snapshot["provinces_json"])
        json.loads(snapshot["nations_json"])
    
    def test_serialize_envelope(self):
        """CountryEnvelope can be serialized to JSON."""
        envelope = create_test_envelope("nation_1")
        
        json_str = serialize_envelope(envelope)
        
        import json
        data = json.loads(json_str)
        assert data["sender_id"] == "nation_1"


class TestIntegration:
    """Integration tests for DB with real world data."""
    
    @pytest.fixture
    def db_with_world(self):
        """Create DB and save a real world snapshot."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "integration.duckdb")
            db = SimulationDB(db_path)
            db.initialize(genesis_seed=42, simulation_seed=99, n_cells=100)
            
            world = generate_world(seed=42, n_cells=100)
            snapshot = serialize_world_snapshot(world)
            
            db.save_snapshot(
                turn=0,
                **snapshot
            )
            
            yield db, world
            db.close()
    
    def test_roundtrip_world_snapshot(self, db_with_world):
        """World snapshot can be saved and loaded."""
        db, original_world = db_with_world
        
        snapshot = db.load_snapshot(0)
        
        assert snapshot is not None
        
        import json
        provinces = json.loads(snapshot["provinces_json"]) if isinstance(snapshot["provinces_json"], str) else snapshot["provinces_json"]
        nations = json.loads(snapshot["nations_json"]) if isinstance(snapshot["nations_json"], str) else snapshot["nations_json"]
        
        # Verify counts match
        assert len(provinces) == len(original_world.provinces)
        assert len(nations) == len(original_world.nations)
    
    def test_load_world_at_turn(self, db_with_world):
        """WorldState can be fully reconstructed from DB."""
        db, original_world = db_with_world
        
        loaded_world = db.load_world_at_turn(0)
        
        assert loaded_world is not None
        assert loaded_world.turn == 0
        assert len(loaded_world.provinces) == len(original_world.provinces)
        assert len(loaded_world.nations) == len(original_world.nations)
        
        # Verify a province was correctly reconstructed
        original_province = list(original_world.provinces.values())[0]
        loaded_province = loaded_world.provinces[original_province.id]
        assert loaded_province.terrain == original_province.terrain
        assert loaded_province.population == original_province.population


class TestEngineIntegration:
    """Tests for SimulationEngine DB integration."""
    
    def test_engine_with_db_creates_initial_snapshot(self):
        """SimulationEngine saves turn 0 snapshot on init."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "sim.duckdb")
            
            # Create engine with DB
            from geomas.simulation import SimulationEngine
            engine = SimulationEngine(
                map_seed=42,
                history_seed=99,
                n_cells=50,
                db_path=db_path
            )
            
            # Verify turn 1 was saved
            snapshot = engine.db.load_snapshot(1)
            assert snapshot is not None
            
            # Verify world can be loaded
            world = engine.db.load_world_at_turn(1)
            assert world is not None
            assert world.turn == 1
            
            engine.close()

