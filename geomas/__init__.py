"""
GeoMAS - Geopolitical Multi-Agent Simulation.

A deterministic, agent-based simulation framework for studying geopolitical
dynamics through AI-driven nation agents. Designed for academic research
on deception, alliance formation, and strategic decision-making.

Packages:
    - actions: Action validation and execution engine
    - agents: LLM-powered nation agents and ministers
    - analysis: Deception scoring and behavioral analysis
    - calculators: Pure economic/physical calculations
    - core: Genesis (historical simulation)
    - schemas: Core data models (WorldState, NationState)
    - simulation: Main simulation loop and phases
    - world: Map generation and spatial intelligence
    - xai: Explainability tools

Usage:
    from geomas.simulation import SimulationEngine
    from geomas.world import generate_world
    
    sim = SimulationEngine(map_seed=42, history_seed=99)
    sim.run(steps=10)
"""

__version__ = "0.3.5"
__author__ = "GeoMAS Research Team"
