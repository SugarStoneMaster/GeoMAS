import numpy as np
from scipy.spatial import Voronoi
import random
import collections
from typing import List, Dict, Tuple, Optional
from shapely.geometry import Polygon as ShapelyPolygon

from geomas.schemas.world import WorldState, ProvinceState, NationState, TerrainType, ResourceBundle, MinisterialState
from geomas.core.genesis import GenesisEngine
from geomas.world.presets import PRESET_NATIONS 

# --- PUBLIC API ---

def generate_world(seed: int = 42, history_seed: int = 99, n_cells: int = 1500, n_nations: int = 10, relaxation_steps: int = 3) -> WorldState:
    """
    Generates a deterministic WorldState using Voronoi diagrams and Organic Growth.
    Wrapper for MapGenerator.
    """
    generator = MapGenerator(seed, n_cells, n_nations, relaxation_steps)
    return generator.generate(history_seed)

# --- GENERATOR CLASS ---

class MapGenerator:
    """
    Encapsulates the procedural generation logic for the GeoMAS world.
    """
    
    def __init__(self, seed: int, n_cells: int, n_nations: int, relaxation_steps: int):
        self.seed = seed
        self.n_cells = n_cells
        self.n_nations = min(n_nations, len(PRESET_NATIONS))
        self.relaxation_steps = relaxation_steps
        
        # State
        self.rng = np.random.RandomState(seed)
        random.seed(seed)
        
        self.vor: Optional[Voronoi] = None
        self.adjacency = collections.defaultdict(set)
        
        self.land_indices: List[int] = []
        self.ocean_indices: List[int] = []
        self.cell_centroids: Dict[int, np.ndarray] = {}
        self.cell_vertices: Dict[int, List[Tuple[float, float]]] = {}
        
        self.nations_dict: Dict[str, NationState] = {}
        self.provinces_dict: Dict[int, ProvinceState] = {}

    def generate(self, history_seed: int) -> WorldState:
        """Main pipeline."""
        self._generate_voronoi()
        self._build_adjacency()
        self._generate_geography()
        self._assign_nations()
        self._create_provinces()
        self._refine_capitals()
        
        # Assemble World
        world = WorldState(
            turn=0, # FIX: Start at 0 (Genesis state)
            provinces=self.provinces_dict,
            nations=self.nations_dict,
            trust_matrix={} # Filled by Genesis
        )
        
        # Run Genesis
        genesis = GenesisEngine(world, seed=history_seed)
        genesis.initialize_history(years=50)
        
        return world

    def _generate_voronoi(self):
        """Generates Voronoi diagram with Lloyd's relaxation."""
        points = self.rng.rand(self.n_cells, 2)
        
        for _ in range(self.relaxation_steps):
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
            
        self.vor = Voronoi(points)

    def _build_adjacency(self):
        """Builds graph connectivity from Voronoi ridges."""
        for p1, p2 in self.vor.ridge_points:
            r1 = self.vor.point_region[p1]
            r2 = self.vor.point_region[p2]
            if r1 != -1 and r2 != -1:
                self.adjacency[r1].add(r2)
                self.adjacency[r2].add(r1)

    def _generate_geography(self):
        """Defines Land vs Ocean using Tectonic Plates logic."""
        n_continents = self.rng.randint(4, 7)
        continent_centers = []
        
        # Rejection Sampling for centers
        attempts = 0
        while len(continent_centers) < n_continents and attempts < 1000:
            candidate = self.rng.rand(2)
            if not (0.1 < candidate[0] < 0.9 and 0.1 < candidate[1] < 0.9):
                attempts += 1; continue
            
            too_close = False
            for c in continent_centers:
                if np.linalg.norm(candidate - c) < 0.35: 
                    too_close = True; break
            
            if not too_close: continent_centers.append(candidate)
            attempts += 1
            
        continent_centers = np.array(continent_centers)
        continent_radii = [self.rng.uniform(0.12, 0.20) for _ in range(len(continent_centers))]
        
        # Classify Cells
        for i, region_index in enumerate(self.vor.point_region):
            region = self.vor.regions[region_index]
            if -1 in region or len(region) == 0:
                self.ocean_indices.append(region_index)
                continue
            
            # Geometry
            polygon_verts = np.array([self.vor.vertices[v] for v in region])
            self.cell_vertices[region_index] = [(float(v[0]), float(v[1])) for v in polygon_verts]
            centroid = np.mean(polygon_verts, axis=0)
            self.cell_centroids[region_index] = centroid
            
            # Land Check
            dists = np.linalg.norm(centroid - continent_centers, axis=1)
            closest_idx = np.argmin(dists)
            min_dist = dists[closest_idx]
            noise = (self.rng.rand() - 0.5) * 0.08
            
            if min_dist + noise < continent_radii[closest_idx]:
                self.land_indices.append(region_index)
            else:
                self.ocean_indices.append(region_index)

    def _assign_nations(self):
        """Assigns land cells to nations using Voronoi clustering."""
        if len(self.land_indices) < self.n_nations:
            self.n_nations = max(1, len(self.land_indices))
            
        self.land_indices.sort()
        initial_capitals = random.sample(self.land_indices, self.n_nations)
        
        # Create Nation Objects
        for i in range(self.n_nations):
            preset = PRESET_NATIONS[i]
            nation_id = preset["id"]
            self.nations_dict[nation_id] = NationState(
                id=nation_id,
                name=preset["name"],
                color=preset["color"],
                capital_province_id=initial_capitals[i],
                province_ids=[],
                internal_state=MinisterialState()
            )
            
        # Assign Provinces to closest Capital
        self.political_map = {} # region_idx -> nation_id
        
        for region_idx in self.land_indices:
            my_loc = self.cell_centroids[region_idx]
            closest_nation_id = None
            min_dist = float('inf')
            
            for nation_id, nation in self.nations_dict.items():
                cap_loc = self.cell_centroids[nation.capital_province_id]
                dist = np.linalg.norm(my_loc - cap_loc)
                if dist < min_dist:
                    min_dist = dist
                    closest_nation_id = nation_id
            
            self.political_map[region_idx] = closest_nation_id
            self.nations_dict[closest_nation_id].province_ids.append(region_idx)

    def _create_provinces(self):
        """Instantiates ProvinceState objects with terrain and resources."""
        
        # Helper
        def get_neighbors(r_idx):
            return list(self.adjacency[r_idx])

        # Land Provinces
        for r_idx in self.land_indices:
            nation_id = self.political_map[r_idx]
            
            # Coastal Check
            is_coastal = False
            for n_idx in get_neighbors(r_idx):
                if n_idx in self.ocean_indices:
                    is_coastal = True; break
            
            # Terrain
            if is_coastal:
                terrain = TerrainType.COASTAL
            elif self.rng.rand() < 0.2:
                terrain = TerrainType.MOUNTAIN
            else:
                terrain = TerrainType.LAND
                
            # Resources
            res = self._generate_resources(terrain)
            
            self.provinces_dict[r_idx] = ProvinceState(
                id=r_idx,
                owner_id=nation_id,
                terrain=terrain,
                coordinates=(float(self.cell_centroids[r_idx][0]), float(self.cell_centroids[r_idx][1])),
                vertices=self.cell_vertices[r_idx],
                resources=res,
                neighbors=get_neighbors(r_idx)
            )
            
        # Ocean Provinces
        for r_idx in self.ocean_indices:
            if r_idx not in self.cell_centroids: continue
            
            self.provinces_dict[r_idx] = ProvinceState(
                id=r_idx,
                owner_id=None,
                terrain=TerrainType.OCEAN,
                coordinates=(float(self.cell_centroids[r_idx][0]), float(self.cell_centroids[r_idx][1])),
                vertices=self.cell_vertices[r_idx],
                resources=ResourceBundle(food=self.rng.uniform(10, 30)),
                neighbors=get_neighbors(r_idx)
            )

    def _generate_resources(self, terrain: TerrainType) -> ResourceBundle:
        res = ResourceBundle()
        if terrain == TerrainType.COASTAL:
            res.food = self.rng.uniform(50, 100)
            res.energy = self.rng.uniform(10, 50)
            res.materials = self.rng.uniform(10, 40)
        elif terrain == TerrainType.MOUNTAIN:
            res.food = self.rng.uniform(5, 20)
            res.energy = self.rng.uniform(0, 20)
            res.materials = self.rng.uniform(80, 150)
        else: # LAND
            res.food = self.rng.uniform(40, 80)
            res.energy = self.rng.uniform(30, 80)
            res.materials = self.rng.uniform(30, 60)
        return res

    def _refine_capitals(self):
        """Moves capital to the largest province in the nation."""
        for nation in self.nations_dict.values():
            max_area = -1.0
            best_capital = nation.capital_province_id
            
            for p_id in nation.province_ids:
                prov = self.provinces_dict[p_id]
                if prov.vertices and len(prov.vertices) >= 3:
                    poly = ShapelyPolygon(prov.vertices)
                    area = poly.area
                    if area > max_area:
                        max_area = area
                        best_capital = p_id
            
            nation.capital_province_id = best_capital
