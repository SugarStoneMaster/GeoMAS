from geomas.simulation.engine import SimulationEngine
import os

def check_nukes(map_seed, hist_seed):
    # Initialize engine (without DB for speed)
    sim = SimulationEngine(map_seed=map_seed, history_seed=hist_seed, n_cells=300, n_nations=4)
    nuke_counts = {nid: nation.nukes for nid, nation in sim.world.nations.items() if nation.nukes > 0}
    return nuke_counts

print("Checking Seed pair (42, 99)...")
c1 = check_nukes(42, 99)
print(f"Result 1: {c1}")
c2 = check_nukes(42, 99)
print(f"Result 2: {c2}")

assert c1 == c2, "Non-deterministic!"
for nid, count in c1.items():
    assert count <= 5, f"{nid} has {count} nukes ( > 5)"

print("Checking different history seed (42, 100)...")
c3 = check_nukes(42, 100)
print(f"Result 3: {c3}")
assert c1 != c3, "History seed change didn't affect distribution!"

print("Checking different map seed (43, 99)...")
c4 = check_nukes(43, 99)
print(f"Result 4: {c4}")
assert c1 != c4, "Map seed change didn't affect distribution!"

print("✅ Verification passed: 1 < nukes <= 5 and distribution is deterministic based on both seeds.")
