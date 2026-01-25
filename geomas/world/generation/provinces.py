"""
Province creation and population management.

Handles creating ProvinceState objects with terrain, population,
military units, and production values.
"""

import numpy as np
from typing import Dict, List, Set, Tuple

from geomas.schemas.world import ProvinceState, TerrainType


# --- CONFIGURATION ---
POP_MIN = 500
POP_MAX = 5000
INITIAL_MILITARY_RATIO_MIN = 0.02  # 2%
INITIAL_MILITARY_RATIO_MAX = 0.08  # 8%
TAX_RATE = 0.1  # 10% base tax rate


def create_provinces(
    land_indices: List[int],
    ocean_indices: List[int],
    political_map: Dict[int, str],
    adjacency: Dict[int, Set[int]],
    cell_centroids: Dict[int, np.ndarray],
    cell_vertices: Dict[int, List[Tuple[float, float]]],
    rng: np.random.RandomState
) -> Dict[int, ProvinceState]:
    """
    Creates ProvinceState objects for all cells.
    
    Args:
        land_indices: List of land cell indices
        ocean_indices: List of ocean cell indices
        political_map: Mapping of region_idx to nation_id
        adjacency: Adjacency graph
        cell_centroids: Mapping of cell index to centroid
        cell_vertices: Mapping of cell index to vertices
        rng: Random state for determinism
        
    Returns:
        Dictionary of province_id -> ProvinceState
    """
    provinces_dict = {}
    
    # Land Provinces
    for r_idx in land_indices:
        nation_id = political_map[r_idx]
        neighbors = list(adjacency[r_idx])
        
        # Determine terrain
        is_coastal = any(n_idx in ocean_indices for n_idx in neighbors)
        terrain = _determine_terrain(is_coastal, rng)
        
        # Population and military
        population = _generate_population(terrain, rng)
        military_ratio = rng.uniform(INITIAL_MILITARY_RATIO_MIN, INITIAL_MILITARY_RATIO_MAX)
        soldiers = int(population * military_ratio)
        workers = population - soldiers
        
        # Production
        food_prod, energy_prod, materials_prod = calculate_production(terrain, workers, rng)
        tax_revenue = population * TAX_RATE
        
        provinces_dict[r_idx] = ProvinceState(
            id=r_idx,
            owner_id=nation_id,
            terrain=terrain,
            coordinates=(float(cell_centroids[r_idx][0]), float(cell_centroids[r_idx][1])),
            vertices=cell_vertices[r_idx],
            neighbors=neighbors,
            population=population,
            workers=workers,
            soldiers=soldiers,
            aircraft=0,
            navy=0,
            food_production=food_prod,
            energy_production=energy_prod,
            materials_production=materials_prod,
            tax_revenue=tax_revenue
        )
    
    # Ocean Provinces
    for r_idx in ocean_indices:
        if r_idx not in cell_centroids:
            continue
        
        provinces_dict[r_idx] = ProvinceState(
            id=r_idx,
            owner_id=None,
            terrain=TerrainType.OCEAN,
            coordinates=(float(cell_centroids[r_idx][0]), float(cell_centroids[r_idx][1])),
            vertices=cell_vertices.get(r_idx, []),
            neighbors=list(adjacency[r_idx]),
            food_production=rng.uniform(10, 30)  # Fishing
        )
    
    return provinces_dict


def _determine_terrain(is_coastal: bool, rng: np.random.RandomState) -> TerrainType:
    """Determines terrain type for a land cell."""
    if is_coastal:
        return TerrainType.COASTAL
    elif rng.rand() < 0.2:
        return TerrainType.MOUNTAIN
    else:
        return TerrainType.LAND


def _generate_population(terrain: TerrainType, rng: np.random.RandomState) -> int:
    """Generates population based on terrain type."""
    if terrain == TerrainType.MOUNTAIN:
        return int(rng.uniform(POP_MIN * 0.3, POP_MAX * 0.5))
    elif terrain == TerrainType.COASTAL:
        return int(rng.uniform(POP_MIN * 1.2, POP_MAX * 1.5))
    else:
        return int(rng.uniform(POP_MIN, POP_MAX))


def calculate_production(
    terrain: TerrainType,
    workers: int,
    rng: np.random.RandomState
) -> Tuple[float, float, float]:
    """
    Calculate production values based on terrain and workforce.
    
    Returns:
        Tuple of (food_production, energy_production, materials_production)
    """
    # Base yields per worker
    if terrain == TerrainType.COASTAL:
        food_yield, energy_yield, materials_yield = 0.08, 0.03, 0.02
    elif terrain == TerrainType.MOUNTAIN:
        food_yield, energy_yield, materials_yield = 0.02, 0.01, 0.10
    else:  # LAND
        food_yield, energy_yield, materials_yield = 0.06, 0.05, 0.04
    
    # Add random variation
    food_prod = workers * food_yield * rng.uniform(0.8, 1.2)
    energy_prod = workers * energy_yield * rng.uniform(0.8, 1.2)
    materials_prod = workers * materials_yield * rng.uniform(0.8, 1.2)
    
    return food_prod, energy_prod, materials_prod
