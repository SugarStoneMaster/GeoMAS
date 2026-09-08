"""
Voronoi generation and adjacency building.

Handles the geometric foundation of the world map using scipy Voronoi
with Lloyd's relaxation for more even cell distribution.
"""

import numpy as np
from scipy.spatial import Voronoi
import collections
from typing import Dict, List, Set, Tuple, Optional, Any


def generate_voronoi(rng: np.random.RandomState, n_cells: int, relaxation_steps: int) -> Tuple[Voronoi, int]:
    """
    Generates Voronoi diagram with Lloyd's relaxation and external boundary padding.
    Returns (Voronoi object, n_survivors) where survivors are points in (0,1) at indices 0..n_survivors-1.
    """
    # 1. Generate core points within (0, 1)
    points = rng.rand(n_cells, 2)
    
    # 2. Add external padding points (ring around the box)
    padding = np.array([
        [-0.3, -0.3], [-0.3, 0.5], [-0.3, 1.3],
        [0.5, -0.3], [0.5, 1.3],
        [1.3, -0.3], [1.3, 0.5], [1.3, 1.3],
        [0.0, -0.3], [1.0, -0.3], [0.0, 1.3], [1.0, 1.3] # More padding for stability
    ])
    points = np.vstack([points, padding])
    
    # 3. Lloyd's Relaxation
    for _ in range(relaxation_steps):
        vor = Voronoi(points)
        new_points = []
        for i, region_index in enumerate(vor.point_region):
            region = vor.regions[region_index]
            if -1 in region or len(region) == 0:
                # Keep padding fixed or move back
                new_points.append(points[i])
            else:
                polygon = [vor.vertices[v] for v in region]
                centroid = np.mean(polygon, axis=0)
                new_points.append(centroid)
        points = np.array(new_points)
    
    # 4. Separate survivors [0, 1] from padding
    # Survivors are everything inside the simulation space.
    mask = (points[:, 0] >= 0) & (points[:, 0] <= 1) & (points[:, 1] >= 0) & (points[:, 1] <= 1)
    survivors = points[mask]
    the_rest = points[~mask]
    
    # 5. Binned Scanline Sort for survivors only
    # Height of row = 0.05
    rows = np.round(survivors[:, 1] / 0.05)
    ind = np.lexsort((survivors[:, 0], -rows))
    sorted_survivors = survivors[ind]
    
    # 6. Recombine: Survivors (0..N-1) then Padding
    final_points = np.vstack([sorted_survivors, the_rest])
    n_survivors = len(sorted_survivors)
        
    return Voronoi(final_points), n_survivors


def build_adjacency(vor: Voronoi, n_survivors: int) -> Dict[int, Set[int]]:
    """
    Builds graph connectivity using POINT indices, restricted to survivors.
    """
    adjacency = collections.defaultdict(set)
    
    for p1, p2 in vor.ridge_points:
        # Only care about adjacencies between survivors 0..n_survivors-1
        if p1 < n_survivors and p2 < n_survivors:
            adjacency[p1].add(p2)
            adjacency[p2].add(p1)
    
    return adjacency
