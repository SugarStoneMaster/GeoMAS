"""
World Package.

Handles all aspects of the simulated world map:

Subpackages:
    - generation/: Procedural world creation (Voronoi, geography, nations)
    - spatial/: Spatial analysis and AI intelligence generation

Main Functions:
    - generate_world(seed, history_seed, n_cells, n_nations): Creates a complete
      WorldState with nations, provinces, and historical relationships.

The world generation pipeline:
    1. Voronoi mesh creation (cells become provinces)
    2. Geography assignment (land, ocean, coastal, mountains)
    3. Nation placement and territory growth
    4. Province initialization (population, resources, military)
    5. Territorial waters calculation
    6. Genesis historical simulation
"""

from geomas.world.generation import generate_world, MapGenerator
from geomas.world.spatial import SpatialManager, SpatialTranslator

__all__ = ["generate_world", "MapGenerator", "SpatialManager", "SpatialTranslator"]
