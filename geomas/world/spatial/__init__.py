"""
Spatial Analysis Package.

Tools for spatial reasoning.

Classes:
    - SpatialManager: Graph-based operations (adjacency, pathfinding, 
      reachability analysis for military movement validation)

Note: SpatialTranslator has been moved to geomas.agents.context.spatial
"""

from geomas.world.spatial.manager import SpatialManager

__all__ = ["SpatialManager"]
