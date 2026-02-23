# 🏗 GeoMAS exhaustive Technical Architecture

GeoMAS is a multi-layered simulation environment built for structural determinism and cognitiveDepth. This document provides a granular breakdown of the system layers and their mathematical/logical foundations.

---

## 1. Orchestration Layer (The Engine)
The **Orchestration Layer** ensures the simulation's integrity through a strictly sequenced turn loop and atomic state management.

- **`SimulationEngine`**: The central controller. Every turn operates in five distinct phases:
    1. **Scenario Phase**: Injects global stochastic events (Pandmics, Famines) using `scenarios.py`.
    2. **Upkeep Phase**: A deterministic resolution of the national ledger.
        - **Population Growth**: Calculated from (`food_surplus` vs. `starvation_rate`).
        - **Spoilage**: Excess resources (Food, materials) decay by a fixed ratio (10-20% per turn).
        - **Taxation**: Direct sum of `province.tax_revenue`.
    3. **Cognitive Phase**: Triggered via `engine.step()`, this runs the agents asynchronously.
    4. **Opinion/Satisfaction Phase**: Resolves the consequences of government actions using rule-based logic (discussed in Physical Layer).
    5. **Persistence Phase**: Performed via the **DuckDB Client** for high-write-speed storage of snaps and traces.

- **State Loading (Forking)**: Structural forking is achieved by initializing a new simulation ID while loading the `provinces`, `nations`, and `context_manager` objects from an existing database snapshot at Turn *T*.

---

## 2. Cognitive Layer (Agent Cognitive Flow)
The **Cognitive Layer** manages the interaction between LLMs and the simulation state.

- **`ContextManager` (Memory Architecture)**: To maintain performance and context relevance, the system uses a **Bounded Rationality** algorithm:
    - **Buffer Limits**: A maximum of **50 global events** and **10 domain-specific actions** (per minister) are kept in active memory.
    - **Relevance Filtering**: Events are tagged with `relevance_to`. If an event (e.g., a border attack) concerns Nation A, it is injected into A's prompt even if it occurred many turns ago.
- **Hierarchical Decision-Making**:
    - **Ministers**: Generate domain-specific proposals with **Private Intent** (Private reasoning for analysis) and **Public Payload**.
    - **The President**: Performs a synthesis. It can **VETO** or **APPROVE** ministerial proposals. A veto results in an `IDLE` action for that domain, preventing unauthorized spending.

---

## 3. Physical Layer (Determinism & Math)
This layer contains the ground truth of the "Universe." Agents cannot ignore or override these rules.

- **Economic Formulas**:
    - **Welfare Investment**: Gain to satisfaction follows a diminishing returns logarithmic curve:  
      $$Gain = 7 \times \log(1 + \frac{Amount}{500})$$
    - **War Tax**: Grants a budget boost of **1% of population**, but imposes a flat **-15 Satisfaction** penalty (scaled to -22 if satisfaction is already < 30).
- **Metric Indices**:
    - **Power Projection Score**:  
      $$Score = (Nukes \times 50) + (Aircraft \times 0.5) + (Navy \times 0.3) + (Soldiers \times 0.1) + (Budget \times 0.001) + \dots$$
    - **Deception Analysis**: The `DeceptionAnalyzer` uses a domain matrix.  
      *Example (Defense)*: `(CONQUEST, DEFENSE) = 0.9` | `(CONQUEST, IDLE) = 0.95`.
- **Public Satisfaction Logic**: Satisfaction transitions are purely deterministic. It tracks multipliers for positive/negative deltas based on **Cultural Traits** (e.g., *Nationalist* = 1.3x military sensitivity).

---

## 4. Action Layer (The Rules Oracle)
The **Action Layer** is the final arbiter. Agent intent is passed through this "Referee" before the world state is updated.

- **`ActionEngine` (Validation Logic)**:
    - **Stock Caps**: Trade proposals are capped at **15% of the sender's current stock** for any single resource.
    - **Thresholds**: International trade requires a **Trust Score ≥ 40** (Neutral relationship).
- **Execution Modules**:
    - **Defense Waterfall**: A priority-based resolver. Nuclear options are processed first, then land/sea attacks, and finally peaceful unit movement and creation.
    - **Naval Landing Logistics**: A multi-stage resolution.  
        1. Naval combat for water control.  
        2. Landing on adjacent coastal provinces.  
        3. **Crew Conversion**: Ships are destroyed to generate infantry (**10 soldiers per ship**) which then resolve land combat against coastal defenders.
- **Topological Constraints**:
    - **Pathfinding**: Soldiers move through owned/allied land; Navy requires international/territorial water cells; Aircraft fly through any cell but require a valid landing zone (own/allies).

---

## 💾 Data & Telemetry
GeoMAS uses a dual-db strategy:
- **DuckDB**: Stores high-resolution world snapshots and agent logs for time-series analysis.
- **Log Traceability**: Every agent execution persists its `last_system_prompt`, `last_input_prompt`, and the `raw_json` response, allowing researchers to "debug" agent logic after the fact.