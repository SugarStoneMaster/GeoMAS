"""
Tests for Public Opinion System.

Validates satisfaction dynamics, triggers, and cultural traits.
"""

import pytest
from geomas.world import generate_world
from geomas.actions.engine import ActionEngine
from geomas.actions.opinion import (
    OpinionPayload,
    OpinionTrigger,
    apply_satisfaction_deltas,
    check_triggers,
    generate_cultural_traits,
)
from geomas.actions.opinion.schemas import (
    THRESHOLD_GENERAL_STRIKE,
    THRESHOLD_CIVIL_UNREST,
    THRESHOLD_UNREST_RECOVERY,
)
from geomas.actions.opinion.handler import (
    is_nation_on_strike,
    get_production_multiplier,
)


class TestCulturalTraits:
    """Tests for cultural traits generation."""
    
    def test_traits_are_deterministic(self):
        """Same seed + nation_id = same traits."""
        traits1 = generate_cultural_traits("nation_A", seed=42)
        traits2 = generate_cultural_traits("nation_A", seed=42)
        assert traits1 == traits2
    
    def test_different_nations_get_different_traits(self):
        """Different nations get different cultural traits."""
        traits_a = generate_cultural_traits("nation_A", seed=42)
        traits_b = generate_cultural_traits("nation_B", seed=42)
        assert traits_a != traits_b
    
    def test_traits_count(self):
        """Each nation gets 4-6 traits."""
        traits = generate_cultural_traits("test_nation", seed=123)
        assert 4 <= len(traits) <= 6


class TestSatisfactionDynamics:
    """Tests for satisfaction delta calculation."""
    
    def test_peace_bonus(self):
        """Nation at peace gets positive satisfaction."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        initial_sat = nation.public_satisfaction
        
        # Ensure at peace
        for other_id in world.nations:
            if other_id != nation_id:
                world.relationship_matrix[nation_id][other_id] = "PEACE"
        
        delta = apply_satisfaction_deltas(engine, nation_id)
        assert delta >= 0  # Should be positive (peace bonus)
    
    def test_war_penalty(self):
        """Nation at war loses satisfaction."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        
        nation_id = list(world.nations.keys())[0]
        other_id = list(world.nations.keys())[1]
        
        # Set at war
        world.relationship_matrix[nation_id][other_id] = "WAR"
        
        delta = apply_satisfaction_deltas(engine, nation_id)
        assert delta < 0  # Should be negative (war penalty)


class TestOpinionTriggers:
    """Tests for automatic triggers."""
    
    def test_general_strike_triggered(self):
        """General strike triggers when satisfaction < 20."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Set satisfaction below threshold
        nation.public_satisfaction = THRESHOLD_GENERAL_STRIKE - 1
        
        triggered = check_triggers(engine, nation_id)
        assert OpinionTrigger.GENERAL_STRIKE in triggered
    
    def test_civil_unrest_triggered(self):
        """Civil unrest triggers when satisfaction < 10."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Set satisfaction below threshold
        nation.public_satisfaction = THRESHOLD_CIVIL_UNREST - 1
        
        triggered = check_triggers(engine, nation_id)
        assert OpinionTrigger.CIVIL_UNREST in triggered
        assert nation.civil_unrest_active is True
    
    def test_civil_unrest_recovery(self):
        """Civil unrest ends when satisfaction > 50."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Simulate active unrest then recovery
        nation.civil_unrest_active = True
        nation.public_satisfaction = THRESHOLD_UNREST_RECOVERY + 1
        
        check_triggers(engine, nation_id)
        assert nation.civil_unrest_active is False


class TestProductionMultiplier:
    """Tests for production penalties."""
    
    def test_normal_production(self):
        """No penalty when satisfaction is healthy."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        nation = list(world.nations.values())[0]
        nation.public_satisfaction = 60
        nation.civil_unrest_active = False
        
        assert get_production_multiplier(nation) == 1.0
    
    def test_strike_production(self):
        """50% penalty during general strike."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        nation = list(world.nations.values())[0]
        nation.public_satisfaction = 15  # Below 20
        nation.civil_unrest_active = False
        
        assert get_production_multiplier(nation) == 0.5
    
    def test_unrest_production(self):
        """0% production during civil unrest."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        nation = list(world.nations.values())[0]
        nation.civil_unrest_active = True
        
        assert get_production_multiplier(nation) == 0.0
