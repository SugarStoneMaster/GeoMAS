# 👑 GeoMAS - High-Level Overview

**GeoMAS (Geopolitical Multi-Agent System)** is a scientific simulation framework designed for researchers to study geopolitical dynamics, strategic decision-making, and explainable AI (XAI) in competitive multi-agent environments. 

The system models a world of competing nations, where each nation is governed by a decentralized "Cabinet" of LLM-powered agents balancing strategic goals, economic constraints, and international relations.

---

## 🎯 Researcher Capabilities

### 1. Repeatable Simulation Architecture
GeoMAS is designed for **scientific analysis**. It utilizes a seed-based architecture to provide a consistent framework for every run.
- **Structural Determinism**: Map generation, resource placement, and simulation rules (e.g., combat math, economic growth) are fully deterministic based on the provided seeds.
- **LLM Intent & Variability**: While the simulation framework is deterministic, LLM-powered agents (Cabinet) exhibit natural cognitive variability even at low temperatures. This allows researchers to study how different linguistic reasonings emerge within a fixed structural environment.

### 2. Cognitive Cabinet Dynamics
Researchers can observe and analyze the decision-making process of a nation's government:
- **Distributed Intelligence**: A nation's actions are the result of three specialized ministerial proposals (Defense, Economy, Foreign).
- **Executive Veto**: The **President** agent acts as the final decision-maker, prioritizing or modifying proposals based on the global strategy.
- **Social Constraints**: A rule-based **Public Satisfaction** system monitors the impact of actions on the citizenry. Low satisfaction triggers discrete events مانند general strikes or civil unrest that physically limit the nation's productivity.

### 3. Diplomatic & Strategic Analysis
- **Dynamic Trust Matrix**: Every action (messages, trade, war) modifies a mathematical trust score between nations, visible to the researcher.
- **Strategic Deception Monitoring**: The system tracks "Private Intent" vs. "Public Action," allowing for the analysis of deception and coherence in MAS.
- **Automatic Treaty Triggers**: Defense pacts and treaties are encoded as deterministic rules that penalize or force entry into conflicts, modeling "locked-in" diplomatic constraints.

### 4. XAI & Counterfactual Research
GeoMAS is a powerful tool for Explainable AI:
- **Full Traceability**: Researchers have access to every prompt, raw LLM response, and the internal reasoning that led to a specific action.
- **State-Based Forking**: You can **load a past simulation state** from the database and diverge from that point. This enables "What-If" analysis (e.g., "What if Nation A accepted the treaty on Turn 10 instead of rejecting it?"), allowing you to compare parallel histories branching from a single event.

---

## 🏗️ The Pillars of GeoMAS

| Pillar | Research Utility |
| :--- | :--- |
| **Simulation Engine** | Orchestrates turn phases, ensuring rules are applied consistently. |
| **Action Engine** | The "Rules Oracle" that validates agent intent against physical constraints. |
| **Context Manager** | Filters and manages agent memory, defining what information is "known" at any time. |
| **DuckDB Telemetry** | High-performance storage of every metric, prompt, and state for post-run analysis. |

---

## 🚀 Key Use Cases
- **Geopolitical Stress-Testing**: Studying how resource scarcity affects the likelihood of conflict.
- **Deception Analysis**: Measuring the propagation of false signals across an agent network.
- **Counterfactual History**: Analyzing how single decisions impact long-term global stability.
