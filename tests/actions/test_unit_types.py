"""
Tests for Unit Types and Constraints.

Validates unit costs, terrain constraints, and validation helpers.
"""

import pytest
from geomas.actions.defense import (
    UnitType,
    UNIT_COSTS,
    UNIT_MAINTENANCE,
    UNIT_TERRAIN_CONSTRAINTS,
    TERRAIN_DEFENSE_MULTIPLIER,
    can_place_unit,
    can_afford_unit,
    get_terrain_defense_bonus,
)
from geomas.schemas.world import TerrainType


class TestUnitCosts:
    """Tests for unit cost definitions."""
    
    def test_all_unit_types_have_costs(self):
        """Every UnitType must have creation costs defined."""
        for unit_type in UnitType:
            assert unit_type in UNIT_COSTS
            costs = UNIT_COSTS[unit_type]
            assert "budget" in costs
            assert "materials" in costs
            assert "energy" in costs
            assert "population" in costs
    
    def test_all_unit_types_have_maintenance(self):
        """Every UnitType must have maintenance costs defined."""
        for unit_type in UnitType:
            assert unit_type in UNIT_MAINTENANCE
            maint = UNIT_MAINTENANCE[unit_type]
            assert "budget" in maint
            assert "materials" in maint
            assert "energy" in maint
    
    def test_cost_ordering_by_complexity(self):
        """More complex units should cost more."""
        # Soldiers are cheapest
        assert UNIT_COSTS[UnitType.SOLDIER]["budget"] < UNIT_COSTS[UnitType.NAVY]["budget"]
        assert UNIT_COSTS[UnitType.SOLDIER]["budget"] < UNIT_COSTS[UnitType.AIRCRAFT]["budget"]
        # Aircraft are most expensive
        assert UNIT_COSTS[UnitType.AIRCRAFT]["budget"] > UNIT_COSTS[UnitType.NAVY]["budget"]
    
    def test_maintenance_proportional_to_cost(self):
        """Maintenance should generally be proportional to unit cost."""
        for unit_type in UnitType:
            # Maintenance budget should be less than creation cost
            assert UNIT_MAINTENANCE[unit_type]["budget"] < UNIT_COSTS[unit_type]["budget"]


class TestTerrainConstraints:
    """Tests for terrain placement constraints."""
    
    def test_all_unit_types_have_constraints(self):
        """Every UnitType must have terrain constraints defined."""
        for unit_type in UnitType:
            assert unit_type in UNIT_TERRAIN_CONSTRAINTS
            assert len(UNIT_TERRAIN_CONSTRAINTS[unit_type]) > 0
    
    def test_soldiers_land_based(self):
        """Soldiers can be on land terrains, not ocean."""
        allowed = UNIT_TERRAIN_CONSTRAINTS[UnitType.SOLDIER]
        assert TerrainType.LAND in allowed
        assert TerrainType.COASTAL in allowed
        assert TerrainType.MOUNTAIN in allowed
        assert TerrainType.OCEAN not in allowed
    
    def test_navy_ocean_only(self):
        """Navy can only be in ocean (territorial waters)."""
        allowed = UNIT_TERRAIN_CONSTRAINTS[UnitType.NAVY]
        assert TerrainType.OCEAN in allowed
        assert len(allowed) == 1  # Only ocean
    
    def test_aircraft_land_based(self):
        """Aircraft stationed on land terrains."""
        allowed = UNIT_TERRAIN_CONSTRAINTS[UnitType.AIRCRAFT]
        assert TerrainType.LAND in allowed
        assert TerrainType.COASTAL in allowed
        assert TerrainType.MOUNTAIN in allowed
        assert TerrainType.OCEAN not in allowed


class TestTerrainDefenseModifiers:
    """Tests for terrain combat modifiers."""
    
    def test_all_terrains_have_modifiers(self):
        """Every terrain type should have a defense modifier."""
        for terrain in TerrainType:
            assert terrain in TERRAIN_DEFENSE_MULTIPLIER
    
    def test_mountain_best_defense(self):
        """Mountains should have the best defense bonus."""
        assert TERRAIN_DEFENSE_MULTIPLIER[TerrainType.MOUNTAIN] == 2.5
        for terrain in TerrainType:
            assert TERRAIN_DEFENSE_MULTIPLIER[terrain] <= TERRAIN_DEFENSE_MULTIPLIER[TerrainType.MOUNTAIN]
    
    def test_coastal_neutralized(self):
        """Coastal disadvantage has been neutralized for balance."""
        assert TERRAIN_DEFENSE_MULTIPLIER[TerrainType.COASTAL] == 1.0


class TestCanPlaceUnit:
    """Tests for can_place_unit helper."""
    
    def test_soldier_on_land(self):
        assert can_place_unit(UnitType.SOLDIER, TerrainType.LAND) is True
    
    def test_soldier_on_ocean(self):
        assert can_place_unit(UnitType.SOLDIER, TerrainType.OCEAN) is False
    
    def test_navy_on_ocean(self):
        assert can_place_unit(UnitType.NAVY, TerrainType.OCEAN) is True
    
    def test_navy_on_land(self):
        assert can_place_unit(UnitType.NAVY, TerrainType.LAND) is False
    
    def test_aircraft_on_mountain(self):
        assert can_place_unit(UnitType.AIRCRAFT, TerrainType.MOUNTAIN) is True


class TestCanAffordUnit:
    """Tests for can_afford_unit helper."""
    
    def test_can_afford_single_soldier(self):
        """Should be able to afford one soldier with sufficient resources."""
        can_afford, reason = can_afford_unit(
            UnitType.SOLDIER,
            quantity=1,
            budget=100.0,
            materials=50.0,
            energy=10.0,
            available_population=100
        )
        assert can_afford is True
        assert reason == ""
    
    def test_cannot_afford_insufficient_budget(self):
        """Should fail when budget is too low."""
        can_afford, reason = can_afford_unit(
            UnitType.SOLDIER,
            quantity=10,
            budget=10.0,  # Need 50, have 10
            materials=100.0,
            energy=100.0,
            available_population=100
        )
        assert can_afford is False
        assert "budget" in reason.lower()
    
    def test_cannot_afford_insufficient_population(self):
        """Should fail when population is too low."""
        can_afford, reason = can_afford_unit(
            UnitType.NAVY,
            quantity=5,
            budget=1000.0,
            materials=500.0,
            energy=100.0,
            available_population=30  # Need 50 (5 ships * 10 crew), have 30
        )
        assert can_afford is False
        assert "population" in reason.lower()
    
    def test_can_afford_expensive_aircraft(self):
        """Should be able to afford aircraft with proper resources."""
        can_afford, reason = can_afford_unit(
            UnitType.AIRCRAFT,
            quantity=2,
            budget=200.0,   # Need 160
            materials=100.0, # Need 80
            energy=30.0,     # Need 20
            available_population=20  # Need 10
        )
        assert can_afford is True


class TestGetTerrainDefenseBonus:
    """Tests for get_terrain_defense_bonus helper."""
    
    def test_mountain_bonus(self):
        assert get_terrain_defense_bonus(TerrainType.MOUNTAIN) == 2.5
    
    def test_land_baseline(self):
        assert get_terrain_defense_bonus(TerrainType.LAND) == 1.2
    
    def test_ocean_baseline(self):
        assert get_terrain_defense_bonus(TerrainType.OCEAN) == 1.0
