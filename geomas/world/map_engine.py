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
    
    # --- CONFIGURATION ---
    # Population distribution
    POP_MIN = 500
    POP_MAX = 5000
    
    # Military distribution (% of population that starts as soldiers)
    INITIAL_MILITARY_RATIO_MIN = 0.02  # 2%
    INITIAL_MILITARY_RATIO_MAX = 0.08  # 8%
    
    # Budget distribution
    BUDGET_MIN = 500.0
    BUDGET_MAX = 3000.0
    
    # Nukes: 2-3 nations get nukes
    NUKE_NATIONS_MIN = 2
    NUKE_NATIONS_MAX = 3
    NUKES_PER_NATION_MIN = 1
    NUKES_PER_NATION_MAX = 5
    
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
        self._assign_territorial_waters()
        self._distribute_nukes()
        self._calculate_nation_aggregates()
        
        # Assemble World
        world = WorldState(
            turn=0,
            provinces=self.provinces_dict,
            nations=self.nations_dict,
            trust_matrix={}  # Filled by Genesis
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
            
            # Random initial budget
            initial_budget = self.rng.uniform(self.BUDGET_MIN, self.BUDGET_MAX)
            
            self.nations_dict[nation_id] = NationState(
                id=nation_id,
                name=preset["name"],
                color=preset["color"],
                capital_province_id=initial_capitals[i],
                province_ids=[],
                internal_state=MinisterialState(budget=initial_budget),
                total_budget=initial_budget
            )
            
        # Assign Provinces to closest Capital
        self.political_map = {}  # region_idx -> nation_id
        
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
        """Instantiates ProvinceState objects with terrain, resources, population, and military."""
        
        def get_neighbors(r_idx):
            return list(self.adjacency[r_idx])

        # Land Provinces
        for r_idx in self.land_indices:
            nation_id = self.political_map[r_idx]
            
            # Coastal Check
            is_coastal = False
            for n_idx in get_neighbors(r_idx):
                if n_idx in self.ocean_indices:
                    is_coastal = True
                    break
            
            # Terrain
            if is_coastal:
                terrain = TerrainType.COASTAL
            elif self.rng.rand() < 0.2:
                terrain = TerrainType.MOUNTAIN
            else:
                terrain = TerrainType.LAND
                
            # Resources (legacy bundle)
            res = self._generate_resources(terrain)
            
            # Population (random based on terrain)
            if terrain == TerrainType.MOUNTAIN:
                population = int(self.rng.uniform(self.POP_MIN * 0.3, self.POP_MAX * 0.5))
            elif terrain == TerrainType.COASTAL:
                population = int(self.rng.uniform(self.POP_MIN * 1.2, self.POP_MAX * 1.5))
            else:
                population = int(self.rng.uniform(self.POP_MIN, self.POP_MAX))
            
            # Initial military (% of population)
            military_ratio = self.rng.uniform(self.INITIAL_MILITARY_RATIO_MIN, self.INITIAL_MILITARY_RATIO_MAX)
            soldiers = int(population * military_ratio)
            workers = population - soldiers
            
            # Production values (based on terrain and workers)
            food_prod, energy_prod, materials_prod = self._calculate_production(terrain, workers)
            
            # Tax revenue (proportional to population)
            tax_rate = 0.1  # 10% base tax rate
            tax_revenue = population * tax_rate
            
            self.provinces_dict[r_idx] = ProvinceState(
                id=r_idx,
                owner_id=nation_id,
                terrain=terrain,
                coordinates=(float(self.cell_centroids[r_idx][0]), float(self.cell_centroids[r_idx][1])),
                vertices=self.cell_vertices[r_idx],
                resources=res,
                neighbors=get_neighbors(r_idx),
                # New fields
                population=population,
                workers=workers,
                soldiers=soldiers,
                aircraft=0,
                navy=0,
                food_production=food_prod,
                energy_production=energy_prod,
                materials_production=materials_prod,
                tax_revenue=tax_revenue
            )
            
        # Ocean Provinces
        for r_idx in self.ocean_indices:
            if r_idx not in self.cell_centroids:
                continue
            
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
        """Legacy resource bundle generation."""
        res = ResourceBundle()
        if terrain == TerrainType.COASTAL:
            res.food = self.rng.uniform(50, 100)
            res.energy = self.rng.uniform(10, 50)
            res.materials = self.rng.uniform(10, 40)
        elif terrain == TerrainType.MOUNTAIN:
            res.food = self.rng.uniform(5, 20)
            res.energy = self.rng.uniform(0, 20)
            res.materials = self.rng.uniform(80, 150)
        else:  # LAND
            res.food = self.rng.uniform(40, 80)
            res.energy = self.rng.uniform(30, 80)
            res.materials = self.rng.uniform(30, 60)
        return res

    def _calculate_production(self, terrain: TerrainType, workers: int) -> Tuple[float, float, float]:
        """Calculate production values based on terrain and workforce."""
        # Base yields per worker
        if terrain == TerrainType.COASTAL:
            food_yield = 0.08
            energy_yield = 0.03
            materials_yield = 0.02
        elif terrain == TerrainType.MOUNTAIN:
            food_yield = 0.02
            energy_yield = 0.01
            materials_yield = 0.10
        else:  # LAND
            food_yield = 0.06
            energy_yield = 0.05
            materials_yield = 0.04
        
        # Add random variation
        food_prod = workers * food_yield * self.rng.uniform(0.8, 1.2)
        energy_prod = workers * energy_yield * self.rng.uniform(0.8, 1.2)
        materials_prod = workers * materials_yield * self.rng.uniform(0.8, 1.2)
        
        return food_prod, energy_prod, materials_prod

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

    def _assign_territorial_waters(self):
        """
        Assigns ocean provinces adjacent to coastal provinces as territorial waters.
        These become owned by the nation that controls the adjacent coast.
        """
        for r_idx in self.ocean_indices:
            if r_idx not in self.provinces_dict:
                continue
            
            ocean_prov = self.provinces_dict[r_idx]
            
            # Check all neighbors for coastal provinces
            adjacent_nations = set()
            for neighbor_idx in ocean_prov.neighbors:
                neighbor = self.provinces_dict.get(neighbor_idx)
                if neighbor and neighbor.terrain == TerrainType.COASTAL and neighbor.owner_id:
                    adjacent_nations.add(neighbor.owner_id)
            
            # If exactly one nation is adjacent, they own this water
            if len(adjacent_nations) == 1:
                owner_id = list(adjacent_nations)[0]
                ocean_prov.owner_id = owner_id
                self.nations_dict[owner_id].territorial_water_ids.append(r_idx)
            # If multiple nations are adjacent, it stays international waters (None)

    def _distribute_nukes(self):
        """
        Distributes nuclear weapons to 2-3 nations randomly.
        Other nations get 0 nukes.
        """
        nation_ids = list(self.nations_dict.keys())
        
        # Need at least NUKE_NATIONS_MIN nations to distribute nukes
        if len(nation_ids) < self.NUKE_NATIONS_MIN:
            return
        
        # Select 2-3 nations to have nukes (but not more than total nations)
        max_nuclear = min(self.NUKE_NATIONS_MAX, len(nation_ids))
        min_nuclear = min(self.NUKE_NATIONS_MIN, max_nuclear)
        
        if min_nuclear >= max_nuclear:
            n_nuclear_nations = min_nuclear
        else:
            n_nuclear_nations = self.rng.randint(min_nuclear, max_nuclear + 1)
        
        nuclear_nations = self.rng.choice(nation_ids, size=n_nuclear_nations, replace=False)
        
        for nation_id in nuclear_nations:
            nuke_count = self.rng.randint(self.NUKES_PER_NATION_MIN, self.NUKES_PER_NATION_MAX + 1)
            self.nations_dict[nation_id].nukes = int(nuke_count)

    def _calculate_nation_aggregates(self):
        """
        Calculates aggregate values for each nation from their provinces.
        """
        for nation in self.nations_dict.values():
            total_pop = 0
            total_soldiers = 0
            total_aircraft = 0
            total_navy = 0
            total_food = 0.0
            total_energy = 0.0
            total_materials = 0.0
            
            for p_id in nation.province_ids:
                prov = self.provinces_dict[p_id]
                total_pop += prov.population
                total_soldiers += prov.soldiers
                total_aircraft += prov.aircraft
                total_navy += prov.navy
                total_food += prov.food_production
                total_energy += prov.energy_production
                total_materials += prov.materials_production
            
            # Also count military in territorial waters
            for p_id in nation.territorial_water_ids:
                prov = self.provinces_dict.get(p_id)
                if prov:
                    total_navy += prov.navy
            
            nation.total_population = total_pop
            nation.total_soldiers = total_soldiers
            nation.total_aircraft = total_aircraft
            nation.total_navy = total_navy
            nation.total_food = total_food
            nation.total_energy = total_energy
            nation.total_materials = total_materials
            
            # Calculate power projection
            nation.power_projection = self._calculate_power_projection(nation)

    def _calculate_power_projection(self, nation: NationState) -> float:
        """
        Calculates a nation's power projection score.
        Weighted sum of economic and military strength.
        """
        # Weights
        W_BUDGET = 0.001
        W_FOOD = 0.01
        W_ENERGY = 0.02
        W_MATERIALS = 0.03
        W_SOLDIERS = 0.1
        W_AIRCRAFT = 0.5
        W_NAVY = 0.3
        W_NUKES = 50.0
        
        score = (
            nation.total_budget * W_BUDGET +
            nation.total_food * W_FOOD +
            nation.total_energy * W_ENERGY +
            nation.total_materials * W_MATERIALS +
            nation.total_soldiers * W_SOLDIERS +
            nation.total_aircraft * W_AIRCRAFT +
            nation.total_navy * W_NAVY +
            nation.nukes * W_NUKES
        )
        
        return round(score, 2)
