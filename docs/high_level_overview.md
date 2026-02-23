# 👑 GeoMAS - High-Level Overview

**GeoMAS (Geopolitical Multi-Agent System)** is a scientific simulation framework designed for the study of geopolitical dynamics, strategic decision-making, and explainable AI (XAI) in multi-agent environments. 

The system models a world of competing nations, where each nation is governed by a distributed "Cabinet" of LLM-powered agents that must balance internal politics, economic constraints, and international relations.

---

## 🎯 What GeoMAS Can Do

### 1. Deterministic World Simulation
GeoMAS is NOT a game; it is a **repeatable scientific experiment**. Given the same seed, the simulation will produce identical results across different runs. 
- **Spatial Topology**: A Voronoi-based world map with realistic terrain and resource distribution.
- **Resource Management**: Tracking Food, Energy, Materials, and Budget across provinces.
- **Upkeep & Consumption**: Realistic modeling of population growth, consumption, and economic cycles.

### 2. Cognitive Agent Cabinet
Each nation is represented by a set of specialized agents:
- **Defense Minister**: Focuses on military power projection, territorial defense, and unit production.
- **Economic Minister**: Manages resource efficiency, welfare investments, and trade.
- **Foreign Minister**: Handles diplomacy, alliances, messages, and treaties.
- **Public Opinion**: A reactive module that monitors government actions and influences stability (unrest, strikes).
- **President**: The final decision-maker who approves, modifies, or vetoes ministerial proposals.

### 3. Diplomatic & Strategic Complexity
- **Trust Matrix**: A dynamic relational system where every nation tracks its trust in every other nation based on interactions.
- **Strategic Deception**: Agents can lie! A nation might publicly profess peace while privately planning an invasion.
- **Mutual Defense Pacts**: Automated triggers that penalize or force entry into wars based on established treaties.

### 4. Explainable AI (XAI) & Counterfactuals
GeoMAS is built to answer "Why?":
- **Traceability**: Every prompt and decision (Presidential decree, Ministerial proposal) is logged and viewable.
- **Counterfactual Branching (Forking)**: You can "freeze" the simulation at any turn, modify a parameter (e.g., "What if Nation A rejected this treaty?"), and run a parallel branch of the simulation to see the divergence.
- **Telemetry Analysis**: Real-time tracking of Global Trust, Total Deception scores, and Economic Coherence.

---

## 🏗️ The Pillars of GeoMAS

| Component | Responsibility |
| :--- | :--- |
| **Simulation Engine** | The "Time Lord" – orchestrates turns, phases, and persistence. |
| **Action Engine** | The "Rules Oracle" – validates actions against physical and economic constraints. |
| **Context Manager** | The "Memory" – keeps track of world events and helps agents remember the past. |
| **Spatial Manager** | The "Geographer" – manages map topology, distance, and adjacency. |
| **Telemetry & DB** | The "Historian" – persists every turn into DuckDB for later analysis. |

---

## 🚀 Use Cases
- **Geopolitical Research**: Simulating the effect of scarcity on international conflict.
- **MAS Benchmarking**: Testing LLM decision-making in high-stakes, competitive environments.
- **Deception Detection**: Analyzing how "private intent" vs "public action" evolves over time.
