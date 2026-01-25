"""
Spatial Analysis Package.

Tools for spatial reasoning and intelligence generation.

Classes:
    - SpatialManager: Graph-based operations (adjacency, pathfinding, 
      reachability analysis for military movement validation)
    - SpatialTranslator: Converts map state into natural language
      intelligence briefs for AI agents

The SpatialTranslator enables LLM agents to "see" the map by translating
numerical data into strategic descriptions (borders, threats, resources).
"""

from geomas.world.spatial.manager import SpatialManager
from geomas.world.spatial.translator import SpatialTranslator

__all__ = ["SpatialManager", "SpatialTranslator"]
