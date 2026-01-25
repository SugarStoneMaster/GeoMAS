"""
World Package.

Handles all aspects of the simulated world:
- generation/: Procedural world creation
- spatial/: Spatial analysis and intelligence
"""

from geomas.world.generation import generate_world, MapGenerator
from geomas.world.spatial import SpatialManager, SpatialTranslator

__all__ = ["generate_world", "MapGenerator", "SpatialManager", "SpatialTranslator"]
