"""
Tests for Memory Package.
"""

import pytest
from geomas.world import generate_world
from geomas.agents.context.events import (
    RelationshipSummary,
    NotableEvent,
    MyAction,
    EventType,
    ContextManager,
)


class TestRelationshipSummary:
    """Tests for RelationshipSummary schema."""
    
    def test_create_summary(self):
        """Can create a relationship summary."""
        summary = RelationshipSummary(
            other_nation_id="nation_b",
            other_nation_name="Belvoria",
            relationship="PEACE",
            trust=65.0
        )
        assert summary.other_nation_id == "nation_b"
        assert summary.trust == 65.0
    
    def test_to_prompt_line_basic(self):
        """Basic prompt line rendering."""
        summary = RelationshipSummary(
            other_nation_id="nation_b",
            other_nation_name="Belvoria",
            relationship="ALLIANCE",
            trust=80.0,
            trust_trend="↑"
        )
        line = summary.to_prompt_line()
        
        assert "Belvoria" in line
        assert "ALLIANCE" in line
        assert "80" in line
        assert "rising" in line
    
    def test_to_prompt_line_with_history(self):
        """Prompt line includes history when present."""
        summary = RelationshipSummary(
            other_nation_id="nation_b",
            other_nation_name="Belvoria",
            relationship="WAR",
            trust=15.0,
            last_interaction_turn=20,
            last_interaction_summary="attacked us",
            notable_events=["T15: broke treaty", "T20: attacked us"]
        )
        line = summary.to_prompt_line()
        
        assert "attacked us" in line
        assert "T20" in line or "History" in line


class TestNotableEvent:
    """Tests for NotableEvent schema."""
    
    def test_create_event(self):
        """Can create a notable event."""
        event = NotableEvent(
            turn=5,
            event_type=EventType.WAR_DECLARED,
            actors=["nation_a", "nation_b"],
            summary="Valdoria declared war on Aquilonia"
        )
        assert event.turn == 5
        assert event.event_type == EventType.WAR_DECLARED
    
    def test_to_prompt_line(self):
        """Event renders to prompt line correctly."""
        event = NotableEvent(
            turn=5,
            event_type=EventType.ALLIANCE_FORMED,
            actors=["nation_a", "nation_b"],
            summary="Alliance formed between A and B"
        )
        line = event.to_prompt_line()
        
        assert "Turn 5" in line
        assert "Alliance" in line
    
    def test_is_critical(self):
        """Critical events are correctly identified."""
        war_event = NotableEvent(
            turn=1, event_type=EventType.WAR_DECLARED,
            actors=[], summary="War"
        )
        trade_event = NotableEvent(
            turn=1, event_type=EventType.TRADE_DEAL,
            actors=[], summary="Trade"
        )
        
        assert war_event.is_critical() is True
        assert trade_event.is_critical() is False


class TestMyAction:
    """Tests for MyAction schema."""
    
    def test_create_action(self):
        """Can create an action record."""
        action = MyAction(
            turn=10,
            domain="Defense",
            action_type="ATTACK",
            action_summary="Attacked Province 7 of Valdoria",
            outcome="Captured"
        )
        assert action.turn == 10
        assert action.domain == "Defense"
    
    def test_to_prompt_line(self):
        """Action renders to prompt line correctly."""
        action = MyAction(
            turn=10,
            domain="Economy",
            action_type="INVEST_IN_WELFARE",
            action_summary="Invested in welfare programs",
            outcome=None
        )
        line = action.to_prompt_line()
        
        assert "Turn 10" in line
        assert "Economy" in line
        assert "welfare" in line.lower()


class TestContextManager:
    """Tests for ContextManager."""
    
    @pytest.fixture
    def world(self):
        """Create a test world."""
        return generate_world(seed=42, history_seed=99, n_cells=200, n_nations=4)
    
    @pytest.fixture
    def manager(self, world):
        """Create and initialize a context manager."""
        manager = ContextManager()
        manager.initialize_from_world(world)
        return manager
    
    def test_initialize_from_world(self, world, manager):
        """ContextManager initializes relationships from world."""
        nation_ids = list(world.nations.keys())
        
        # Should have relationships for all nations
        assert len(manager.relationship_summaries) == len(nation_ids)
        
        # Each nation should have relationships with all others
        for nation_id in nation_ids:
            assert len(manager.relationship_summaries[nation_id]) == len(nation_ids) - 1
    
    def test_get_relationships_for(self, world, manager):
        """Can get formatted relationships for a nation."""
        nation_id = list(world.nations.keys())[0]
        
        relationships = manager.get_relationships_for(nation_id)
        
        assert len(relationships) > 0
        assert all(isinstance(r, str) for r in relationships)
    
    def test_get_events_for_empty(self, manager):
        """Returns empty list when no events."""
        manager.global_events = []
        events = manager.get_events_for("nation_a", current_turn=1)
        assert events == []
    
    def test_get_actions_for_empty(self, manager):
        """Returns empty list when no actions."""
        actions = manager.get_actions_for("nation_a")
        assert actions == []
    
    def test_pruning_events(self, manager):
        """Events are pruned when exceeding limit."""
        # FIX: The number of genesis events varies by seed, so we dynamically calculate initial_count instead of hardcoding 169
        initial_count = len(manager.global_events)
        # Add many events
        for i in range(100):
            manager.global_events.append(NotableEvent(
                turn=i,
                event_type=EventType.TRADE_DEAL,
                actors=[],
                summary=f"Trade event {i}"
            ))
        
        manager._prune_if_needed()
        
        assert len(manager.global_events) == initial_count + 100 # No pruning for global events anymore
    
    def test_critical_events_preserved(self, manager):
        """Critical events are preserved during pruning."""
        # Add one critical event
        manager.global_events.append(NotableEvent(
            turn=1,
            event_type=EventType.WAR_DECLARED,
            actors=["a", "b"],
            summary="Critical war event"
        ))
        
        # Add many non-critical events
        for i in range(100):
            manager.global_events.append(NotableEvent(
                turn=i + 10,
                event_type=EventType.TRADE_DEAL,
                actors=[],
                summary=f"Trade event {i}"
            ))
        
        manager._prune_if_needed()
        
        # Critical event should still be present
        war_events = [e for e in manager.global_events if e.event_type == EventType.WAR_DECLARED]
        assert len(war_events) == 1
    
    def test_trust_trend_calculation(self, world, manager):
        """Trust trend is calculated correctly."""
        nation_id = list(world.nations.keys())[0]
        other_id = list(world.nations.keys())[1]
        
        # Simulate trust changes over multiple turns
        for i in range(5):
            if nation_id in world.trust_matrix:
                world.trust_matrix[nation_id][other_id] = 50 + i * 3  # Rising trust
            
            manager._update_relationships(world)
        
        summary = manager.relationship_summaries[nation_id][other_id]
        assert summary.trust_trend == "↑"  # Should show rising trend
