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
    Generates Voronoi diagram with Lloyd's relaxation.
    
    Args:
        rng: Random state for determinism
        n_cells: Number of cells to generate
        relaxation_steps: Number of Lloyd's relaxation iterations
        
    Returns:
        Relaxed Voronoi diagram
    """
    points = rng.rand(n_cells, 2)
    
    for _ in range(relaxation_steps):
        vor = Voronoi(points)
        new_points = []
        for i, region_index in enumerate(vor.point_region):
            region = vor.regions[region_index]
            if -1 in region or len(region) == 0:
                new_points.append(points[i])
            else:
                polygon = [vor.vertices[i] for i in region]
                centroid = np.mean(polygon, axis=0)
                new_points.append(centroid)
        points = np.array(new_points)
    
    # Sort points spatially (left-to-right, top-to-bottom) to ensure ID coherence
    # Normalized coordinates 0-1.
    # Lexsort keys are (secondary, primary). Sort by Y then X.
    # Actually, scanline order: Sort by Y (major) then X (minor) creates strips.
    # But usually X then Y is better for reading.
    # Let's do (y, x): Sort by x (secondary), y (primary)?
    # np.lexsort((points[:, 0], points[:, 1])) -> Sort by X first, then Y?
    # No, lexsort((B, A)) sorts by A then B.
    # We want standard reading order: sort by Y (rows), then X (cols).
    # Since Y is usually 0 at bottom in math, but 0 at top in images... 
    # Let's just sort by X coordinate primarily to get left-to-right progression.
    # Scanline order: Top-to-Bottom (y desc), then Left-to-Right (x asc)
    # lexsort sorts by the last key primarily.
    ind = np.lexsort((points[:, 0], -points[:, 1]))
    points = points[ind]
        
    return Voronoi(points)


def build_adjacency(vor: Voronoi) -> Dict[int, Set[int]]:
    """
    Builds graph connectivity from Voronoi ridges.
    
    Args:
        vor: Voronoi diagram
        
    Returns:
        Dictionary mapping region index to set of adjacent region indices
    """
    adjacency = collections.defaultdict(set)
    
    for p1, p2 in vor.ridge_points:
        r1 = vor.point_region[p1]
        r2 = vor.point_region[p2]
        if r1 != -1 and r2 != -1:
            adjacency[r1].add(r2)
            adjacency[r2].add(r1)
    
    return adjacency
