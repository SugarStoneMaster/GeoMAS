# 🏗 GeoMAS Technical Architecture

GeoMAS is a multi-layered simulation environment built for determinism in mechanics and cognitive depth in agents.

## 1. Orchestration Layer (Timing & Synchronization)
The orchestration layer ensures the simulation survives turn-by-turn with structural consistency.

- **`SimulationEngine`**: The core loop orchestrator. It executes the simulation phases and handles the **deterministic seeding** of all non-LLM components. 
- **DB-State Synchronization**: The engine manages the persistence of `WorldState` snapshots and `CountryEnvelope` (agent logs) into DuckDB.
- **State Loading & Forking**: Forking is implemented as a **load-and-diverge** mechanism. The engine can load any turn *T* from a simulation *S1* and initialize a new simulation *S2* from that exact state, enabling controlled experimental branching.

## 2. Cognitive Layer (LLM Cabinet)
The cognitive layer is where strategic reasoning takes place. It is designed to be asynchronous and context-aware.

- **Agent Hierarchy**: 
    - **Ministers**: Specialized domain prompts (`Defense`, `Economy`, `Foreign`) that propose actions based on local and global context.
    - **President**: A higher-order LLM agent that performs synthesis, resolving conflicts between ministerial proposals.
- **`ContextManager`**: A centralized state-to-prompt bridge. It filters thousands of world events into a relevant, token-efficient memory buffer for each agent.
- **Non-Deterministic Cognitive Edge**: While the system uses seeds and low temperature, the Cabinet agents are treated as stochastic decision-makers within a deterministic physical world.

## 3. Physical Layer (World Grammar)
The physical layer represents the rigid, rule-based environment that agents must navigate.

- **`WorldState`**: A comprehensive Pydantic model representing the exact state of provinces (population, infrastructure, units) and global relations (treaty status, trust values).
- **Metric Calculators**: Pure Python solvers for production, consumption, and "Satisfaction" logic.
- **Public Satisfaction Logic**: Unlike the Cabinet, **Public Opinion is currently a rule-based deterministic system**. It calculates a "Satisfaction Delta" based on government actions (taxes, welfare, war) and cultural traits, triggering physical penalties (unrest) without LLM intervention.

## 4. Action Layer (The Rules Oracle)
The action layer acts as the system's "Physics Engine," ensuring that agent intent is constrained by reality.

- **`ActionEngine`**: The central validator. It intercepts agent "Envelopes" and rejects or modifies actions that violate constraints (e.g., negative budget, impossible unit movement).
- **Execution Handlers**:
    - **Defense Waterfall**: A sequential resolver for military movements and combat, ensuring zero-sum results in territorial changes.
    - **Trade & Treaties**: Deterministic evaluators for diplomatic offers based on mathematical trust thresholds and resource scarcity.
- **Explainability (XAI) Hooks**: The action layer decorates execution with metadata, allowing the `DeceptionAnalyzer` to compare agent internal reasoning with the actual physical outcome for post-run analysis.