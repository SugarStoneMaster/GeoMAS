# 🏗 GeoMAS Technical Architecture

GeoMAS is structured into four distinct layers to ensure modularity, determinism, and testability.

## 1. Orchestration Layer (The Engine)
The **Orchestration Layer** manages the flow of time and the sequence of events within a simulation.

- **`SimulationEngine`**: The main entry point. It manages the simulation loop, turn progression, and database synchronization.
- **Turn Phases**:
    1. **Scenario Phase**: Triggers random or planned global events (e.g., pandemics, rebellions).
    2. **Upkeep Phase**: Calculates economic aggregates, handles resource consumption, and updates population satisfaction.
    3. **Diplomacy Phase**: Clears expired treaties and handles automatic relationship decay.
    4. **Sequential Action Phase**: Each nation acts one by one. Changes made by one nation (e.g., invasion) are immediately visible to the next nation in the same turn.
    5. **Opinion Phase**: The population reacts to government actions, potentially triggering unrest or strikes.
    6. **Persistence Phase**: World state snapshots and agent "Envelopes" (decision logs) are saved to DuckDB.

## 2. Cognitive Layer (The Agents)
The **Cognitive Layer** contains the logic for LLM-powered decision-making.

- **`NationAgent`**: Orchestrates a cabinet of ministers.
- **Ministers (Defense, Economy, Foreign)**: Specialized agents that generate proposals based on domain-specific prompts and world context.
- **`President`**: A "manager" LLM that receives ministerial proposals and a "Public Opinion Briefing" to issue a final `PresidentialDecree`.
- **`OpinionAgent`**: Represents the citizenry. Evaluates government actions and generates a "Satisfaction Delta" that affects economic productivity.
- **`ContextManager`**: Maintains the "Memory" of the simulation, filtering recent events and history into relevant context for agents.

## 3. Physical Layer (The World)
The **Physical Layer** represents the deterministic state of the world.

- **`WorldState`**: A Pydantic-based single source of truth containing all provinces, nations, resources, and relationship matrices.
- **`SpatialManager`**: A utility layer for calculating distances, adjacency (Voronoi), and pathfinding through hostile/neutral territory.
- **`Calculators`**: Pure Python functions that compute production, consumption, power projection, and economic multipliers without external side effects.

## 4. Action Layer (Rules & Execution)
The **Action Layer** is the "Referee" of the system.

- **`ActionEngine`**: Validates ministerial proposals against `WorldState` constraints (e.g., "Do you have enough budget for this unit?").
- **Specialized Handlers**:
    - **Defense Waterfall**: Executes military moves, creations, and combat resolution.
    - **Economy Handler**: Manages welfare investments, war taxes, and trade evaluation.
    - **Foreign Handler**: Manages treaty formation, alliance breaks, and messages.
- **`DeceptionAnalyzer`**: A post-action calculator that compares a nation's "Private Intent" (inside the Cabinet) with its "Public Statement" to calculate a Deception Score.

---

## 💾 Data Strategy
- **DuckDB**: Used for heavy telemetry and historical analysis.
- **SQLite/JSON**: Used for quick snapshotting and structured logging.
- **Single Source of Truth**: Agents NEVER modify the world directly. They propose actions, which are validated and executed by the `ActionEngine`, resulting in a new `WorldState`.