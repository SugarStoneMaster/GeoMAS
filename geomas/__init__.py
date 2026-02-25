"""
GeoMAS - Geopolitical Multi-Agent Simulation.

A deterministic, agent-based simulation framework for studying geopolitical
dynamics through AI-driven nation agents. Designed for academic research
(Master's Thesis) on deception, alliance formation, moral washing, and
strategic decision-making under resource constraints.

Architecture Overview:
    GeoMAS is organized into a clean layered architecture where data flows
    downward (Orchestration → Cognitive → Physical → Persistence) and each
    layer has strict responsibilities:

    1. ORCHESTRATION (geomas.simulation):
       SimulationEngine runs a 7-phase turn loop:
         Scenario → Upkeep → Diplomacy Cleanup → Agent Decision+Execution
         → Ambiguity Penalty → Context Update → Opinion Phase → Persist.
       Supports state forking for counterfactual analysis (XAI injection).

    2. COGNITIVE (geomas.agents):
       Hierarchical cabinet model: 3 Ministers (Defense, Economy, Foreign)
       propose actions concurrently via async LLM calls, the President LLM
       synthesizes (APPROVE/VETO) proposals into a CountryEnvelope.
       An OpinionAgent represents population reaction post-execution.
       All prompts are built via context/ sub-package (system + input builders).

    3. PHYSICAL (geomas.actions, geomas.calculators):
       The ActionEngine is the "Rules Oracle" — validates and executes
       actions deterministically. Defense uses a waterfall priority resolver
       (nukes → attacks → movements → unit creation). Economy handles
       welfare investment (log curve), war tax, and trade (oracle formula).
       Foreign handles war declarations, alliances, peace proposals, and
       diplomatic messaging with cooldown and trust impact.
       Calculators provide pure, stateless functions for production
       multipliers (workforce × satisfaction × energy), consumption rates,
       power projection scores, and crisis resolution (starvation, energy).

    4. WORLD (geomas.world):
       Procedural generation pipeline: Voronoi tessellation → Geography
       (land/ocean/coastal/mountain) → Nation placement (organic growth)
       → Province initialization → Territorial waters → Genesis (50-year
       deterministic ancient history populating trust matrix).
       SpatialManager wraps NetworkX for relationship-aware pathfinding.

    5. ANALYSIS (geomas.analysis):
       Behavioral analysis toolkit: DeceptionAnalyzer (dual matrix for
       defense + foreign domains with governance-specific moral washing
       patterns), CoherenceAnalyzer (strategy alignment scoring),
       DeltaAnalyzer (counterfactual divergence with LLM explanation),
       BehaviorTracker (turn-by-turn deception/coherence history),
       SimulationHealthAnalyzer, and TokenLogger for cost observability.

    6. DATA (geomas.schemas, geomas.db):
       All inter-component communication uses Pydantic models.
       WorldState is the Single Source of Truth. Dual-DB strategy:
       DuckDB (SimulationDB) for snapshots/envelopes/behaviors,
       MetricsDB for time-series analytics. TurnCache for fast in-memory
       access. Full serialization/deserialization for state save/load.

    7. EXPLAINABILITY (geomas.xai):
       CountryEnvelope persists full prompt traces (system, input, raw JSON)
       for all 5 agent types per nation per turn. XAI injections allow
       forcing or blocking specific actions for counterfactual experiments.

Design Principles:
    - DETERMINISM: Given identical seeds (map_seed + history_seed), the
      structural simulation produces identical results. All RNG is local.
    - PYDANTIC EVERYWHERE: No raw dicts cross package boundaries.
    - BOUNDED RATIONALITY: Agents see limited context (configurable token
      budget, capped events/actions window) via ContextManager pruning.
    - SEPARATION: Calculators are pure functions; Actions are validated
      then executed; Agents only produce intent (CountryEnvelope).

Packages:
    - actions: Action validation and execution engine (defense waterfall,
               economy handler, foreign diplomacy, opinion triggers)
    - agents: LLM-powered nation agents (NationAgent, Ministers, OpinionAgent,
              LLMClient with multi-provider support)
    - analysis: Deception scoring, coherence analysis, behavior tracking,
                counterfactual comparison, simulation health, token logging
    - calculators: Pure stateless functions for consumption, production,
                   power projection, crisis resolution, and metrics extraction
    - core: Reserved (GenesisEngine moved to world.genesis)
    - db: DuckDB persistence (SimulationDB, GenesisDB, MetricsDB, TurnCache,
          serialization utilities)
    - schemas: Core Pydantic models (WorldState, NationState, ProvinceState,
               TerrainType, RelationshipState, WarStats)
    - simulation: Main simulation loop (SimulationEngine), turn phases
                  (upkeep, opinion), and mid-simulation scenarios
                  (pandemic, resource discovery, separatist insurrection)
    - world: Procedural map generation (Voronoi pipeline), spatial analysis
             (SpatialManager with NetworkX), and genesis historical simulation
    - xai: Explainability tools (under development, current features
            embedded in CountryEnvelope trace fields)

Usage:
    from geomas.simulation import SimulationEngine
    from geomas.world import generate_world

    sim = SimulationEngine(map_seed=42, history_seed=99)
    sim.run(steps=10)
"""

__version__ = "0.3.5"
__author__ = "GeoMAS Research Team"
