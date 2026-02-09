"""
Voronoi generation and adjacency building.

Handles the geometric foundation of the world map using scipy Voronoi
with Lloyd's relaxation for more even cell distribution.
"""

import numpy as np
from scipy.spatial import Voronoi
import collections
from typing import Dict, List, Set, Tuple, Optional


def generate_voronoi(rng: np.random.RandomState, n_cells: int, relaxation_steps: int) -> Voronoi:
    """
    Generates Voronoi diagram with Lloyd's relaxation and external boundary padding.
    The padding ensures all interior regions are finite and well-shaped.
    """
    # 1. Generate core points within (0, 1)
    points = rng.rand(n_cells, 2)
    
    # 2. Add external padding points to push infinite regions outside the simulation box
    # We add points at -0.1 and 1.1 on both axes.
    padding = np.array([
        [-0.2, -0.2], [-0.2, 0.5], [-0.2, 1.2],
        [0.5, -0.2], [0.5, 1.2],
        [1.2, -0.2], [1.2, 0.5], [1.2, 1.2]
    ])
    points = np.vstack([points, padding])
    
    # 3. Lloyd's Relaxation
    for _ in range(relaxation_steps):
        vor = Voronoi(points)
        new_points = []
        for i, region_index in enumerate(vor.point_region):
            region = vor.regions[region_index]
            if -1 in region or len(region) == 0:
                # Keep padding fixed
                new_points.append(points[i])
            else:
                polygon = [vor.vertices[i] for i in region]
                centroid = np.mean(polygon, axis=0)
                new_points.append(centroid)
        points = np.array(new_points)
    
    # 4. Filter only points that are STRICTLY inside the simulation box (0, 1)
    # This removes the "ghost" padding provinces.
    mask = (points[:, 0] >= 0) & (points[:, 0] <= 1) & (points[:, 1] >= 0) & (points[:, 1] <= 1)
    survivors = points[mask]
    
    # 5. Binned Scanline Sort for survivors only
    rows = np.round(survivors[:, 1] / 0.05)
    ind = np.lexsort((survivors[:, 0], -rows))
    survivors = survivors[ind]
        
    return Voronoi(survivors)


def build_adjacency(vor: Voronoi) -> Dict[int, Set[int]]:
    """
    Builds graph connectivity using POINT indices.
    Point index 'i' maps directly to Province ID 'i'.
    """
    adjacency = collections.defaultdict(set)
    
    # ridge_points are indices into vor.points
    for p1, p2 in vor.ridge_points:
        adjacency[p1].add(p2)
        adjacency[p2].add(p1)
    
    return adjacency
