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
    Generates Voronoi diagram with Lloyd's relaxation and corner padding.
    """
    # 1. Generate core points
    points = rng.rand(n_cells, 2)
    
    # 2. Add 4 corner points to ensure all regions are finite within the box
    corners = np.array([[0.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 1.0]])
    points = np.vstack([points, corners])
    
    # 3. Lloyd's Relaxation
    for _ in range(relaxation_steps):
        vor = Voronoi(points)
        new_points = []
        for i, region_index in enumerate(vor.point_region):
            region = vor.regions[region_index]
            if -1 in region or len(region) == 0:
                # Keep corners fixed, or move edge points back
                new_points.append(points[i])
            else:
                polygon = [vor.vertices[i] for i in region]
                centroid = np.mean(polygon, axis=0)
                new_points.append(centroid)
        points = np.array(new_points)
    
    # 4. Binned Scanline Sort (Top-to-Bottom, then Left-to-Right)
    # DIVIDE Y into 'rows' (e.g., 20 rows) so that points in same row match in primary key
    # Then sort by X within each row.
    rows = np.round(points[:, 1] / 0.05) # ~20 bins
    ind = np.lexsort((points[:, 0], -rows))
    points = points[ind]
        
    return Voronoi(points)


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
