"""
Tests for the economy module.
"""

import pytest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from geomas import calculators as economy
from geomas.schemas.world import WorldState, NationState, ProvinceState, TerrainType


# --- FIXTURES ---

@pytest.fixture
def sample_nation():
    """Creates a sample nation for testing."""
    return NationState(
        id="TEST",
        name="Test Nation",
        color="#FF0000",
        province_ids=[1, 2, 3],
        total_budget=1000.0,
        total_food=500.0,
        total_energy=300.0,
        total_materials=200.0,
        total_population=10000,
        total_soldiers=500,
        total_aircraft=10,
        total_navy=20,
        nukes=0,
        public_satisfaction=0.5
    )


@pytest.fixture
def sample_world(sample_nation):
    """Creates a sample world with provinces."""
    provinces = {
        1: ProvinceState(
            id=1, owner_id="TEST", terrain=TerrainType.LAND,
            coordinates=(0.5, 0.5), population=4000, workers=3800, soldiers=200,
            food_production=100.0, energy_production=50.0, materials_production=30.0,
            tax_revenue=400.0
        ),
        2: ProvinceState(
            id=2, owner_id="TEST", terrain=TerrainType.COASTAL,
            coordinates=(0.6, 0.5), population=4000, workers=3700, soldiers=300,
            food_production=120.0, energy_production=40.0, materials_production=20.0,
            tax_revenue=400.0
        ),
        3: ProvinceState(
            id=3, owner_id="TEST", terrain=TerrainType.MOUNTAIN,
            coordinates=(0.4, 0.5), population=2000, workers=2000, soldiers=0,
            food_production=30.0, energy_production=20.0, materials_production=80.0,
            tax_revenue=200.0
        ),
    }
    
    return WorldState(
        turn=1,
        provinces=provinces,
        nations={"TEST": sample_nation},
        trust_matrix={}
    )


# --- CONSUMPTION TESTS ---

class TestConsumption:
    def test_food_consumption(self):
        """1 food per person per turn."""
        assert economy.calculate_food_consumption(1000) == 1000.0
        assert economy.calculate_food_consumption(0) == 0.0
        assert economy.calculate_food_consumption(12345) == 12345.0
    
    def test_energy_consumption(self):
        """0.5 energy per person per turn."""
        assert economy.calculate_energy_consumption(1000) == 500.0
        assert economy.calculate_energy_consumption(0) == 0.0
        assert economy.calculate_energy_consumption(100) == 50.0
    
    def test_materials_consumption(self):
        """Military maintenance costs."""
        # soldiers=0.1, aircraft=2.0, navy=1.5 per unit
        consumption = economy.calculate_materials_consumption(
            total_soldiers=100,
            total_aircraft=10,
            total_navy=20
        )
        expected = 100 * 0.1 + 10 * 2.0 + 20 * 1.5  # 10 + 20 + 30 = 60
        assert consumption == expected


# --- PRODUCTION TESTS ---

class TestProduction:
    def test_production_penalty_full_workforce(self):
        """No penalty when workforce ratio >= 50%."""
        # 100% workforce
        assert economy.calculate_production_penalty(workers=1000, population=1000) == 1.0
        # Exactly 50%
        assert economy.calculate_production_penalty(workers=500, population=1000) == 1.0
        # 60% workforce
        assert economy.calculate_production_penalty(workers=600, population=1000) == 1.0
    
    def test_production_penalty_low_workforce(self):
        """Penalty when workforce ratio < 50%."""
        # 25% workforce -> 0.5 penalty
        penalty = economy.calculate_production_penalty(workers=250, population=1000)
        assert penalty == pytest.approx(0.5)
        
        # 0% workforce -> 0 penalty
        penalty = economy.calculate_production_penalty(workers=0, population=1000)
        assert penalty == 0.0
    
    def test_production_penalty_zero_population(self):
        """Zero population returns 0 penalty."""
        assert economy.calculate_production_penalty(workers=0, population=0) == 0.0


