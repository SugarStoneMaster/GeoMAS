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
        
        # Initialize RNGs
        self.rng = np.random.RandomState(seed)
        # Fix: Create a local random instance to preserve current behavior 
        # without touching the global random state.
        self.random_inst = random.Random(seed)
    
    def generate(self, history_seed: int) -> WorldState:
        """Main generation pipeline."""
        # Step 1: Generate Voronoi geometry
        vor, n_survivors = generate_voronoi(self.rng, self.n_cells, self.relaxation_steps)
        adjacency = build_adjacency(vor, n_survivors)
        
        # Step 2: Generate geography (land/ocean)
        land_indices, ocean_indices, cell_centroids, cell_vertices = generate_geography(
            vor, n_survivors, self.rng
        )
        
        # Step 3: Create and assign nations
        # Pass the local random_inst to preserve map layout for each seed
        nations_dict, seed_ids = assign_nations(land_indices, self.rng, self.n_nations, random_inst=self.random_inst)
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
            turn=1,
            provinces=provinces_dict,
            nations=nations_dict,
            trust_matrix={}
        )
        
        # Step 7: Run Genesis (historical simulation)
        genesis = GenesisEngine(world, seed=history_seed)
        genesis.initialize_history(years=50)
        
        # Step 8: Recalculate aggregates after history to ensure accurate power projection
        self._calculate_nation_aggregates(nations_dict, provinces_dict)
        
        return world
    
    def _calculate_nation_aggregates(
        self,
        nations_dict: dict,
        provinces_dict: dict
    ) -> None:
        """
        Calculates aggregate values and initializes stockpiles for each nation.
        
        Stockpile logic:
        - Each nation gets 10 turns of consumption as initial reserves.
        - A 'Prosperity Factor' (0.7 - 1.3) adds variance between nations.
        """
        temp_world = WorldState(provinces=provinces_dict, nations=nations_dict)
        
        # Constants for stockpile calculation
        AUTONOMY_TURNS = 5  # Reduced from 10 to create trade pressure
        FOOD_PER_PERSON = 1.0
        ENERGY_PER_PERSON = 0.5
        
        for i, nation in enumerate(nations_dict.values()):
            # Seed-based prosperity factor (0.7 to 1.3)
            prosperity = 0.7 + (self.rng.random() * 0.6)
            
            aggregates = economy.calculate_nation_aggregates(nation, temp_world)
            
            # Set production totals from provinces
            nation.total_population = aggregates["total_population"]
            nation.total_soldiers = aggregates["total_soldiers"]
            nation.total_aircraft = aggregates["total_aircraft"]
            nation.total_navy = aggregates["total_navy"]
            
            # Calculate consumption-based stockpiles (5 turns of autonomy)
            pop = nation.total_population
            food_consumption = pop * FOOD_PER_PERSON
            energy_consumption = pop * ENERGY_PER_PERSON
            materials_consumption = economy.calculate_materials_consumption(
                nation.total_soldiers, nation.total_aircraft, nation.total_navy
            )
            
            # Calculate base income (Tax Revenue) for budget baseline
            base_tax_revenue = sum(
                provinces_dict[p_id].tax_revenue 
                for p_id in nation.province_ids
            )
            
            # Apply prosperity factor and autonomy buffer
            nation.total_food = food_consumption * AUTONOMY_TURNS * prosperity
            nation.total_energy = energy_consumption * AUTONOMY_TURNS * prosperity
            nation.total_materials = max(100, materials_consumption * AUTONOMY_TURNS * prosperity)
            
            # --- FIX: Start with Autonomy Rounds of Budget (Consistent with Taxes) ---
            # Old: (1000 + pop * 0.01) -> trivial amount compared to turn income
            # New: Tax Revenue * Autonomy * Prosperity -> Consistent initial state
            nation.total_budget = max(5000, base_tax_revenue * AUTONOMY_TURNS * prosperity)
            
            nation.power_projection = economy.calculate_power_projection(nation)

