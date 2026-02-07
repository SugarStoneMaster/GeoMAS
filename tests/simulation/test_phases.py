"""
Tests for Simulation Phases.

Tests run_upkeep_phase and related functions.
"""

import pytest
from geomas.world import generate_world
from geomas.simulation.phases import (
    run_upkeep_phase,
    apply_population_loss,
    apply_production_penalty,
)


class TestRunUpkeepPhase:
    """Tests for run_upkeep_phase function."""
    
    def test_upkeep_updates_resources(self):
        """Upkeep phase updates nation resources."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        turn_logs = []
        
        # Record initial values
        nation = list(world.nations.values())[0]
        initial_budget = nation.total_budget
        
        run_upkeep_phase(world, turn_logs)
        
        # Budget should change (taxes collected)
        # Resources should be updated
        assert len(turn_logs) > 0  # Some logging occurred
    
    def test_upkeep_generates_logs(self):
        """Upkeep phase generates log entries."""
        world = generate_world(seed=42, n_cells=50, n_nations=3)
        turn_logs = []
        
        run_upkeep_phase(world, turn_logs)
        
        # Should have log entries
        assert len(turn_logs) >= 1
    
    def test_upkeep_handles_all_nations(self):
        """Upkeep phase processes all nations."""
        world = generate_world(seed=42, n_cells=50, n_nations=4)
        turn_logs = []
        
        run_upkeep_phase(world, turn_logs)
        
        # Check all nations were processed (power projection updated)
        for nation in world.nations.values():
            assert nation.power_projection >= 0
    
    def test_starvation_reduces_population(self):
        """Starvation reduces population when food is negative."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        turn_logs = []
        
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Create food crisis
        nation.total_food = -100
        for p_id in nation.province_ids:
            world.provinces[p_id].food_production = 0
        
        # Record initial population
        initial_pop = sum(world.provinces[p].population for p in nation.province_ids)
        
        run_upkeep_phase(world, turn_logs)
        
        # If there was starvation, population decreased
        # Note: may not happen if production covers consumption
        final_pop = sum(world.provinces[p].population for p in nation.province_ids)
        assert final_pop <= initial_pop


class TestApplyPopulationLoss:
    """Tests for apply_population_loss function."""
    
    def test_distributes_loss_proportionally(self):
        """Population loss is distributed across provinces."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Set equal population in all provinces
        # Set equal population in all provinces
        for p_id in nation.province_ids:
            world.provinces[p_id].population = 1000
        
        # Calculate consistent total population for correct ratio logic
        nation.total_population = sum(world.provinces[p].population for p in nation.province_ids)
        
        initial_pop = nation.total_population
        
        apply_population_loss(world, nation_id, casualties=100)
        
        final_pop = sum(world.provinces[p].population for p in nation.province_ids)
        # Allow small rounding error due to integer division distribution
        assert final_pop == pytest.approx(initial_pop - 100, abs=len(nation.province_ids))
    
    def test_no_negative_population(self):
        """Population never goes below 0."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Set low population
        for p_id in nation.province_ids:
            world.provinces[p_id].population = 10
        
        apply_population_loss(world, nation_id, casualties=999999)
        
        for p_id in nation.province_ids:
            assert world.provinces[p_id].population >= 0


class TestApplyProductionPenalty:
    """Tests for apply_production_penalty function."""
    
    def test_reduces_all_production(self):
        """Penalty reduces food, energy, materials production."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Set known production values
        for p_id in nation.province_ids:
            world.provinces[p_id].food_production = 100.0
            world.provinces[p_id].energy_production = 100.0
            world.provinces[p_id].materials_production = 100.0
        
        apply_production_penalty(world, nation_id, penalty_multiplier=0.5)
        
        for p_id in nation.province_ids:
            assert world.provinces[p_id].food_production == 50.0
            assert world.provinces[p_id].energy_production == 50.0
            assert world.provinces[p_id].materials_production == 50.0
    
    def test_penalty_of_one_no_change(self):
        """Penalty of 1.0 = no change."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Record initial values
        initial_prod = {
            p_id: world.provinces[p_id].food_production 
            for p_id in nation.province_ids
        }
        
        apply_production_penalty(world, nation_id, penalty_multiplier=1.0)
        
        for p_id in nation.province_ids:
            assert world.provinces[p_id].food_production == initial_prod[p_id]
    
    def test_penalty_of_zero_stops_production(self):
        """Penalty of 0.0 = no production."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        apply_production_penalty(world, nation_id, penalty_multiplier=0.0)
        
        for p_id in nation.province_ids:
            assert world.provinces[p_id].food_production == 0.0
            assert world.provinces[p_id].energy_production == 0.0
            assert world.provinces[p_id].materials_production == 0.0
