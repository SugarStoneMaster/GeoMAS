"""
Test Initial Resources.

Verifies that nations start with adequate resources (Budget, Food, Energy, Materials)
proportional to their population/economy, preventing the "Turn 1 Poverty" issue.
"""

import pytest
from geomas.world.generation.generator import generate_world

def test_initial_budget_consistency():
    """
    Test that initial budget is roughly 5x daily tax revenue, 
    not a trivial amount like 2000.
    """
    # Generate a small world
    world = generate_world(seed=42, n_cells=100, n_nations=2)
    
    for nation_id, nation in world.nations.items():
        # Calculate expected daily tax
        # From provinces.py: sum(pop * 1.0)
        daily_tax = sum(
            world.provinces[p_id].tax_revenue 
            for p_id in nation.province_ids
        )
        
        print(f"Nation {nation_id}: Pop {nation.total_population}, Tax {daily_tax}, Budget {nation.total_budget}")
        
        # Check that budget is at least 3x daily tax (allowing for prosperity variance 0.7-1.3 * 5 turns)
        # 0.7 * 5 = 3.5. So > 3x is a safe lower bound.
        assert nation.total_budget > daily_tax * 3.0, \
            f"Budget {nation.total_budget} is too low compared to tax {daily_tax}"
            
        # Also check hard minimum
        assert nation.total_budget >= 5000

def test_initial_stockpiles():
    """Test that food/energy/materials are also initialized."""
    world = generate_world(seed=42, n_cells=100, n_nations=2)
    
    for nation_id, nation in world.nations.items():
        assert nation.total_food > 0
        assert nation.total_energy > 0
        assert nation.total_materials >= 100
