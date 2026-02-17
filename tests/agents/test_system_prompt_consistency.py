
import pytest
from geomas.world.generation.generator import generate_world
from geomas.agents.context.system import DefenseSystemPrompt, EconomySystemPrompt, ForeignSystemPrompt, PresidentSystemPrompt
from geomas.agents.schemas import GlobalStrategy
from geomas.schemas.world import NationState

def test_system_prompt_consistency():
    """Verify that system prompts remain 100% static across turns/state changes."""
    
    # 1. Setup World
    world = generate_world(seed=42, n_cells=50, n_nations=2)
    nation_id = list(world.nations.keys())[0]
    nation = world.nations[nation_id]
    
    # Ensure cultural traits exist and are varied
    nation.cultural_traits = ["Stoic", "Aggressive", "Maritime"]
    strategy = GlobalStrategy.TOTAL_EXPANSIONISM

    # 2. Generate Initial Prompts
    def_1 = DefenseSystemPrompt.generate(nation.name, strategy, nation_id=nation_id)
    eco_1 = EconomySystemPrompt.generate(nation.name, strategy, nation_id=nation_id)
    for_1 = ForeignSystemPrompt.generate(nation.name, strategy, nation_id=nation_id)
    pres_1 = PresidentSystemPrompt.generate(nation.name, strategy, nation.cultural_traits, nation_id=nation_id)

    # 3. Mutate World State (Simulate game progression)
    world.turn = 10
    nation.total_budget = 999999
    nation.public_satisfaction = 10.0 # Crisis
    nation.active_wars = {"FAIL": "WAR"}
    
    # Shuffle cultural traits to test order stability (if applicable)
    # Note: If the code doesn't sort, this WILL break consistency
    nation.cultural_traits = ["Maritime", "Stoic", "Aggressive"] # Different order

    # 4. Generate New Prompts
    def_2 = DefenseSystemPrompt.generate(nation.name, strategy, nation_id=nation_id)
    eco_2 = EconomySystemPrompt.generate(nation.name, strategy, nation_id=nation_id)
    for_2 = ForeignSystemPrompt.generate(nation.name, strategy, nation_id=nation_id)
    pres_2 = PresidentSystemPrompt.generate(nation.name, strategy, nation.cultural_traits, nation_id=nation_id)

    # 5. Assert Equality
    assert def_1 == def_2, "Defense Prompt changed! Caching broken."
    assert eco_1 == eco_2, "Economy Prompt changed! Caching broken."
    assert for_1 == for_2, "Foreign Prompt changed! Caching broken."
    
    # President traits check
    # If traits are simply joined, order matters.
    # The President prompt includes traits.
    if pres_1 != pres_2:
        print("\n[FAIL] President Prompt Consistency Broken!")
        print("Diff (Traits?):")
        print(f"Old: ...{pres_1[50:150]}...")
        print(f"New: ...{pres_2[50:150]}...")
        pytest.fail("President Prompt changed due to trait order! Caching broken.")

    print("\nSUCCESS: All System Prompts are static.")

if __name__ == "__main__":
    test_system_prompt_consistency()
