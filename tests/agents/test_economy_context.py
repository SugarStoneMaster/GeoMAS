
import pytest
from geomas.agents.context.input.economy import EconomyInputBuilder
from geomas.world import generate_world

def test_economy_context_welfare_costs():
    """Verify that INVEST_WELFARE cost description includes Materials."""
    # 1. Setup
    world = generate_world(seed=42, n_cells=20, n_nations=1)
    nation_id = list(world.nations.keys())[0]
    builder = EconomyInputBuilder(world)
    from geomas.agents.context.system.economy import EconomySystemPrompt
    from geomas.agents.schemas import GlobalStrategy
    
    # 2. Build Context
    user_prompt = builder.build(nation_id=nation_id, turn=1)
    system_prompt = EconomySystemPrompt.generate(
        nation_name=world.nations[nation_id].name,
        strategy=GlobalStrategy.COALITION_BUILDER,
        nation_id=nation_id
    )
    
    # 3. Assertions
    # Tool info is now in SYSTEM prompt
    assert "INVEST_WELFARE" in system_prompt
    assert "Budgets & Materials" in system_prompt or "Budget" in system_prompt

    # Input prompt should have Treasury
    assert "Treasury" in user_prompt
    
    # Check that warning is NOT present (as per user request)
    assert "Critical: Insufficient materials" not in user_prompt
