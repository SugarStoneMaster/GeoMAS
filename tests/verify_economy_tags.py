
import sys
import os

# --- PATH FIX ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../"))
if project_root not in sys.path:
    sys.path.append(project_root)

from geomas.schemas.world import WorldState, NationState, ProvinceState, TerrainType
from geomas.agents.context.input.economy import EconomyInputBuilder

def test_economy_prompt_tags():
    # 1. Setup Mock World
    p1 = ProvinceState(id=1, owner_id="N1", terrain=TerrainType.LAND, coordinates=(0,0))
    p2 = ProvinceState(id=2, owner_id="N2", terrain=TerrainType.LAND, coordinates=(1,1))
    
    n1 = NationState(id="N1", name="Nation 1", color="blue", province_ids=[1], total_food=1000)
    n2 = NationState(id="N2", name="Nation 2", color="red", province_ids=[2], total_food=10) # Needs food
    n3 = NationState(id="N3", name="Nation 3", color="green", province_ids=[3], total_food=500) # Average shifter
    
    world = WorldState(
        turn=5,
        provinces={1: p1, 2: p2, 3: p1}, # Province IDs don't matter much for this test
        nations={"N1": n1, "N2": n2, "N3": n3},
        trust_matrix={"N1": {"N2": 10.0, "N3": 80.0}}, # LOW TRUST for N2, HIGH for N3
        relationship_matrix={"N1": {"N2": "PEACE", "N3": "PEACE"}}
    )
    
    # 2. Build Prompt
    builder = EconomyInputBuilder(world)
    prompt = builder.build(nation_id="N1", turn=5)
    
    print("--- GENERATED PROMPT SNIPPET ---")
    if "[NO TRADE - Trust too low or War]" in prompt:
        print("SUCCESS: Found 'NO TRADE' tag in relationships.")
    else:
        print("FAILURE: 'NO TRADE' tag missing in relationships.")
        
    if "❌ [NO TRADE - Trust too low or War]" in prompt:
        print("SUCCESS: Found 'NO TRADE' tag in market intelligence.")
    else:
        print("FAILURE: 'NO TRADE' tag missing in market intelligence.")

    # High Trust test
    world.trust_matrix["N1"]["N2"] = 80.0
    prompt_high = builder.build(nation_id="N1", turn=5)
    
    if "[TRADE ELIGIBLE]" in prompt_high:
        print("SUCCESS: Found 'TRADE ELIGIBLE' tag in relationships.")
    else:
        print("FAILURE: 'TRADE ELIGIBLE' tag missing in relationships.")
        
    if "✅ [TRADE ELIGIBLE]" in prompt_high:
        print("SUCCESS: Found 'TRADE ELIGIBLE' tag in market intelligence.")
    else:
        print("FAILURE: 'TRADE ELIGIBLE' tag missing in market intelligence.")

if __name__ == "__main__":
    test_economy_prompt_tags()
