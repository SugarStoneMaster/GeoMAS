"""
World Map Generator - Main orchestration module.

Coordinates the entire world generation pipeline using the
specialized modules for voronoi, geography, nations, and provinces.
"""

import numpy as np
import random
from typing import Optional

from geomas.schemas.world import WorldState
from geomas.world.genesis import GenesisEngine
from geomas import calculators as economy

from geomas.world.generation.voronoi import generate_voronoi, build_adjacency
from geomas.world.generation.geography import generate_geography
from geomas.world.generation.nations import (
    assign_nations,
    assign_provinces_to_nations,
    assign_territorial_waters,
    distribute_nukes
)
from geomas.world.generation.provinces import create_provinces


def generate_world(
    seed: int = 42,
    history_seed: int = 99,
    n_cells: int = 1500,
    n_nations: int = 10,
    relaxation_steps: int = 3
) -> WorldState:
    """
    Generates a deterministic WorldState using Voronoi diagrams and Organic Growth.
    
    Args:
        seed: Random seed for map generation
        history_seed: Random seed for historical simulation
        n_cells: Number of Voronoi cells
        n_nations: Number of nations to create
        relaxation_steps: Lloyd's relaxation iterations
        
    Returns:
        Complete WorldState ready for simulation
    """
    generator = MapGenerator(seed, n_cells, n_nations, relaxation_steps)
    return generator.generate(history_seed)


class MapGenerator:
    """
    Orchestrates the procedural generation pipeline for the GeoMAS world.
    
    Each step is delegated to specialized modules for maintainability.
    """
    
    def __init__(self, seed: int, n_cells: int, n_nations: int, relaxation_steps: int):
        self.seed = seed
        self.n_cells = n_cells
        self.n_nations = n_nations
        self.relaxation_steps = relaxation_steps
        
        # Initialize RNG
        self.rng = np.random.RandomState(seed)
        random.seed(seed)
    
    def generate(self, history_seed: int) -> WorldState:
        """Main generation pipeline."""
        # Step 1: Generate Voronoi geometry
        vor = generate_voronoi(self.rng, self.n_cells, self.relaxation_steps)
        adjacency = build_adjacency(vor)
        
        # Step 2: Generate geography (land/ocean)
        land_indices, ocean_indices, cell_centroids, cell_vertices = generate_geography(
            vor, self.rng
        )
        
        # Step 3: Create and assign nations
        nations_dict, seed_ids = assign_nations(land_indices, self.rng, self.n_nations)
        political_map = assign_provinces_to_nations(land_indices, cell_centroids, nations_dict, seed_ids)
        
        # Step 4: Create provinces
        provinces_dict = create_provinces(
            land_indices, ocean_indices, political_map, adjacency,
            cell_centroids, cell_vertices, self.rng
        )
        
        # Step 5: Finalize
        assign_territorial_waters(ocean_indices, provinces_dict, nations_dict)
        distribute_nukes(nations_dict, self.rng)
        
        # Step 6: Calculate aggregates
        self._calculate_nation_aggregates(nations_dict, provinces_dict)
        
        # Assemble World
        world = WorldState(
            turn=0,
            provinces=provinces_dict,
            nations=nations_dict,
            trust_matrix={}
        )
        
        # Step 7: Run Genesis (historical simulation)
        genesis = GenesisEngine(world, seed=history_seed)
        genesis.initialize_history(years=50)
        
        return world
    
    def _calculate_nation_aggregates(
        self,
        nations_dict: dict,
        provinces_dict: dict
    ) -> None:
        """Calculates aggregate values for each nation from their provinces."""
        temp_world = WorldState(provinces=provinces_dict, nations=nations_dict)
        
        for nation in nations_dict.values():
            aggregates = economy.calculate_nation_aggregates(nation, temp_world)
            
            nation.total_population = aggregates["total_population"]
            nation.total_soldiers = aggregates["total_soldiers"]
            nation.total_aircraft = aggregates["total_aircraft"]
            nation.total_navy = aggregates["total_navy"]
            nation.total_food = aggregates["total_food_production"]
            nation.total_energy = aggregates["total_energy_production"]
            nation.total_materials = aggregates["total_materials_production"]
            
            nation.power_projection = economy.calculate_power_projection(nation)
