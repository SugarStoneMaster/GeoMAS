"""
Tests for Calculators Module.

Tests analytics, crisis, production and consumption calculators.
"""

import pytest
from geomas.world import generate_world
from geomas.calculators.analytics import calculate_nation_aggregates, calculate_power_projection
from geomas.calculators.crisis import (
    calculate_resource_balance,
    calculate_starvation_casualties,
    calculate_energy_penalty,
)
from geomas.calculators.consumption import (
    calculate_food_consumption,
    calculate_energy_consumption,
    calculate_materials_consumption,
)
from geomas.calculators.production import (
    calculate_production_penalty,
    calculate_tax_collection,
)


class TestCalculateNationAggregates:
    """Tests for calculate_nation_aggregates function."""
    
    def test_aggregates_population(self):
        """Aggregates population from all provinces."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Set known population values
        total_pop = 0
        for p_id in nation.province_ids:
            world.provinces[p_id].population = 1000
            total_pop += 1000
        
        result = calculate_nation_aggregates(nation, world)
        assert result["total_population"] == total_pop
    
    def test_aggregates_military_units(self):
        """Aggregates soldiers, aircraft, navy from all provinces."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Set known unit values
        for p_id in nation.province_ids:
            world.provinces[p_id].soldiers = 100
            world.provinces[p_id].aircraft = 10
            world.provinces[p_id].navy = 5
        
        result = calculate_nation_aggregates(nation, world)
        expected_soldiers = 100 * len(nation.province_ids)
        expected_aircraft = 10 * len(nation.province_ids)
        expected_navy = 5 * len(nation.province_ids)
        
        assert result["total_soldiers"] == expected_soldiers
        assert result["total_aircraft"] == expected_aircraft
        # Navy may include territorial waters, so >= check
        assert result["total_navy"] >= expected_navy
    
    def test_aggregates_production(self):
        """Aggregates food, energy, materials production."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Set known production values
        for p_id in nation.province_ids:
            world.provinces[p_id].food_production = 50.0
            world.provinces[p_id].energy_production = 30.0
            world.provinces[p_id].materials_production = 20.0
        
        result = calculate_nation_aggregates(nation, world)
        n_provs = len(nation.province_ids)
        
        assert result["total_food_production"] == 50.0 * n_provs
        assert result["total_energy_production"] == 30.0 * n_provs
        assert result["total_materials_production"] == 20.0 * n_provs


class TestCalculatePowerProjection:
    """Tests for calculate_power_projection function."""
    
    def test_power_increases_with_military(self):
        """More military units = higher power projection."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        nation = list(world.nations.values())[0]
        
        nation.total_soldiers = 0
        nation.total_aircraft = 0
        nation.total_navy = 0
        nation.nukes = 0
        nation.total_budget = 0
        nation.total_food = 0
        nation.total_energy = 0
        nation.total_materials = 0
        
        power_base = calculate_power_projection(nation)
        
        nation.total_soldiers = 1000
        power_with_soldiers = calculate_power_projection(nation)
        
        assert power_with_soldiers > power_base
    
    def test_nukes_have_high_weight(self):
        """Nuclear weapons significantly increase power."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        nation = list(world.nations.values())[0]
        
        nation.total_soldiers = 1000
        nation.total_aircraft = 50
        nation.total_navy = 50
        nation.nukes = 0
        nation.total_budget = 1000
        nation.total_food = 500
        nation.total_energy = 500
        nation.total_materials = 500
        
        power_no_nukes = calculate_power_projection(nation)
        
        nation.nukes = 5
        power_with_nukes = calculate_power_projection(nation)
        
        # Nukes should add significant power (50 weight per nuke)
        assert power_with_nukes - power_no_nukes >= 250  # 5 * 50
    
    def test_returns_rounded_float(self):
        """Power projection is rounded to 2 decimals."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        nation = list(world.nations.values())[0]
        
        power = calculate_power_projection(nation)
        assert isinstance(power, float)
        # Check rounding
        assert power == round(power, 2)


class TestCalculateResourceBalance:
    """Tests for calculate_resource_balance function."""
    
    def test_balance_calculation(self):
        """Resource balance = production - consumption."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        result = calculate_resource_balance(nation, world)
        
        assert "food_balance" in result
        assert "energy_balance" in result
        assert "materials_balance" in result
    
    def test_positive_balance_with_surplus(self):
        """Positive balance when production > consumption."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Set very high production
        for p_id in nation.province_ids:
            world.provinces[p_id].food_production = 1000.0
            world.provinces[p_id].population = 10  # Low consumption
        
        result = calculate_resource_balance(nation, world)
        assert result["food_balance"] > 0


