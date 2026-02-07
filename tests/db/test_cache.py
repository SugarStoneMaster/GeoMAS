"""
Tests for In-Memory Turn Cache.
"""

import pytest
from copy import deepcopy
from geomas.db.cache import TurnCache, TurnSnapshot
from geomas.schemas.world import WorldState, ProvinceState, NationState, TerrainType
from geomas.agents.schemas import CountryEnvelope, GlobalStrategy, DefenseIntentType, EconomicIntentType, ForeignIntentType


@pytest.fixture
def sample_world():
    """Create a minimal world for testing."""
    return WorldState(
        turn=0,
        provinces={
            0: ProvinceState(id=0, coordinates=(0.0, 0.0), terrain=TerrainType.LAND),
            1: ProvinceState(id=1, coordinates=(1.0, 0.0), terrain=TerrainType.COASTAL),
        },
        nations={
            "nation_a": NationState(id="nation_a", name="Nation A", color="#FF0000", province_ids=[0]),
            "nation_b": NationState(id="nation_b", name="Nation B", color="#00FF00", province_ids=[1]),
        },
        trust_matrix={"nation_a": {"nation_b": 50.0}, "nation_b": {"nation_a": 50.0}},
        relationship_matrix={"nation_a": {"nation_b": "PEACE"}, "nation_b": {"nation_a": "PEACE"}}
    )


@pytest.fixture
def sample_envelope():
    """Create a sample envelope using conftest helper."""
    from tests.conftest import create_test_envelope
    return create_test_envelope("nation_a", turn=1)


class TestTurnCache:
    """Tests for TurnCache class."""
    
    def test_create_empty_cache(self):
        """Cache starts empty."""
        cache = TurnCache(max_turns=10)
        
        assert len(cache) == 0
        assert cache.current_turn == 0
        assert cache.oldest_turn == 0
    
    def test_add_and_retrieve_turn(self, sample_world, sample_envelope):
        """Can add and retrieve a turn."""
        cache = TurnCache(max_turns=10)
        
        cache.add_turn(
            turn=1,
            world_state=sample_world,
            envelopes=[sample_envelope],
            behaviors={"nation_a": {"deception_total": 0.1}}
        )
        
        assert len(cache) == 1
        assert 1 in cache
        
        snapshot = cache.get_turn(1)
        assert snapshot is not None
        assert snapshot.turn == 1
        assert len(snapshot.envelopes) == 1
    
    def test_get_world_at_turn(self, sample_world):
        """Can retrieve WorldState for a turn."""
        cache = TurnCache(max_turns=10)
        sample_world.turn = 5
        
        cache.add_turn(turn=5, world_state=sample_world, envelopes=[])
        
        world = cache.get_world_at_turn(5)
        assert world is not None
        assert world.turn == 5
        assert len(world.nations) == 2
    
    def test_world_is_deep_copied(self, sample_world):
        """WorldState is deep copied to prevent mutation."""
        cache = TurnCache(max_turns=10)
        
        cache.add_turn(turn=1, world_state=sample_world, envelopes=[])
        
        # Modify original
        sample_world.turn = 999
        sample_world.nations["nation_a"].total_budget = 99999
        
        # Cached version should be unchanged
        cached = cache.get_world_at_turn(1)
        assert cached.turn == 0
        assert cached.nations["nation_a"].total_budget == 0.0
    
    def test_max_capacity_eviction(self, sample_world):
        """Oldest turns are evicted when capacity reached."""
        cache = TurnCache(max_turns=3)
        
        for turn in range(1, 6):  # Add turns 1-5
            world = deepcopy(sample_world)
            world.turn = turn
            cache.add_turn(turn=turn, world_state=world, envelopes=[])
        
        assert len(cache) == 3
        assert cache.oldest_turn == 3
        assert cache.current_turn == 5
        
        # Early turns should be evicted
        assert 1 not in cache
        assert 2 not in cache
        
        # Recent turns should be present
        assert 3 in cache
        assert 4 in cache
        assert 5 in cache
    
    def test_get_recent_turns(self, sample_world):
        """Can retrieve N most recent turns."""
        cache = TurnCache(max_turns=10)
        
        for turn in range(1, 6):
            world = deepcopy(sample_world)
            world.turn = turn
            cache.add_turn(turn=turn, world_state=world, envelopes=[])
        
        recent = cache.get_recent_turns(3)
        
        assert len(recent) == 3
        assert recent[0].turn == 5  # Newest first
        assert recent[1].turn == 4
        assert recent[2].turn == 3
    
    def test_get_envelopes_for_nation(self, sample_world):
        """Can retrieve all envelopes for a specific nation."""
        from tests.conftest import create_test_envelope
        cache = TurnCache(max_turns=10)
        
        # Add 3 turns with envelopes
        for turn in range(1, 4):
            envelope = create_test_envelope(
                "nation_a", 
                turn=turn,
                public_statement=f"Turn {turn}"
            )
            cache.add_turn(turn=turn, world_state=sample_world, envelopes=[envelope])
        
        envelopes = cache.get_envelopes_for_nation("nation_a")
        
        assert len(envelopes) == 3
        assert envelopes[0].public_statement == "Turn 3"  # Newest first
        assert envelopes[2].public_statement == "Turn 1"  # Oldest last
    
    def test_get_behaviors_for_nation(self, sample_world):
        """Can retrieve behavior history for a nation."""
        cache = TurnCache(max_turns=10)
        
        for turn in range(1, 4):
            cache.add_turn(
                turn=turn,
                world_state=sample_world,
                envelopes=[],
                behaviors={
                    "nation_a": {"deception_total": turn * 0.1, "coherence_score": 0.9}
                }
            )
        
        behaviors = cache.get_behaviors_for_nation("nation_a")
        
        assert len(behaviors) == 3
        assert behaviors[0]["turn"] == 3
        assert abs(behaviors[0]["deception_total"] - 0.3) < 0.001
        assert behaviors[2]["turn"] == 1
    
    def test_clear_cache(self, sample_world):
        """Can clear all cached data."""
        cache = TurnCache(max_turns=10)
        
        cache.add_turn(turn=1, world_state=sample_world, envelopes=[])
        cache.add_turn(turn=2, world_state=sample_world, envelopes=[])
        
        cache.clear()
        
        assert len(cache) == 0
        assert 1 not in cache
        assert 2 not in cache
    
    def test_nonexistent_turn_returns_none(self):
        """Querying nonexistent turn returns None."""
        cache = TurnCache(max_turns=10)
        
        assert cache.get_turn(99) is None
        assert cache.get_world_at_turn(99) is None
        assert cache.get_envelopes_at_turn(99) == []
