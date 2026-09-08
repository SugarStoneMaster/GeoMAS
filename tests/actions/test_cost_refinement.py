
import pytest
import math
from geomas.schemas.world import WorldState, NationState, TerrainType, ProvinceState
from geomas.actions.engine import ActionEngine
from geomas.actions.economy.schemas import EconomicActionType, EconomicPayload
from geomas.actions.economy.handler import execute_economic
from geomas.calculators.consumption import (
    calculate_energy_consumption,
    ENERGY_MAINTENANCE_AIRCRAFT,
    ENERGY_MAINTENANCE_NAVY
)

@pytest.fixture
def world_with_nation():
    w = WorldState(turn=1)
    n = NationState(
        id="NAT_EX",
        name="Example",
        color="green",
        total_budget=1000,
        total_materials=1000,
        total_energy=1000,
        total_population=100000, # 100k pop
        public_satisfaction=50
    )
    w.nations["NAT_EX"] = n
    return w

class TestEconomyRefinement:
    def test_war_tax_rebalanced_revenue(self, world_with_nation):
        """War tax should give 1% of population in budget."""
        engine = ActionEngine(world_with_nation)
        nation = world_with_nation.nations["NAT_EX"]
        initial_budget = nation.total_budget
        
        payload = EconomicPayload(action_type=EconomicActionType.RAISE_WAR_TAX)
        execute_economic(engine, "NAT_EX", payload)
        
        # 100,000 * 0.01 = 1,000
        assert nation.total_budget == initial_budget + 1000
        assert nation.public_satisfaction == 50 - 15 # Base penalty

    def test_war_tax_dynamic_penalty(self, world_with_nation):
        """War tax penalty should be higher if satisfaction is low (< 30)."""
        engine = ActionEngine(world_with_nation)
        nation = world_with_nation.nations["NAT_EX"]
        nation.public_satisfaction = 25
        
        payload = EconomicPayload(action_type=EconomicActionType.RAISE_WAR_TAX)
        execute_economic(engine, "NAT_EX", payload)
        
        # 15 * 1.5 = 22.5
        assert nation.public_satisfaction == 25 - 22.5

    def test_invest_welfare_requires_materials(self, world_with_nation):
        """Welfare investment should fail if materials are missing."""
        engine = ActionEngine(world_with_nation)
        nation = world_with_nation.nations["NAT_EX"]
        nation.total_materials = 5 # Needs 20 for 100 budget investment
        
        payload = EconomicPayload(action_type=EconomicActionType.INVEST_WELFARE, amount=100)
        execute_economic(engine, "NAT_EX", payload)
        
        # Should fail and logs should contain reason
        assert nation.total_budget == 1000 # Unchanged
        assert any("Insufficient materials" in l for l in engine.logs)

    def test_invest_welfare_deducts_materials(self, world_with_nation):
        """Welfare investment should deduct 20% of budget in materials."""
        engine = ActionEngine(world_with_nation)
        nation = world_with_nation.nations["NAT_EX"]
        
        payload = EconomicPayload(action_type=EconomicActionType.INVEST_WELFARE, amount=100)
        execute_economic(engine, "NAT_EX", payload)
        
        assert nation.total_budget == 900
        assert nation.total_materials == 1000 - 20 # 100 * 0.2
        assert nation.public_satisfaction > 50

class TestUpkeepRefinement:
    def test_energy_maintenance_includes_military(self, world_with_nation):
        """Energy consumption should include fuel for ships and planes."""
        nation = world_with_nation.nations["NAT_EX"]
        nation.total_aircraft = 10
        nation.total_navy = 5
        
        # Pop: 100,000 * 0.5 = 50,000
        # Aircraft: 10 * 5 = 50
        # Navy: 5 * 3 = 15
        expected = 50000 + 50 + 15
        
        actual = calculate_energy_consumption(
            nation.total_population,
            total_aircraft=nation.total_aircraft,
            total_navy=nation.total_navy
        )
        
        assert actual == expected