class TestCalculateStarvationCasualties:
    """Tests for calculate_starvation_casualties function."""
    
    def test_no_casualties_with_surplus(self):
        """No starvation when food_deficit >= 0."""
        casualties = calculate_starvation_casualties(food_deficit=100, total_population=10000)
        assert casualties == 0
    
    def test_no_casualties_at_zero(self):
        """No starvation when food_deficit = 0."""
        casualties = calculate_starvation_casualties(food_deficit=0, total_population=10000)
        assert casualties == 0
    
    def test_casualties_with_deficit(self):
        """Starvation occurs when food_deficit < 0."""
        casualties = calculate_starvation_casualties(food_deficit=-500, total_population=10000)
        assert casualties > 0
    
    def test_casualties_capped_at_10_percent(self):
        """Starvation capped at 10% of population per turn."""
        casualties = calculate_starvation_casualties(food_deficit=-99999, total_population=10000)
        assert casualties <= 1000  # Max 10% of 10000
    
    def test_returns_integer(self):
        """Casualties is always an integer."""
        casualties = calculate_starvation_casualties(food_deficit=-100, total_population=5000)
        assert isinstance(casualties, int)


class TestCalculateEnergyPenalty:
    """Tests for calculate_energy_penalty function."""
    
    def test_no_penalty_with_surplus(self):
        """No penalty when energy_deficit >= 0."""
        penalty = calculate_energy_penalty(energy_deficit=100)
        assert penalty == 1.0
    
    def test_no_penalty_at_zero(self):
        """No penalty when energy_deficit = 0."""
        penalty = calculate_energy_penalty(energy_deficit=0)
        assert penalty == 1.0
    
    def test_penalty_with_deficit(self):
        """Penalty when energy_deficit < 0."""
        penalty = calculate_energy_penalty(energy_deficit=-50)
        assert penalty < 1.0
    
    def test_penalty_capped_at_50_percent(self):
        """Penalty never goes below 0.5 (50% production)."""
        penalty = calculate_energy_penalty(energy_deficit=-99999)
        assert penalty >= 0.5
    
    def test_penalty_scales_with_deficit(self):
        """Larger deficit = larger penalty."""
        penalty_small = calculate_energy_penalty(energy_deficit=-10)
        penalty_large = calculate_energy_penalty(energy_deficit=-50)
        
        assert penalty_large < penalty_small


class TestConsumptionCalculators:
    """Tests for consumption calculation functions."""
    
    def test_food_consumption_scales_with_population(self):
        """More population = more food consumption."""
        low = calculate_food_consumption(total_population=1000)
        high = calculate_food_consumption(total_population=10000)
        
        assert high > low
    
    def test_energy_consumption_scales_with_population(self):
        """More population = more energy consumption."""
        low = calculate_energy_consumption(total_population=1000)
        high = calculate_energy_consumption(total_population=10000)
        
        assert high > low
    
    def test_materials_consumption_scales_with_military(self):
        """More military = more materials consumption."""
        low = calculate_materials_consumption(total_soldiers=100, total_aircraft=10, total_navy=5)
        high = calculate_materials_consumption(total_soldiers=1000, total_aircraft=100, total_navy=50)
        
        assert high > low
    
    def test_zero_population_zero_consumption(self):
        """Zero population = zero food consumption."""
        consumption = calculate_food_consumption(total_population=0)
        assert consumption == 0


class TestProductionCalculators:
    """Tests for production calculation functions."""
    
    def test_production_penalty_based_on_workforce_ratio(self):
        """Penalty applied when workforce ratio is low."""
        # MIN_WORKFORCE_RATIO is 0.5
        
        # Good ratio (600 workers / 1000 pop = 0.6)
        penalty = calculate_production_penalty(workers=600, population=1000)
        assert penalty == 1.0
        
        # Bad ratio (300 workers / 1000 pop = 0.3)
        # Should be scaled: 0.3 / 0.5 = 0.6
        penalty = calculate_production_penalty(workers=300, population=1000)
        assert penalty == pytest.approx(0.6)
        
    def test_penalty_handles_zero_population(self):
        """Zero population results in 0.0 penalty (no production)."""
        penalty = calculate_production_penalty(workers=0, population=0)
        assert penalty == 0.0

    def test_tax_collection_aggregates_provinces(self):
        """Tax collection sums revenue from all provinces."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Set tax revenue
        expected_total = 0.0
        for p_id in nation.province_ids:
            world.provinces[p_id].tax_revenue = 10.0
            expected_total += 10.0
            
        total_tax = calculate_tax_collection(nation, world)
        assert total_tax == pytest.approx(expected_total)
