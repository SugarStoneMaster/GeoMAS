"""
World Package — Procedural Generation and Spatial Intelligence.

Map generation pipeline, spatial analysis tools, and historical simulation.
Produces a fully initialized WorldState from a pair of seeds (map + history).

Architecture:
    The world generation pipeline runs in 8 sequential stages:
    1. Voronoi Tessellation: N cells (default 1500) with Lloyd's relaxation
       (default 3 iterations) for uniform distribution.
    2. Geography: Land/ocean classification using distance-from-center.
       Terrain: PLAINS, MOUNTAIN, DESERT, FOREST, COASTAL, OCEAN, VOID.
    3. Nation Seeding: Place N capitals on land cells (maximin distance).
    4. Organic Territory Growth: BFS expansion from capitals.
    5. Province Initialization: Population, resources, military by terrain.
    6. Territorial Waters: Ocean provinces adjacent to nation's coastline.
    7. Nation Aggregates: Stockpiles = 5 turns consumption × prosperity (0.7-1.3).
    8. Genesis: 50-year deterministic history populating trust matrix with
       asymmetric relationships via border friction, trade, diplomatic shifts.

Subpackages:
    - generation/: Procedural creation pipeline
        voronoi.py: Scipy Voronoi + Lloyd's relaxation + adjacency graph
        geography.py: Land/ocean classification, terrain assignment
        nations.py: Capital placement, BFS territory growth, territorial waters
        provinces.py: create_provinces() with terrain-dependent initialization
        generator.py: MapGenerator orchestrating all 8 stages

    - spatial/: Graph-based spatial operations
        manager.py (SpatialManager, 176 lines): NetworkX graph wrapper.
          Key methods: get_permitted_path() — relationship-aware pathfinding
          through owned/allied territory with terrain constraints;
          get_border_provinces(), get_neighboring_nations(),
          get_coastal_provinces(), is_contiguous().

Modules:
    - genesis.py (GenesisEngine, 311 lines): Ancient history simulator.
      Per-year: trust decay, border dynamics (friction → trust decrease),
      trade dynamics (complementary resources → trust increase),
      diplomatic shifts (trust thresholds → rivalry/alliance events).
      Config: BORDER_FRICTION=0.3, TRADE_BONUS=0.2, TRUST_DECAY=0.02.
    - territory.py: Territory transfer utilities.
    - presets.py: Preset world configurations.

Note: SpatialTranslator has been moved to geomas.agents.context
"""

from geomas.world.generation import generate_world, MapGenerator
from geomas.world.spatial import SpatialManager
from geomas.world.genesis import GenesisEngine

__all__ = ["generate_world", "MapGenerator", "SpatialManager", "GenesisEngine"]
