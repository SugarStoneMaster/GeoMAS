"""
Nation assignment and territory management.

Handles assigning land cells to nations, capital placement,
territorial waters, and nuclear distribution.
"""

import numpy as np
from typing import Dict, List, Tuple
from shapely.geometry import Polygon as ShapelyPolygon

from geomas.schemas.world import NationState, ProvinceState, TerrainType
from geomas.world.presets import PRESET_NATIONS  # Top-level world package


# --- CONFIGURATION ---
BUDGET_MIN = 500.0
BUDGET_MAX = 3000.0
NUKE_NATIONS_MIN = 2
NUKE_NATIONS_MAX = 3
NUKES_PER_NATION_MIN = 1
NUKES_PER_NATION_MAX = 5


def assign_nations(
    land_indices: List[int],
    rng: np.random.RandomState,
    n_nations: int
) -> Tuple[Dict[str, NationState], List[int]]:
    """
    Creates nations and picks initial seed provinces for territory expansion.
    
    Args:
        land_indices: List of land cell indices
        rng: Random state for determinism
        n_nations: Number of nations to create
        
    Returns:
        tuple (nations_dict, seed_province_ids)
    """
    import random
    
    n_nations = min(n_nations, len(PRESET_NATIONS), len(land_indices))
    sorted_land = sorted(land_indices)
    seed_provinces = random.sample(sorted_land, n_nations)
    
    nations_dict = {}
    
    for i in range(n_nations):
        preset = PRESET_NATIONS[i]
        nation_id = preset["id"]
        initial_budget = rng.uniform(BUDGET_MIN, BUDGET_MAX)
        
        # Generate cultural traits based on seed
        from geomas.actions.opinion.traits import generate_cultural_traits
        traits = generate_cultural_traits(nation_id, rng.randint(0, 1000000))
        
        nations_dict[nation_id] = NationState(
            id=nation_id,
            name=preset["name"],
            color=preset["color"],
            province_ids=[],
            total_budget=initial_budget,
            cultural_traits=traits
        )
    
    return nations_dict, seed_provinces


def assign_provinces_to_nations(
    land_indices: List[int],
    cell_centroids: Dict[int, np.ndarray],
    nations_dict: Dict[str, NationState],
    seed_province_ids: List[int]
) -> Dict[int, str]:
    """
    Assigns each land cell to the nearest nation's seed province.
    
    Returns:
        Political map (region_idx -> nation_id)
    """
    political_map = {}
    
    # Map nation_id to its seed centroid
    nation_ids = list(nations_dict.keys())
    seed_locations = {
        nation_ids[i]: cell_centroids[seed_province_ids[i]] 
        for i in range(len(nation_ids))
    }
    
    for region_idx in land_indices:
        my_loc = cell_centroids[region_idx]
        closest_nation_id = None
        min_dist = float('inf')
        
        for nation_id, start_loc in seed_locations.items():
            dist = np.linalg.norm(my_loc - start_loc)
            if dist < min_dist:
                min_dist = dist
                closest_nation_id = nation_id
        
        political_map[region_idx] = closest_nation_id
        nations_dict[closest_nation_id].province_ids.append(int(region_idx))
    
    return political_map




def assign_territorial_waters(
    ocean_indices: List[int],
    provinces_dict: Dict[int, ProvinceState],
    nations_dict: Dict[str, NationState]
) -> None:
    """Assigns ocean provinces adjacent to single nation's coast as territorial waters."""
    for r_idx in ocean_indices:
        ocean_prov = provinces_dict.get(r_idx)
        if not ocean_prov:
            continue
        
        adjacent_nations = set()
        for neighbor_idx in ocean_prov.neighbors:
            neighbor = provinces_dict.get(neighbor_idx)
            if neighbor and neighbor.terrain == TerrainType.COASTAL and neighbor.owner_id:
                adjacent_nations.add(neighbor.owner_id)
        
        if len(adjacent_nations) == 1:
            owner_id = list(adjacent_nations)[0]
            ocean_prov.owner_id = owner_id
            nations_dict[owner_id].territorial_water_ids.append(int(r_idx))


def distribute_nukes(
    nations_dict: Dict[str, NationState],
    rng: np.random.RandomState
) -> None:
    """Distributes nuclear weapons to 2-3 random nations."""
    nation_ids = list(nations_dict.keys())
    
    if len(nation_ids) < NUKE_NATIONS_MIN:
        return
    
    max_nuclear = min(NUKE_NATIONS_MAX, len(nation_ids))
    min_nuclear = min(NUKE_NATIONS_MIN, max_nuclear)
    
    if min_nuclear >= max_nuclear:
        n_nuclear_nations = min_nuclear
    else:
        n_nuclear_nations = rng.randint(min_nuclear, max_nuclear + 1)
    
    nuclear_nations = rng.choice(nation_ids, size=n_nuclear_nations, replace=False)
    
    for nation_id in nuclear_nations:
        nuke_count = rng.randint(NUKES_PER_NATION_MIN, NUKES_PER_NATION_MAX + 1)
        nations_dict[nation_id].nukes = int(nuke_count)
