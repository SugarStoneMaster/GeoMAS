"""
Tests for Genesis Database.
"""

import pytest
import tempfile
import os
from geomas.db.genesis import GenesisDB


class TestGenesisDB:
    """Tests for GenesisDB class."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "genesis.duckdb")
            db = GenesisDB(db_path)
            db.initialize(seed=42, years=50, n_nations=5)
            yield db
            db.close()
    
    def test_create_and_initialize(self, temp_db):
        """Can create and initialize database."""
        info = temp_db.get_genesis_info()
        
        assert info is not None
        assert info["seed"] == 42
        assert info["years"] == 50
        assert info["n_nations"] == 5
    
    def test_save_and_load_event(self, temp_db):
        """Can save and retrieve a single event."""
        temp_db.save_event(
            event_id=1,
            year=10,
            tag="ALLIANCE",
            description="Nation A allied with Nation B",
            nation_a="nation_a",
            nation_b="nation_b"
        )
        
        events = temp_db.get_all_events()
        
        assert len(events) == 1
        assert events[0]["year"] == 10
        assert events[0]["tag"] == "ALLIANCE"
        assert events[0]["nation_a"] == "nation_a"
    
    def test_save_events_batch(self, temp_db):
        """Can save multiple events at once."""
        events = [
            (1, 5, "CONFLICT", "Border skirmish", "nation_a", "nation_b"),
            (2, 10, "TRADE", "Trade agreement", "nation_a", "nation_c"),
            (3, 15, "ALLIANCE", "Alliance formed", "nation_b", "nation_c"),
        ]
        
        temp_db.save_events_batch(events)
        
        all_events = temp_db.get_all_events()
        assert len(all_events) == 3
    
    def test_get_events_for_nation(self, temp_db):
        """Can filter events by nation."""
        events = [
            (1, 5, "CONFLICT", "A vs B", "nation_a", "nation_b"),
            (2, 10, "TRADE", "A with C", "nation_a", "nation_c"),
            (3, 15, "ALLIANCE", "B with C", "nation_b", "nation_c"),
        ]
        temp_db.save_events_batch(events)
        
        nation_a_events = temp_db.get_events_for_nation("nation_a")
        
        assert len(nation_a_events) == 2
        assert all(e["nation_a"] == "nation_a" or e["nation_b"] == "nation_a" for e in nation_a_events)
    
    def test_get_events_by_tag(self, temp_db):
        """Can filter events by tag."""
        events = [
            (1, 5, "CONFLICT", "Fight 1", "a", "b"),
            (2, 10, "CONFLICT", "Fight 2", "c", "d"),
            (3, 15, "TRADE", "Deal", "a", "c"),
        ]
        temp_db.save_events_batch(events)
        
        conflicts = temp_db.get_events_by_tag("CONFLICT")
        
        assert len(conflicts) == 2
        assert all(e["tag"] == "CONFLICT" for e in conflicts)
    
    def test_save_and_load_trust_matrix(self, temp_db):
        """Can save and retrieve trust matrix."""
        trust = {
            "nation_a": {"nation_b": 75.0, "nation_c": 30.0},
            "nation_b": {"nation_a": 75.0, "nation_c": 50.0},
            "nation_c": {"nation_a": 30.0, "nation_b": 50.0},
        }
        
        temp_db.save_trust_matrix(trust)
        loaded = temp_db.get_trust_matrix()
        
        assert loaded["nation_a"]["nation_b"] == 75.0
        assert loaded["nation_c"]["nation_a"] == 30.0
    
    def test_save_and_load_alliances(self, temp_db):
        """Can save and retrieve alliances."""
        alliances = {
            ("nation_a", "nation_b"): True,
            ("nation_c", "nation_d"): True,
        }
        
        temp_db.save_alliances(alliances)
        loaded = temp_db.get_alliances()
        
        assert len(loaded) == 2
        assert ("nation_a", "nation_b") in loaded
    
    def test_event_count(self, temp_db):
        """Event count is tracked correctly."""
        assert temp_db.event_count() == 0
        
        events = [
            (1, 5, "CONFLICT", "Fight", "a", "b"),
            (2, 10, "TRADE", "Deal", "c", "d"),
        ]
        temp_db.save_events_batch(events)
        
        assert temp_db.event_count() == 2
    
    def test_context_manager(self, temp_db):
        """Context manager works correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "ctx_test.duckdb")
            
            with GenesisDB(db_path) as db:
                db.initialize(seed=99, years=25, n_nations=3)
                db.save_event(1, 5, "TEST", "Test event", "a", "b")
            
            # Reopen and verify
            with GenesisDB(db_path) as db:
                assert db.event_count() == 1
