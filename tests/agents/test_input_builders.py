"""
Tests for Input Builders.
"""

import pytest
from geomas.world import generate_world
from geomas.agents.context.input import (
    PresidentInputBuilder,
    DefenseInputBuilder,
    EconomyInputBuilder,
    ForeignInputBuilder,
    OpinionInputBuilder,
)


@pytest.fixture
def world():
    """Create a test world."""
    return generate_world(seed=42, history_seed=99, n_cells=200, n_nations=4)


class TestPresidentInputBuilder:
    """Tests for President input builder."""
    
    def test_builds_input(self, world):
        """Can build president input context."""
        builder = PresidentInputBuilder(world)
        nation_id = list(world.nations.keys())[0]
        
        context = builder.build(nation_id, turn=1)
        
        assert "NATION STATUS" in context
        assert "RELATIONSHIPS" in context
    
    def test_includes_minister_briefings(self, world):
        """Minister briefings appear when provided."""
        builder = PresidentInputBuilder(world)
        nation_id = list(world.nations.keys())[0]
        
        context = builder.build(
            nation_id,
            turn=1,
            defense_summary="Border secure",
            economy_summary="Budget stable",
            foreign_summary="Peace with all"
        )
        
        assert "Border secure" in context
        assert "Budget stable" in context
        assert "Peace with all" in context


class TestDefenseInputBuilder:
    """Tests for Defense input builder."""
    
    def test_builds_input(self, world):
        """Can build defense input context."""
        builder = DefenseInputBuilder(world)
        nation_id = list(world.nations.keys())[0]
        
        context = builder.build(nation_id, turn=1)
        
        assert "MILITARY" in context or "BUDGET" in context
    
    def test_includes_morale_warning_when_low(self, world):
        """Morale warning shown when satisfaction is low."""
        builder = DefenseInputBuilder(world)
        nation_id = list(world.nations.keys())[0]
        
        # Lower satisfaction
        world.nations[nation_id].public_satisfaction = 25
        
        context = builder.build(nation_id, turn=1)
        
        assert "MORALE" in context or "WARNING" in context


class TestEconomyInputBuilder:
    """Tests for Economy input builder."""
    
    def test_builds_input(self, world):
        """Can build economy input context."""
        builder = EconomyInputBuilder(world)
        nation_id = list(world.nations.keys())[0]
        
        context = builder.build(nation_id, turn=1)
        
        assert "TREASURY" in context
        assert "SATISFACTION" in context
    
    def test_shows_satisfaction_actions(self, world):
        """Shows actions that affect satisfaction."""
        builder = EconomyInputBuilder(world)
        nation_id = list(world.nations.keys())[0]
        
        context = builder.build(nation_id, turn=1)
        
        assert "INVEST_IN_WELFARE" in context or "welfare" in context.lower()


class TestForeignInputBuilder:
    """Tests for Foreign input builder."""
    
    def test_builds_input(self, world):
        """Can build foreign input context."""
        builder = ForeignInputBuilder(world)
        nation_id = list(world.nations.keys())[0]
        
        context = builder.build(nation_id, turn=1)
        
        assert "Diplomatic relationships" in context
    
    def test_shows_pending_proposals(self, world):
        """Shows pending proposals when present."""
        builder = ForeignInputBuilder(world)
        nation_id = list(world.nations.keys())[0]
        
        # Add a pending proposal
        world.nations[nation_id].pending_proposals = [
            {"type": "ALLIANCE", "from": "other_nation", "turn": 5}
        ]
        
        context = builder.build(nation_id, turn=1)
        
        assert "Pending proposals" in context
        assert "ALLIANCE" in context


class TestOpinionInputBuilder:
    """Tests for Opinion input builder."""
    
    def test_builds_input(self, world):
        """Can build opinion input context."""
        builder = OpinionInputBuilder(world)
        nation_id = list(world.nations.keys())[0]
        
        context = builder.build(nation_id, turn=1)
        
        assert "PUBLIC MOOD" in context or "SATISFACTION" in context
    
    def test_shows_conflict_status(self, world):
        """Shows war status when at war."""
        builder = OpinionInputBuilder(world)
        nation_id = list(world.nations.keys())[0]
        other_id = list(world.nations.keys())[1]
        
        # Set up war
        if nation_id not in world.relationship_matrix:
            world.relationship_matrix[nation_id] = {}
        world.relationship_matrix[nation_id][other_id] = "WAR"
        
        context = builder.build(nation_id, turn=1)
        
        assert "WAR" in context
