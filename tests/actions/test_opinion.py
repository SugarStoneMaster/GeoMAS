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
        """Production decays linearly (at 15 satisfaction, mult should be 0.5625)."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        nation = list(world.nations.values())[0]
        nation.public_satisfaction = 15  # In the decay zone
        nation.civil_unrest_active = False
        
        # 0.5 + (15-10)/40 * 0.5 = 0.5 + 0.0625 = 0.5625
        assert get_production_multiplier(nation) == pytest.approx(0.5625)
    
    def test_unrest_production(self):
        """0% production during civil unrest."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        nation = list(world.nations.values())[0]
        nation.civil_unrest_active = True
        
        assert get_production_multiplier(nation) == 0.0


class TestSeparateDeltaMultipliers:
    """Tests for separate positive/negative delta multipliers."""
    
    def test_positive_delta_uses_increase_multiplier(self):
        """Positive deltas multiplied by multiplier_increase."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Set all at peace and good resources
        for other_id in world.nations:
            if other_id != nation_id:
                world.relationship_matrix[nation_id][other_id] = "PEACE"
        nation.total_food = 200
        nation.total_energy = 200
        
        # High increase multiplier
        nation.population_multiplier_increase = 2.0
        nation.population_multiplier_decrease = 0.5
        
        initial_sat = nation.public_satisfaction
        apply_satisfaction_deltas(engine, nation_id)
        
        # Should get boosted positive effect (peace + surplus)
        delta = nation.public_satisfaction - initial_sat
        assert delta > 2  # Base would be +2, with 2.0 mult = +4
    
    def test_negative_delta_uses_decrease_multiplier(self):
        """Negative deltas multiplied by multiplier_decrease."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        
        nation_id = list(world.nations.keys())[0]
        other_id = list(world.nations.keys())[1]
        nation = world.nations[nation_id]
        
        # Set at war (negative delta)
        world.relationship_matrix[nation_id][other_id] = "WAR"
        
        # Low decrease multiplier = reduced negative effect
        nation.population_multiplier_increase = 1.0
        nation.population_multiplier_decrease = 0.5
        
        initial_sat = nation.public_satisfaction
        apply_satisfaction_deltas(engine, nation_id)
        
        delta = nation.public_satisfaction - initial_sat
        # War penalty is -3, with 0.5 mult = -1.5
        assert -2 < delta < 0


class TestCivilUnrest50PercentRevolt:
    """Tests for 50% random province revolt during civil unrest."""
    
    def test_only_half_provinces_revolt(self):
        """Only 50% of provinces get in_revolt=True."""
        import random
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Ensure nation has provinces
        assert len(nation.province_ids) >= 2
        
        # Trigger civil unrest
        nation.public_satisfaction = THRESHOLD_CIVIL_UNREST - 1
        rng = random.Random(42)  # Deterministic
        
        check_triggers(engine, nation_id, rng=rng)
        
        # Count revolting provinces
        revolting = sum(
            1 for pid in nation.province_ids 
            if world.provinces[pid].in_revolt
        )
        
        # Should be ~50% (allow for rounding)
        expected = max(1, len(nation.province_ids) // 2)
        assert revolting == expected
    
    def test_in_revolt_flag_set_correctly(self):
        """in_revolt flag is True only for selected provinces."""
        import random
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Initially no province in revolt
        for pid in nation.province_ids:
            assert world.provinces[pid].in_revolt is False
        
        # Trigger unrest
        nation.public_satisfaction = 5
        check_triggers(engine, nation_id, rng=random.Random(42))
        
        # Some provinces should be in revolt
        revolting_provs = [
            pid for pid in nation.province_ids 
            if world.provinces[pid].in_revolt
        ]
        assert len(revolting_provs) > 0
    
    def test_provinces_restored_on_recovery(self):
        """in_revolt=False for all provinces when unrest ends."""
        import random
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # First trigger unrest
        nation.public_satisfaction = 5
        check_triggers(engine, nation_id, rng=random.Random(42))
        assert nation.civil_unrest_active is True
        
        # Then recover
        nation.public_satisfaction = THRESHOLD_UNREST_RECOVERY + 1
        check_triggers(engine, nation_id)
        
        # All provinces should be restored
        for pid in nation.province_ids:
            assert world.provinces[pid].in_revolt is False


class TestProvinceProductionBlocked:
    """Tests for province-level production blocking."""
    
    def test_province_in_revolt_zero_production(self):
        """Province with in_revolt=True gets 0 production multiplier."""
        from geomas.actions.opinion.handler import get_province_production_multiplier
        from geomas.schemas.world import ProvinceState, NationState
        
        province = ProvinceState(id=1, terrain="LAND", coordinates=(0, 0))
        province.in_revolt = True
        
        nation = NationState(id="test", name="Test", color="red")
        nation.public_satisfaction = 60
        
        assert get_province_production_multiplier(province, nation) == 0.0
    
    def test_province_not_in_revolt_normal_production(self):
        """Province with in_revolt=False gets normal production."""
        from geomas.actions.opinion.handler import get_province_production_multiplier
        from geomas.schemas.world import ProvinceState, NationState
        
        province = ProvinceState(id=1, terrain="LAND", coordinates=(0, 0))
        province.in_revolt = False
        
        nation = NationState(id="test", name="Test", color="red")
        nation.public_satisfaction = 60
        
        assert get_province_production_multiplier(province, nation) == 1.0

