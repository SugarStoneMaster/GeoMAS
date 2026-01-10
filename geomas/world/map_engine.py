import numpy as np
from scipy.spatial import Voronoi
import random
import collections
from typing import List, Dict, Tuple
from shapely.geometry import Polygon as ShapelyPolygon

from geomas.schemas.models import WorldState, ProvinceState, NationState, TerrainType, ResourceBundle, MinisterialState
from geomas.core.genesis import GenesisEngine # NEW IMPORT

# --- STATIC NATION DEFINITIONS (High Contrast Palette) ---
PRESET_NATIONS = [
    {"id": "AGRIA", "name": "🔴 Republic of Agria", "color": "#E6194B"},     # Red
    {"id": "KRELL", "name": "🔵 Union of Krell", "color": "#4363d8"},        # Blue
    {"id": "OSTER", "name": "🟢 Osterland Federation", "color": "#3CB44B"},  # Green
    {"id": "ZENTORA", "name": "🟡 Zentora Empire", "color": "#FFE119"},      # Yellow
    {"id": "VALKYR", "name": "🟣 Valkyria", "color": "#911EB4"},             # Purple
    {"id": "SYLVAN", "name": "🟠 Sylvania", "color": "#f58231"},             # Orange
    {"id": "NORD", "name": "⚫ Nordland", "color": "#A9A9A9"},               # Dark Grey
    {"id": "MERIDIA", "name": "🧊 Meridia", "color": "#42d4f4"},             # Cyan
    {"id": "EQUAT", "name": "🌸 Equatoria", "color": "#f032e6"},             # Magenta
    {"id": "DRAKON", "name": "🟤 Drakonia", "color": "#9A6324"},             # Brown
]

