import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import Voronoi
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
import random

def generate_map(n_cells=500, n_nations=15, relaxation_steps=3):
    """
    Generates a synthetic map using Voronoi diagrams with distinct, separated continents.
    """
    # 1. Initialize random seeds (provinces)
    points = np.random.rand(n_cells, 2)

    # 2. Lloyd's Relaxation (Smoothing)
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

    # 3. Compute Final Voronoi Diagram
    vor = Voronoi(points)

    # 4. Define Geography: "Tectonic Plates" approach
    # We place seeds far apart, and land only grows around them up to a limit.
    
    n_continents = random.randint(4, 6)
    continent_centers = []
    
    # Rejection Sampling to ensure continents are far apart
    attempts = 0
    while len(continent_centers) < n_continents and attempts < 1000:
        candidate = np.random.rand(2)
        # Keep away from edges
        if not (0.1 < candidate[0] < 0.9 and 0.1 < candidate[1] < 0.9):
            attempts += 1
            continue
            
        # Keep away from other continents
        too_close = False
        for c in continent_centers:
            if np.linalg.norm(candidate - c) < 0.35: # Minimum separation
                too_close = True
                break
        
        if not too_close:
            continent_centers.append(candidate)
        attempts += 1
    
    continent_centers = np.array(continent_centers)
    
    # Assign land based on distance to these centers
    land_cells = []
    ocean_cells = []
    cell_centroids = {}

    # Each continent gets a random "radius" to vary size
    continent_radii = [random.uniform(0.12, 0.20) for _ in range(len(continent_centers))]

    for i, region_index in enumerate(vor.point_region):
        region = vor.regions[region_index]
        if -1 in region or len(region) == 0:
            ocean_cells.append(region_index)
            continue
        
        polygon_verts = np.array([vor.vertices[v] for v in region])
        centroid = np.mean(polygon_verts, axis=0)
        cell_centroids[region_index] = centroid
        
        # Find closest continent center
        dists = np.linalg.norm(centroid - continent_centers, axis=1)
        closest_idx = np.argmin(dists)
        min_dist = dists[closest_idx]
        
        # Add noise to the radius check for jagged coastlines
        noise = (np.random.rand() - 0.5) * 0.08
        
        if min_dist + noise < continent_radii[closest_idx]:
            land_cells.append(region_index)
        else:
            ocean_cells.append(region_index)

    # 5. Assign Nations
    # Ensure we have enough land
    if len(land_cells) < n_nations:
        print(f"Warning: Low land count ({len(land_cells)}). Reducing nations.")
        n_nations = max(1, len(land_cells))

    # Simple Random Sampling for Capitals (Robust)
    capitals = random.sample(land_cells, n_nations)
    
    political_map = {}
    
    # Assign every land cell to the closest capital
    for region_idx in land_cells:
        my_loc = cell_centroids[region_idx]
        
        closest_capital = None
        min_dist = float('inf')
        
        for nation_id, cap_idx in enumerate(capitals):
            cap_loc = cell_centroids[cap_idx]
            dist = np.linalg.norm(my_loc - cap_loc)
            if dist < min_dist:
                min_dist = dist
                closest_capital = nation_id
        
        political_map[region_idx] = closest_capital

    return vor, land_cells, ocean_cells, political_map, n_nations

def plot_map(vor, land_cells, ocean_cells, political_map, n_nations):
    """
    Visualizes the generated map.
    """
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Colors: Generate N distinct colors using HSV to ensure variety
    # Then convert to RGB. This guarantees we have exactly n_nations distinct colors.
    cmap = plt.get_cmap('gist_ncar') # A map with many colors
    nation_colors = [cmap(i) for i in np.linspace(0.1, 0.9, n_nations)]
    random.shuffle(nation_colors) # Shuffle so neighbors don't look similar

    patches = []
    colors = []

    # Draw Ocean
    for r_idx in ocean_cells:
        region = vor.regions[r_idx]
        if -1 in region or len(region) == 0: continue
        polygon = Polygon([vor.vertices[i] for i in region])
        patches.append(polygon)
        colors.append((0.75, 0.85, 1.0)) # Lighter Blue

    # Draw Land / Nations
    for r_idx in land_cells:
        region = vor.regions[r_idx]
        if -1 in region or len(region) == 0: continue
        polygon = Polygon([vor.vertices[i] for i in region])
        patches.append(polygon)
        
        nation_id = political_map.get(r_idx)
        if nation_id is not None:
            colors.append(nation_colors[nation_id])
        else:
            colors.append((0.5, 0.5, 0.5)) # Error color

    p = PatchCollection(patches, match_original=True)
    p.set_facecolor(colors)
    p.set_edgecolor('black')
    p.set_linewidth(0.2) # Thinner lines for cleaner look
    
    ax.add_collection(p)
    
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    plt.title(f"GeoMAS Map: {n_nations} Nations, {len(land_cells)} Land Provinces", fontsize=15)
    plt.show()

if __name__ == "__main__":
    print("Generating World...")
    vor, land, ocean, pol_map, n_nations = generate_map(n_cells=500, n_nations=10, relaxation_steps=14)
    print(f"Map Generated: {len(land)} Land Provinces.")
    print("Rendering...")
    plot_map(vor, land, ocean, pol_map, n_nations)
