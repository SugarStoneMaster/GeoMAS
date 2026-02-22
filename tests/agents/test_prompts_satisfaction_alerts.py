"""
Verification test for Critical Satisfaction and Unrest Alerts in Prompts.
"""

import pytest
from geomas.world import generate_world
from geomas.agents.context.input.economy import EconomyInputBuilder
from geomas.agents.context.input.president import PresidentInputBuilder
from geomas.agents.context.input.defense import DefenseInputBuilder
from geomas.agents.context.input.foreign import ForeignInputBuilder

class TestPromptAlerts:
    """Tests that critical alerts appear in prompts based on satisfaction levels."""

    @pytest.fixture
    def setup(self):
        """Standard setup for prompt tests."""
        world = generate_world(seed=42, n_cells=50, n_nations=1)
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        return world, nation_id, nation

    def test_economy_alerts_unrest(self, setup):
        """Alerts appear in Economy prompt during Civil Unrest."""
        world, nation_id, nation = setup
        nation.public_satisfaction = 5.0
        nation.civil_unrest_active = True
        
        builder = EconomyInputBuilder(world)
        prompt = builder.build(nation_id, turn=1)
        
        assert "## CRITICAL ALERTS" in prompt
        assert "CIVIL UNREST ACTIVE" in prompt
        assert "Total production and recruitment halt" in prompt

    def test_president_alerts_strike(self, setup):
        """Alerts appear in President prompt during General Strike."""
        world, nation_id, nation = setup
        nation.public_satisfaction = 15.0
        nation.civil_unrest_active = False
        
        builder = PresidentInputBuilder(world)
        prompt = builder.build(nation_id, turn=1)
        
        assert "## CRITICAL ALERTS" in prompt
        assert "GENERAL STRIKE" in prompt
        assert "Economy is paralyzed" in prompt

    def test_defense_alerts_decay(self, setup):
        """Alerts appear in Defense prompt during Production Decay."""
        world, nation_id, nation = setup
        nation.public_satisfaction = 40.0
        nation.civil_unrest_active = False
        
        builder = DefenseInputBuilder(world)
        prompt = builder.build(nation_id, turn=1)
        
        assert "## CRITICAL ALERTS" in prompt
        assert "PRODUCTION DECAY" in prompt
        assert "Current efficiency: 88%" in prompt # 0.5 + (30/40)*0.5 = 0.5 + 0.375 = 0.875 -> 88%

    def test_foreign_alerts_shortage(self, setup):
        """Alerts appear in Foreign prompt during resource shortages."""
        world, nation_id, nation = setup
        nation.public_satisfaction = 80.0 # High satisfaction
        nation.total_food = 20.0 # Shortage
        
        builder = ForeignInputBuilder(world)
        prompt = builder.build(nation_id, turn=1)
        
        assert "## CRITICAL ALERTS" in prompt
        assert "SHORTAGE ALERT: FOOD" in prompt

    def test_no_alerts_when_stable(self, setup):
        """No alerts appear when nation is stable."""
        world, nation_id, nation = setup
        nation.public_satisfaction = 70.0
        nation.total_food = 500.0
        nation.total_energy = 500.0
        nation.total_materials = 500.0
        nation.civil_unrest_active = False
        
        builder = EconomyInputBuilder(world)
        prompt = builder.build(nation_id, turn=1)
        
        assert "## CRITICAL ALERTS" not in prompt
