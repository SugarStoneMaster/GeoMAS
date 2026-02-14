
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from geomas.world.generation.generator import MapGenerator
from geomas.agents.context.input.defense import DefenseInputBuilder
from geomas.schemas.world import TerrainType
from geomas.actions.defense.schemas import UnitType

def debug_defense_prompt():
    print("--- 🛠️ DEBUGGING DEFENSE CONTEXT ---")
    
    # 1. Setup minimal world
    print("Generating world...")
    generator = MapGenerator(seed=42, n_cells=500, n_nations=5, relaxation_steps=1)
    world = generator.generate(history_seed=99)
    
    # Pick a nation
    nation_ids = list(world.nations.keys())
    if not nation_ids:
        print("No nations found!")
        return

    # Sort nations by unit count to get one with units
    best_nation = None
    max_units = -1
    
    for nid in nation_ids:
        n = world.nations[nid]
        u_count = n.total_soldiers + n.total_navy + n.total_aircraft
        if u_count > max_units:
            max_units = u_count
            best_nation = nid
            
    target_nation_id = best_nation
    print(f"Selected Nation: {target_nation_id} ({world.nations[target_nation_id].name})")
    
    # 2. Add some specific test scenarios
    # Add a soldier near ocean
    nation = world.nations[target_nation_id]
    p_ids = sorted(nation.province_ids)
    
    # Find a coastal province
    coastal_prov = None
    for pid in p_ids:
        p = world.provinces[pid]
        if p.terrain == TerrainType.COASTAL:
            coastal_prov = p
            break
            
    if coastal_prov:
        print(f"Injecting SOLDIER at Coastal Province {coastal_prov.id} to test Ocean filtering...")
        coastal_prov.soldiers += 100
        nation.total_soldiers += 100
    
    # 3. Generate Prompt
    builder = DefenseInputBuilder(world)
    prompt = builder.build(target_nation_id, turn=15, recent_actions=["Moved troops", "Recruited soldiers"])
    
    print("\n" + "="*40)
    print("GENERATED PROMPT:")
    print("="*40)
    print(prompt)
    print("="*40)
    
    # 4. Analysis
    print("\n--- ANALYSIS ---")
    print(f"Total Length (chars): {len(prompt)}")
    print(f"Est. Tokens: {len(prompt)/4:.0f}")
    
    if "❌SEA" in prompt:
        print("✅ Found explicit SEA warnings (or old logic leftovers).")
    else:
        print("ℹ️ No explicit SEA warnings found (Clean filtering applied).")

    # Check for VOID
    if "VOID" in prompt:
        print("❌ WARNING: 'VOID' keyword found in prompt!")
    else:
        print("✅ No 'VOID' references found.")

if __name__ == "__main__":
    debug_defense_prompt()
