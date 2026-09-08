"""
World Generation Package.

Procedural world creation using Voronoi tessellation.

Modules:
    - voronoi: Mesh generation and cell adjacency
    - geography: Land/ocean classification and terrain assignment
    - nations: Nation placement and territory growth algorithms
    - provinces: Population, resources, and military initialization
    - generator: High-level orchestration (MapGenerator class)

Pipeline:
    Voronoi cells → Geography → Nations → Provinces → WorldState
"""

from geomas.world.generation.generator import generate_world, MapGenerator

__all__ = ["generate_world", "MapGenerator"]
