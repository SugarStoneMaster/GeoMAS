import sys
import os
import numpy as np
from scipy.optimize import differential_evolution

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from geomas.world.world_engine import generate_world
from geomas.core.genesis import GenesisEngine

# TARGET DISTRIBUTION
TARGET_HIGH = 0.15  # > 0.8
TARGET_LOW = 0.20   # < 0.2
TARGET_MID = 0.65   # 0.2 - 0.8

def objective_function(params):
    """
    Evaluates a set of parameters by running a simulation and comparing
    the resulting Trust Matrix distribution to the target.
    """
    # Unpack params
    config = {
        "base_friction": params[0],
        "trade_bonus": params[1],
        "conflict_penalty": params[2],
        "alliance_threshold": params[3],
        "rivalry_threshold": params[4],
        "decay_rate": params[5],
        "resource_envy_penalty": params[6],
        "alliance_chance": params[7],
        "rivalry_chance": params[8]
    }
    
    # Run Simulation (Fast)
    # We use a fixed map seed but vary history seed slightly to average out noise?
    # Actually, let's use a fixed seed for stability during optimization step.
    # We generate the world WITHOUT running genesis inside map_engine first.
    # Wait, map_engine runs genesis by default. We need to instantiate Genesis manually.
    
    # Hack: We generate a world with 0 years history to get the map, then run our own Genesis.
    # But map_engine doesn't support 0 years arg exposed.
    # Let's just instantiate GenesisEngine directly on a pre-generated world.
    
    # Generate a base world ONCE (global variable would be faster but let's be safe)
    # For speed, we use a smaller resolution
    world = generate_world(seed=42, history_seed=0, n_cells=500, n_nations=10)
    
    # Reset Trust Matrix (map_engine might have initialized it)
    # GenesisEngine.__init__ handles logic, but initialize_history resets it.
    
    genesis = GenesisEngine(world, seed=123, config=config)
    genesis.initialize_history(years=50)
    
    # Analyze Distribution
    trust_values = []
    nation_ids = list(world.nations.keys())
    for i in range(len(nation_ids)):
        for j in range(i + 1, len(nation_ids)):
            val = world.trust_matrix[nation_ids[i]][nation_ids[j]]
            trust_values.append(val)
            
    total = len(trust_values)
    if total == 0: return 999.0
    
    count_high = sum(1 for v in trust_values if v > 0.8)
    count_low = sum(1 for v in trust_values if v < 0.2)
    count_mid = total - count_high - count_low
    
    ratio_high = count_high / total
    ratio_low = count_low / total
    ratio_mid = count_mid / total
    
    # Calculate Error (MSE)
    error = (ratio_high - TARGET_HIGH)**2 + \
            (ratio_low - TARGET_LOW)**2 + \
            (ratio_mid - TARGET_MID)**2
            
    return error

def optimize():
    print("Starting Genesis Optimization...")
    print(f"Targets: High={TARGET_HIGH}, Low={TARGET_LOW}, Mid={TARGET_MID}")
    
    # Bounds for parameters
    bounds = [
        (0.05, 0.30), # base_friction
        (0.01, 0.15), # trade_bonus
        (0.05, 0.30), # conflict_penalty
        (0.60, 0.90), # alliance_threshold
        (0.10, 0.40), # rivalry_threshold
        (0.001, 0.05), # decay_rate
        (0.01, 0.10), # resource_envy_penalty
        (0.05, 0.30), # alliance_chance
        (0.05, 0.30)  # rivalry_chance
    ]
    
    result = differential_evolution(
        objective_function, 
        bounds, 
        maxiter=10, # Keep it short for demo
        popsize=5,
        disp=True,
        workers=-1 # Parallelize
    )
    
    print("\n--- OPTIMIZATION COMPLETE ---")
    print("Best Parameters found:")
    names = [
        "base_friction", "trade_bonus", "conflict_penalty", 
        "alliance_threshold", "rivalry_threshold", "decay_rate",
        "resource_envy_penalty", "alliance_chance", "rivalry_chance"
    ]
    
    for name, val in zip(names, result.x):
        print(f'"{name}": {val:.4f},')
        
    print(f"\nFinal Error: {result.fun:.6f}")

if __name__ == "__main__":
    optimize()