def generate_world(seed: int = 42, history_seed: int = 99, n_cells: int = 1500, n_nations: int = 10, relaxation_steps: int = 3) -> WorldState:
    """
    Generates a deterministic WorldState using Voronoi diagrams and Organic Growth.
    Uses PRESET_NATIONS to ensure persistent identity across runs.
    
    Args:
        seed: Controls map geometry (Voronoi, Continents).
        history_seed: Controls historical events (Genesis).
    """
    
    # 1. Deterministic Seeding (Map)
    rng = np.random.RandomState(seed)
    random.seed(seed) 

    # 2. Initialize random seeds (provinces)
    points = rng.rand(n_cells, 2)

    # 3. Lloyd's Relaxation (Smoothing)
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

    # 4. Compute Final Voronoi Diagram
    vor = Voronoi(points)

    # 5. Build Adjacency Graph
    adjacency = collections.defaultdict(set)
    for p1, p2 in vor.ridge_points:
        r1 = vor.point_region[p1]
        r2 = vor.point_region[p2]
        if r1 != -1 and r2 != -1:
            adjacency[r1].add(r2)
            adjacency[r2].add(r1)

    # 6. Define Geography: "Tectonic Plates"
    n_continents = rng.randint(4, 7) 
    continent_centers = []
    
    attempts = 0
    while len(continent_centers) < n_continents and attempts < 1000:
        candidate = rng.rand(2)
        if not (0.1 < candidate[0] < 0.9 and 0.1 < candidate[1] < 0.9):
            attempts += 1
            continue
        too_close = False
        for c in continent_centers:
            if np.linalg.norm(candidate - c) < 0.35: 
                too_close = True
                break
        if not too_close:
            continent_centers.append(candidate)
        attempts += 1
    
    continent_centers = np.array(continent_centers)
    
    land_region_indices = []
    ocean_region_indices = []
    cell_centroids = {}
    cell_vertices = {} 
    
    continent_radii = [rng.uniform(0.12, 0.20) for _ in range(len(continent_centers))]

    for i, region_index in enumerate(vor.point_region):
        region = vor.regions[region_index]
        if -1 in region or len(region) == 0:
            ocean_region_indices.append(region_index)
            continue
        
        polygon_verts = np.array([vor.vertices[v] for v in region])
        cell_vertices[region_index] = [(float(v[0]), float(v[1])) for v in polygon_verts]
        
        centroid = np.mean(polygon_verts, axis=0)
        cell_centroids[region_index] = centroid
        
        dists = np.linalg.norm(centroid - continent_centers, axis=1)
        closest_idx = np.argmin(dists)
        min_dist = dists[closest_idx]
        
        noise = (rng.rand() - 0.5) * 0.08
        
        if min_dist + noise < continent_radii[closest_idx]:
            land_region_indices.append(region_index)
        else:
            ocean_region_indices.append(region_index)

    # 7. Assign Nations
    n_nations = min(n_nations, len(PRESET_NATIONS))
    
    if len(land_region_indices) < n_nations:
        n_nations = max(1, len(land_region_indices))

    land_region_indices.sort() 
    
    initial_capitals = random.sample(land_region_indices, n_nations)
    
    political_map = {} 
    
    for region_idx in land_region_indices:
        my_loc = cell_centroids[region_idx]
        closest_capital_idx = -1
        min_dist = float('inf')
        
        for nation_idx, cap_region_idx in enumerate(initial_capitals):
            cap_loc = cell_centroids[cap_region_idx]
            dist = np.linalg.norm(my_loc - cap_loc)
            if dist < min_dist:
                min_dist = dist
                closest_capital_idx = nation_idx
        
        political_map[region_idx] = closest_capital_idx

    # 8. Construct Pydantic Models
    
    # 8a. Create Nations using PRESETS
    nations_dict: Dict[str, NationState] = {}
    
    for i in range(n_nations):
        preset = PRESET_NATIONS[i]
        nation_id = preset["id"]
        
        nations_dict[nation_id] = NationState(
            id=nation_id,
            name=preset["name"], 
            color=preset["color"],
            capital_province_id=initial_capitals[i], 
            province_ids=[], 
            internal_state=MinisterialState()
        )

    # 8b. Create Provinces
    provinces_dict: Dict[int, ProvinceState] = {}
    
    def get_neighbors_list(r_idx):
        return list(adjacency[r_idx])

    # Process Land
    for r_idx in land_region_indices:
        nation_idx = political_map[r_idx]
        nation_id = PRESET_NATIONS[nation_idx]["id"]
        
        nations_dict[nation_id].province_ids.append(r_idx)
        
        is_coastal = False
        for n_idx in get_neighbors_list(r_idx):
            if n_idx in ocean_region_indices:
                is_coastal = True
                break
        
        # Determine Terrain
        if is_coastal:
            terrain = TerrainType.COASTAL
        else:
            if rng.rand() < 0.2: 
                terrain = TerrainType.MOUNTAIN
            else:
                terrain = TerrainType.LAND
        
        res = ResourceBundle()
        if terrain == TerrainType.COASTAL:
            res.food = rng.uniform(50, 100)
            res.energy = rng.uniform(10, 50)
            res.materials = rng.uniform(10, 40)
        elif terrain == TerrainType.MOUNTAIN:
            res.food = rng.uniform(5, 20)      
            res.energy = rng.uniform(0, 20)
            res.materials = rng.uniform(80, 150) 
        else: 
            res.food = rng.uniform(40, 80)
            res.energy = rng.uniform(30, 80)
            res.materials = rng.uniform(30, 60)

        provinces_dict[r_idx] = ProvinceState(
            id=r_idx,
            owner_id=nation_id,
            terrain=terrain,
            coordinates=(float(cell_centroids[r_idx][0]), float(cell_centroids[r_idx][1])),
            vertices=cell_vertices[r_idx],
            resources=res,
            neighbors=get_neighbors_list(r_idx)
        )

    # Process Ocean
    for r_idx in ocean_region_indices:
        if r_idx not in cell_centroids: continue
        
        provinces_dict[r_idx] = ProvinceState(
            id=r_idx,
            owner_id=None,
            terrain=TerrainType.OCEAN,
            coordinates=(float(cell_centroids[r_idx][0]), float(cell_centroids[r_idx][1])),
            vertices=cell_vertices[r_idx],
            resources=ResourceBundle(food=rng.uniform(10, 30)), 
            neighbors=get_neighbors_list(r_idx)
        )

    # RE-ASSIGN CAPITALS BASED ON AREA
    for nation_id, nation in nations_dict.items():
        max_area = -1.0
        best_capital = nation.capital_province_id 
        
        for p_id in nation.province_ids:
            prov = provinces_dict[p_id]
            if prov.vertices and len(prov.vertices) >= 3:
                poly = ShapelyPolygon(prov.vertices)
                area = poly.area
                if area > max_area:
                    max_area = area
                    best_capital = p_id
        
        nation.capital_province_id = best_capital

    # 9. Initialize Trust Matrix (Placeholder)
    # We initialize it empty here, Genesis will fill it.
    trust_matrix = {}
    
    # 10. Assemble World
    world = WorldState(
        turn=1,
        provinces=provinces_dict,
        nations=nations_dict,
        trust_matrix=trust_matrix
    )
    
    # 11. RUN GENESIS (History Generation)
    # This populates trust_matrix and global_events
    genesis = GenesisEngine(world, seed=history_seed)
    genesis.initialize_history(years=50)
    
    return world