# --- TAX COLLECTION TESTS ---

class TestTaxCollection:
    def test_tax_collection(self, sample_nation, sample_world):
        """Tax collection sums all province tax revenues."""
        total_tax = economy.calculate_tax_collection(sample_nation, sample_world)
        expected = 400.0 + 400.0 + 200.0  # From 3 provinces
        assert total_tax == expected
    
    def test_tax_collection_no_provinces(self, sample_world):
        """Nation with no provinces collects 0 tax."""
        empty_nation = NationState(id="EMPTY", name="Empty", color="#000", province_ids=[])
        assert economy.calculate_tax_collection(empty_nation, sample_world) == 0.0


# --- AGGREGATES TESTS ---

class TestAggregates:
    def test_calculate_nation_aggregates(self, sample_nation, sample_world):
        """Aggregates sum province values correctly."""
        aggregates = economy.calculate_nation_aggregates(sample_nation, sample_world)
        
        assert aggregates["total_population"] == 4000 + 4000 + 2000
        assert aggregates["total_soldiers"] == 200 + 300 + 0
        assert aggregates["total_food_production"] == 100.0 + 120.0 + 30.0
        assert aggregates["total_energy_production"] == 50.0 + 40.0 + 20.0
        assert aggregates["total_materials_production"] == 30.0 + 20.0 + 80.0


# --- POWER PROJECTION TESTS ---

class TestPowerProjection:
    def test_power_projection_basic(self, sample_nation):
        """Power projection is weighted sum of resources and military."""
        score = economy.calculate_power_projection(sample_nation)
        
        # Expected calculation with weights from economy.py
        expected = (
            1000.0 * 0.001 +  # budget
            500.0 * 0.01 +   # food
            300.0 * 0.02 +   # energy
            200.0 * 0.03 +   # materials
            500 * 0.1 +      # soldiers
            10 * 0.5 +       # aircraft
            20 * 0.3 +       # navy
            0 * 50.0         # nukes
        )
        assert score == pytest.approx(round(expected, 2))
    
    def test_power_projection_with_nukes(self, sample_nation):
        """Nukes significantly boost power projection."""
        sample_nation.nukes = 5
        score_with_nukes = economy.calculate_power_projection(sample_nation)
        
        sample_nation.nukes = 0
        score_without_nukes = economy.calculate_power_projection(sample_nation)
        
        # 5 nukes * 50.0 weight = 250 extra points
        assert score_with_nukes - score_without_nukes == pytest.approx(250.0)


# --- STARVATION TESTS ---

class TestStarvation:
    def test_starvation_no_deficit(self):
        """No casualties when food balance is positive."""
        assert economy.calculate_starvation_casualties(food_deficit=100.0, total_population=10000) == 0
    
    def test_starvation_with_deficit(self):
        """Casualties occur when food deficit exists."""
        # Deficit of -100 with population 10000
        casualties = economy.calculate_starvation_casualties(food_deficit=-100.0, total_population=10000)
        assert casualties > 0
        assert casualties < 1000  # Capped at 10%


# --- ENERGY PENALTY TESTS ---

class TestEnergyPenalty:
    def test_energy_penalty_no_deficit(self):
        """No penalty when energy balance is positive."""
        assert economy.calculate_energy_penalty(energy_deficit=50.0) == 1.0
    
    def test_energy_penalty_with_deficit(self):
        """Penalty when energy deficit exists."""
        penalty = economy.calculate_energy_penalty(energy_deficit=-50.0)
        assert 0.5 <= penalty < 1.0


# --- RESOURCE BALANCE TESTS ---

class TestResourceBalance:
    def test_resource_balance(self, sample_nation, sample_world):
        """Net balance = production - consumption."""
        balance = economy.calculate_resource_balance(sample_nation, sample_world)
        
        # Food: production - population
        assert "food_balance" in balance
        assert "energy_balance" in balance
        assert "materials_balance" in balance
