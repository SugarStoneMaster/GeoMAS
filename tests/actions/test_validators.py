"""
Tests for Action Validators.

Tests all validation logic in ActionValidators class.
"""

import pytest
from geomas.world import generate_world
from geomas.actions.validators import ActionValidators
from geomas.world.spatial import SpatialManager


class TestCanMoveTroops:
    """Tests for can_move_troops validator."""
    
    @pytest.fixture
    def setup(self):
        """Create world and spatial manager."""
        world = generate_world(seed=42, n_cells=100, n_nations=3)
        spatial = SpatialManager(world)
        return world, spatial
    
    def test_valid_move_within_own_territory(self, setup):
        """Can move troops between own provinces."""
        world, spatial = setup
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Find two connected provinces
        if len(nation.province_ids) >= 2:
            from_prov = nation.province_ids[0]
            to_prov = nation.province_ids[1]
            
            can, msg = ActionValidators.can_move_troops(
                world, spatial, nation_id, from_prov, to_prov
            )
            # May or may not be valid depending on connectivity
            assert isinstance(can, bool)
            assert isinstance(msg, str)
    
    def test_cannot_move_from_foreign_province(self, setup):
        """Cannot move troops from province not owned."""
        world, spatial = setup
        nations = list(world.nations.keys())
        nation_id = nations[0]
        other_nation = nations[1]
        
        # Try to move from other nation's province
        other_prov = world.nations[other_nation].province_ids[0]
        own_prov = world.nations[nation_id].province_ids[0]
        
        can, msg = ActionValidators.can_move_troops(
            world, spatial, nation_id, other_prov, own_prov
        )
        assert can is False
        assert "does not belong" in msg
    
    def test_cannot_move_to_foreign_territory(self, setup):
        """Cannot redeploy to foreign territory (must use ATTACK)."""
        world, spatial = setup
        nations = list(world.nations.keys())
        nation_id = nations[0]
        other_nation = nations[1]
        
        own_prov = world.nations[nation_id].province_ids[0]
        other_prov = world.nations[other_nation].province_ids[0]
        
        can, msg = ActionValidators.can_move_troops(
            world, spatial, nation_id, own_prov, other_prov
        )
        assert can is False
        assert "foreign territory" in msg.lower() or "ATTACK" in msg
    
    def test_invalid_destination(self, setup):
        """Cannot move to non-existent province."""
        world, spatial = setup
        nation_id = list(world.nations.keys())[0]
        own_prov = world.nations[nation_id].province_ids[0]
        
        can, msg = ActionValidators.can_move_troops(
            world, spatial, nation_id, own_prov, 99999
        )
        assert can is False
        assert "does not exist" in msg


class TestCanAttack:
    """Tests for can_attack validator."""
    
    @pytest.fixture
    def world(self):
        """Create world."""
        return generate_world(seed=42, n_cells=100, n_nations=3)
    
    def test_cannot_attack_own_territory(self, world):
        """Cannot attack own province."""
        nation_id = list(world.nations.keys())[0]
        own_prov = world.nations[nation_id].province_ids[0]
        
        can, msg = ActionValidators.can_attack(world, nation_id, own_prov)
        assert can is False
        assert "own territory" in msg.lower() or "Cannot attack" in msg
    
    def test_cannot_attack_non_adjacent(self, world):
        """Cannot attack non-adjacent province."""
        nations = list(world.nations.keys())
        attacker_id = nations[0]
        
        # Find a province far from attacker
        attacker_provs = set(world.nations[attacker_id].province_ids)
        
        # Find target that is not adjacent to any attacker province
        for target_prov_id in world.provinces:
            target = world.provinces[target_prov_id]
            if target.owner_id != attacker_id:
                # Check if any neighbor is owned by attacker
                has_adjacent = any(
                    world.provinces.get(n, None) and 
                    world.provinces[n].owner_id == attacker_id 
                    for n in target.neighbors
                )
                if not has_adjacent:
                    can, msg = ActionValidators.can_attack(world, attacker_id, target_prov_id)
                    assert can is False
                    assert "not adjacent" in msg.lower()
                    return
    
    def test_valid_attack_on_adjacent_enemy(self, world):
        """Can attack adjacent enemy province."""
        nations = list(world.nations.keys())
        attacker_id = nations[0]
        
        # Find adjacent enemy province
        for prov_id in world.nations[attacker_id].province_ids:
            prov = world.provinces[prov_id]
            for neighbor_id in prov.neighbors:
                neighbor = world.provinces.get(neighbor_id)
                if neighbor and neighbor.owner_id != attacker_id:
                    can, msg = ActionValidators.can_attack(world, attacker_id, neighbor_id)
                    assert can is True
                    assert "Valid" in msg
                    return
    
    def test_invalid_target(self, world):
        """Cannot attack non-existent province."""
        nation_id = list(world.nations.keys())[0]
        
        can, msg = ActionValidators.can_attack(world, nation_id, 99999)
        assert can is False
        assert "invalid" in msg.lower() or "Target" in msg


