
import pytest
from geomas.agents.context.input.economy import EconomyInputBuilder
from geomas.world import generate_world

def test_economy_context_welfare_costs():
    """Verify that INVEST_WELFARE cost description includes Materials."""
    # 1. Setup
    world = generate_world(seed=42, n_cells=20, n_nations=1)
    nation_id = list(world.nations.keys())[0]
    builder = EconomyInputBuilder(world)
    
    # 2. Build Context
    prompt = builder.build(nation_id=nation_id, turn=1)
    
    # 3. Assertions
    print(prompt) # For debug
    
    # Check for Cost Description
    assert "INVEST_WELFARE" in prompt
    assert "Budget + Materials" in prompt
    assert "20% of Budget" in prompt or "Materials = 20%" in prompt
    
    # Check that warning is NOT present (as per user request)
    assert "Critical: Insufficient materials" not in prompt
