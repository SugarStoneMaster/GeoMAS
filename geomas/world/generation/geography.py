"""
Geography generation for the world map.

Handles land/ocean classification using a tectonic plates approach
with continent centers and radii.
"""

import numpy as np
from scipy.spatial import Voronoi
from typing import Dict, List, Tuple, Set


def generate_geography(
    vor: Voronoi,
    rng: np.random.RandomState
) -> Tuple[List[int], List[int], Dict[int, np.ndarray], Dict[int, List[Tuple[float, float]]]]:
    """
    Defines Land vs Ocean using Tectonic Plates logic.
    
    Args:
        vor: Voronoi diagram
        rng: Random state for determinism
        
    Returns:
        Tuple of (land_indices, ocean_indices, cell_centroids, cell_vertices)
    """
    n_continents = rng.randint(4, 7)
    continent_centers = _generate_continent_centers(rng, n_continents)
    continent_radii = [rng.uniform(0.12, 0.20) for _ in range(len(continent_centers))]
    
    land_indices = []
    ocean_indices = []
    cell_centroids = {}
    cell_vertices = {}
    
    for i, region_index in enumerate(vor.point_region):
        region = vor.regions[region_index]
        
        if -1 in region or len(region) == 0:
            ocean_indices.append(region_index)
            continue
        
        # Extract geometry
        polygon_verts = np.array([vor.vertices[v] for v in region])
        cell_vertices[region_index] = [(float(v[0]), float(v[1])) for v in polygon_verts]
        centroid = np.mean(polygon_verts, axis=0)
        cell_centroids[region_index] = centroid
        
        # Land Check
        if _is_land(centroid, continent_centers, continent_radii, rng):
            land_indices.append(region_index)
        else:
            ocean_indices.append(region_index)
    
    return land_indices, ocean_indices, cell_centroids, cell_vertices


def _generate_continent_centers(rng: np.random.RandomState, n_continents: int) -> np.ndarray:
    """
    Generates continent centers using rejection sampling.
    
    Centers must be inside the map and not too close to each other.
    """
    continent_centers = []
    attempts = 0
    
    while len(continent_centers) < n_continents and attempts < 1000:
        candidate = rng.rand(2)
        
        # Must be inside map margins
        if not (0.1 < candidate[0] < 0.9 and 0.1 < candidate[1] < 0.9):
            attempts += 1
            continue
        
        # Must not be too close to existing centers
        too_close = False
        for c in continent_centers:
            if np.linalg.norm(candidate - c) < 0.35:
                too_close = True
                break
        
        if not too_close:
            continent_centers.append(candidate)
        attempts += 1
    
    return np.array(continent_centers)


def _is_land(
    centroid: np.ndarray,
    continent_centers: np.ndarray,
    continent_radii: List[float],
    rng: np.random.RandomState
) -> bool:
    """Determines if a cell is land based on distance to continent centers."""
    dists = np.linalg.norm(centroid - continent_centers, axis=1)
    closest_idx = np.argmin(dists)
    min_dist = dists[closest_idx]
    noise = (rng.rand() - 0.5) * 0.08
    
    return min_dist + noise < continent_radii[closest_idx]
