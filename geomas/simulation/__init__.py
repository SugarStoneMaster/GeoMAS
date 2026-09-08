"""
Simulation Package — The Orchestration Layer.

Contains the core simulation loop and turn management. The SimulationEngine
is the main entry point that initializes the world, creates agents, and
runs the deterministic turn loop.

Modules:
    - engine.py (SimulationEngine, 979 lines): The central orchestrator.
      Initialization: generate_world(seed) → create NationAgents with
        LLMClient → assign GlobalStrategy + GovernmentType → set initial
        nuke allocation based on strategy profile → initialize ContextManager.
      Turn Loop (7 phases executed in strict order each turn):
        1. SCENARIO: Apply mid-simulation events (pandemic, discovery, etc.).
        2. UPKEEP: Tax collection, production (unified multiplier),
           consumption, resource capping (max = 10× consumption),
           spoilage, starvation casualties, energy penalties.
        3. DIPLOMACY CLEANUP: Expire old pending proposals (>1 turn).
        4. AGENT DECISION + EXECUTION: NationAgent.act() → CountryEnvelope
           → ActionEngine (defense waterfall → economy → foreign).
        5. AMBIGUITY PENALTY: -2 trust for public IDLE + private non-IDLE.
        6. CONTEXT UPDATE: Refresh relationships, extract events, log actions.
        7. OPINION PHASE: OpinionAgent.react() → satisfaction deltas →
           trigger checks (strike, civil unrest, recovery).
      State Forking: Checkpoint + fork from any turn for counterfactual XAI.
      Persistence: Serialize + save snapshot + envelopes + metrics each turn.

    - phases.py (274 lines): Turn phase implementations.
      upkeep_phase(): Tax, production (multiplied), consumption, resource
        capping at 10× consumption, crisis (starvation, energy penalty).
      opinion_phase(): Post-execution satisfaction update with LLM
        multipliers, trigger checks (STRIKE, CIVIL_UNREST, RECOVERY).

    - scenarios.py (343 lines): Mid-simulation event scenarios.
      PANDEMIC: Population × (1 - mortality_rate), satisfaction -20.
      RESOURCE_DISCOVERY: +50% production for specified resource.
      SEPARATIST_INSURRECTION: Province revolts, production halved.

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
