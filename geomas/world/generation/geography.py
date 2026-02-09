"""
Geography generation for the world map.

Handles land/ocean classification using a tectonic plates approach
with continent centers and radii.
"""

import numpy as np
from scipy.spatial import Voronoi
from typing import List, Dict, Tuple
from shapely.geometry import Polygon as ShapelyPolygon, box

def generate_geography(
    vor: Voronoi,
    rng: np.random.RandomState
) -> Tuple[List[int], List[int], Dict[int, np.ndarray], Dict[int, List[Tuple[float, float]]]]:
    """
    Defines Land vs Ocean using Tectonic Plates logic.
    """
    n_continents = rng.randint(4, 7)
    continent_centers = _generate_continent_centers(rng, n_continents)
    continent_radii = [rng.uniform(0.12, 0.20) for _ in range(len(continent_centers))]
    
    land_indices = []
    ocean_indices = []
    cell_centroids = {}
    cell_vertices = {}
    
    # Bounding box for clipping (0, 0) to (1, 1)
    boundary = box(0, 0, 1, 1)
    
    for i, region_index in enumerate(vor.point_region):
        region = vor.regions[region_index]
        centroid = vor.points[i]
        cell_centroids[i] = centroid
        
        # 1. Extract raw vertices (if any)
        if -1 not in region and len(region) > 0:
            polygon_verts = np.array([vor.vertices[v] for v in region])
            poly = ShapelyPolygon(polygon_verts)
        else:
            # For infinite or incomplete regions, we can't make a poly easily.
            # But wait, Scipy sometimes has finite regions that are outside?
            # We'll try to find any finite verts or just center it.
            # Actually, a safer way to clip infinite regions is complex.
            # For now, we'll try to use a "large" bounding box for infinite regions then clip.
            poly = None

        # 2. Clip to unit square
        if poly and poly.is_valid:
            clipped = poly.intersection(boundary)
            if not clipped.is_empty and hasattr(clipped, 'exterior'):
                cell_vertices[i] = list(clipped.exterior.coords)
            else:
                cell_vertices[i] = []
        else:
            # Fallback for infinite regions: we don't draw the fill, just label.
            cell_vertices[i] = []
        
        # 3. Land Check
        if _is_land(centroid, continent_centers, continent_radii, rng):
            land_indices.append(i)
        else:
            ocean_indices.append(i)
    
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
