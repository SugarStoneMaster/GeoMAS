# GeoMAS - Geopolitical Multi-Agent Simulation

A deterministic, agent-based simulation framework for studying geopolitical dynamics through AI-driven nation agents.

## Overview

GeoMAS simulates a world where AI agents control nations, making strategic decisions about military actions, economic policies, and diplomacy. Each agent can publicly declare peaceful intentions while secretly planning aggression - enabling research on **deception, trust, and strategic behavior**.

### Key Features

- **Procedural World Generation**: Voronoi-based map with oceans, mountains, and coastal regions
- **LLM-Powered Agents**: Each nation has a "President" and three "Ministers" (Defense, Economy, Foreign Affairs)
- **Dual-Layer Communication**: Public statements vs. private intentions (for deception analysis)
- **Deterministic Simulation**: Same seeds = same results (reproducibility for research)
- **Trade System**: Oracle-based trade evaluation using economic formulas
- **Explainability**: Every decision includes reasoning for XAI research

## Architecture

```
geomas/
├── actions/        # Action validation and execution
├── agents/         # LLM-powered nation agents
├── analysis/       # Deception scoring and metrics
├── calculators/    # Pure economic/physical calculations
├── core/           # Genesis (historical simulation)
├── schemas/        # Core Pydantic models
├── simulation/     # Main simulation loop
├── world/          # Map generation and spatial analysis
└── xai/            # Explainability tools
```

## Quick Start

```python
from geomas.simulation import SimulationEngine

# Create simulation with reproducible seeds
sim = SimulationEngine(
    map_seed=42,      # Map generation seed
    history_seed=99,  # Historical events seed
    n_cells=1500      # Number of provinces
)

# Run 10 turns
sim.run(steps=10)

# Access results
print(f"Turn: {sim.world.turn}")
print(f"Nations: {list(sim.world.nations.keys())}")
```

## Installation

```bash
git clone https://github.com/your-repo/GeoMAS.git
cd GeoMAS
pip install -r requirements.txt
```

## Running Tests

```bash
pytest tests/ -q
```

## Current Status: Phase 3.5 Complete

### Completed
- ✅ World generation with Voronoi tessellation
- ✅ Multi-agent architecture with ministerial hierarchy
- ✅ Resource system (food, energy, materials)
- ✅ Trade oracle with economic formulas
- ✅ Deception analysis tools
- ✅ Full test coverage (66 tests)

### Next Phase: Advanced Military System
- Combat resolution mechanics
- Unit movement and logistics
- War/peace state machine

## Research Applications

- **Deception Detection**: Compare public statements vs. private intentions
- **Alliance Formation**: Study how trust evolves through interactions
- **Strategic Decision-Making**: Analyze how LLMs reason about geopolitical situations

## License

Academic use only. See LICENSE for details.

---

*GeoMAS is developed for a Master's Thesis on Multi-Agent Systems and Geopolitical Simulation.*
