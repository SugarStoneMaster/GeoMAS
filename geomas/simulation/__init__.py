"""
Simulation Package.

The main simulation loop and phase logic.

Modules:
    - engine: SimulationEngine class that orchestrates the simulation
    - phases: Turn phase implementations (upkeep, economy updates)

The SimulationEngine manages:
    1. World initialization (via generate_world)
    2. Agent initialization (one NationAgent per nation)
    3. Turn execution loop:
        a. Upkeep Phase: Resource consumption, production, crisis handling
        b. Agent Phase: Each agent decides actions
        c. Execution Phase: Actions are validated and applied

Example:
    from geomas.simulation import SimulationEngine
    
    sim = SimulationEngine(map_seed=42, history_seed=99, n_cells=1500)
    sim.run(steps=10)
    
    # Access simulation state
    print(sim.world.turn)
    print(sim.turn_logs)
"""

from geomas.simulation.engine import SimulationEngine

__all__ = ["SimulationEngine"]
