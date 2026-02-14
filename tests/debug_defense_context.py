
from geomas.world import generate_world
from geomas.agents.context.input.defense import DefenseInputBuilder
from geomas.agents.context.military import MilitaryTranslator
from geomas.schemas.world import TerrainType

def test_defense_context_output():
    """
    Generate and print the Defense Input Prompt for manual inspection.
    """
    # 1. Setup a world with some units
    world = generate_world(seed=42, n_cells=20, n_nations=2)
    nation_id = list(world.nations.keys())[0]
    
    # Add some interior units to test aggregation
    nation = world.nations[nation_id]
    
    # Mock some troops
    p_ids = sorted(nation.province_ids)
    if len(p_ids) > 3:
        # Border
        world.provinces[p_ids[0]].soldiers = 100
        # Interior
        world.provinces[p_ids[1]].soldiers = 50
        world.provinces[p_ids[2]].soldiers = 50 # Should be aggregated
        # Sea Neighbor setup (if possible in random gen, or mock it)
        
    builder = DefenseInputBuilder(world)
    prompt = builder.build(nation_id=nation_id, turn=1)
    
    print("\nXXX BEGIN PROMPT XXX\n")
    print(prompt)
    print("\nXXX END PROMPT XXX\n")

if __name__ == "__main__":
    test_defense_context_output()