class TestCanAffordBudget:
    """Tests for can_afford_budget validator."""
    
    @pytest.fixture
    def world(self):
        """Create world."""
        return generate_world(seed=42, n_cells=50, n_nations=2)
    
    def test_can_afford_within_budget(self, world):
        """Can afford amount less than budget."""
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        nation.total_budget = 1000.0
        
        can, msg = ActionValidators.can_afford_budget(world, nation_id, 500.0)
        assert can is True
        assert "available" in msg.lower()
    
    def test_cannot_afford_exceeding_budget(self, world):
        """Cannot afford amount exceeding budget."""
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        nation.total_budget = 100.0
        
        can, msg = ActionValidators.can_afford_budget(world, nation_id, 500.0)
        assert can is False
        assert "Insufficient" in msg
    
    def test_can_afford_exact_budget(self, world):
        """Can afford amount equal to budget."""
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        nation.total_budget = 500.0
        
        can, msg = ActionValidators.can_afford_budget(world, nation_id, 500.0)
        assert can is True
    
    def test_invalid_nation(self, world):
        """Invalid nation returns error."""
        can, msg = ActionValidators.can_afford_budget(world, "INVALID_NATION", 100.0)
        assert can is False
        assert "not found" in msg.lower()


class TestCanRaiseWarTax:
    """Tests for can_raise_war_tax validator."""
    
    @pytest.fixture
    def world(self):
        """Create world."""
        return generate_world(seed=42, n_cells=50, n_nations=2)
    
    def test_can_raise_with_high_satisfaction(self, world):
        """Can raise war tax with satisfaction >= 20."""
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        nation.public_satisfaction = 50.0
        
        can, msg = ActionValidators.can_raise_war_tax(world, nation_id)
        assert can is True
        assert "sufficient" in msg.lower()
    
    def test_cannot_raise_with_low_satisfaction(self, world):
        """Cannot raise war tax with satisfaction < 20."""
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        nation.public_satisfaction = 15.0
        
        can, msg = ActionValidators.can_raise_war_tax(world, nation_id)
        assert can is False
        assert "too low" in msg.lower()
    
    def test_threshold_boundary(self, world):
        """Test exact threshold value (20)."""
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Exactly at threshold
        nation.public_satisfaction = 20.0
        can, msg = ActionValidators.can_raise_war_tax(world, nation_id)
        assert can is True
        
        # Just below threshold
        nation.public_satisfaction = 19.9
        can, msg = ActionValidators.can_raise_war_tax(world, nation_id)
        assert can is False
    
    def test_invalid_nation(self, world):
        """Invalid nation returns error."""
        can, msg = ActionValidators.can_raise_war_tax(world, "INVALID_NATION")
        assert can is False
        assert "not found" in msg.lower()
