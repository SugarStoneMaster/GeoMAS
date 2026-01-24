from typing import List, Dict, Tuple, Optional
from pydantic import BaseModel, Field
from enum import Enum


class TerrainType(str, Enum):
    OCEAN = "OCEAN"
    LAND = "LAND"       # Generic flat land (Plains)
    COASTAL = "COASTAL" # Land touching Ocean
    MOUNTAIN = "MOUNTAIN" # High defense bonus, movement penalty


class ResourceBundle(BaseModel):
    """Static resource yields for a province (base production values)."""
    energy: float = 0.0
    materials: float = 0.0
    food: float = 0.0


class ProvinceState(BaseModel):
    """
    Represents a single province (Voronoi cell) in the world.
    
    Contains both static attributes (terrain, coordinates) and dynamic state
    (population, military units, production values).
    """
    id: int
    owner_id: Optional[str] = None  # None if Ocean or Unclaimed
    terrain: TerrainType
    coordinates: Tuple[float, float]  # Centroid (x, y)
    vertices: List[Tuple[float, float]] = Field(default_factory=list)
    neighbors: List[int] = Field(default_factory=list)
    
    # --- LEGACY (kept for compatibility, will be deprecated) ---
    resources: ResourceBundle = Field(default_factory=ResourceBundle)
    
    # --- PRODUCTION (base yields per turn) ---
    food_production: float = 0.0
    energy_production: float = 0.0
    materials_production: float = 0.0
    # Tax revenue = population * tax_rate (calculated at turn start)
    tax_revenue: float = 0.0
    
    # --- POPULATION ---
    population: int = 0       # Total population in this province
    workers: int = 0          # Active workforce (population - military)
    
    # --- MILITARY UNITS ---
    soldiers: int = 0         # Ground troops stationed here
    aircraft: int = 0         # Air units stationed here
    navy: int = 0             # Naval units (only valid for OCEAN provinces)


class MinisterialState(BaseModel):
    """
    Represents the internal metrics managed by the Cabinet.
    These are nation-level aggregate values.
    """
    # DEPRECATED: Use NationState.total_budget instead
    budget: float = 1000.0
    public_satisfaction: float = 0.5  # 0.0 to 1.0


class NationState(BaseModel):
    """
    Represents a nation in the simulation.
    
    Contains identity, territory, internal state, and aggregate resources.
    """
    id: str
    name: str
    color: str  # Hex code or Matplotlib color
    capital_province_id: Optional[int] = None
    province_ids: List[int] = Field(default_factory=list)
    internal_state: MinisterialState = Field(default_factory=MinisterialState)
    
    # --- TERRITORIAL WATERS ---
    # Ocean provinces adjacent to owned coastal provinces (exclusive economic zone)
    territorial_water_ids: List[int] = Field(default_factory=list)
    
    # --- BUDGET (National Treasury) ---
    # Initialized randomly at genesis, increased only by province taxes
    total_budget: float = 0.0
    
    # --- AGGREGATE RESOURCES (calculated each turn) ---
    total_food: float = 0.0
    total_energy: float = 0.0
    total_materials: float = 0.0
    
    # --- STRATEGIC ASSETS ---
    nukes: int = 0  # Nuclear weapons (national level, not per province)
    
    # --- AGGREGATE MILITARY (derived from province sums) ---
    total_soldiers: int = 0
    total_aircraft: int = 0
    total_navy: int = 0
    total_population: int = 0
    
    # --- POWER PROJECTION (calculated from resources + military) ---
    # Formula: weighted sum of budget, resources, and military assets
    power_projection: float = 0.0


class WorldState(BaseModel):
    """
    The complete state of the simulated world at a given turn.
    
    This is the Single Source of Truth for the simulation.
    """
    turn: int = 0
    provinces: Dict[int, ProvinceState] = Field(default_factory=dict)
    nations: Dict[str, NationState] = Field(default_factory=dict)
    
    # Trust Matrix: trust_matrix[NationA][NationB] = 0.5 (A trusts B)
    trust_matrix: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    
    # Global Event Log for the current simulation run
    global_events: List[str] = Field(default_factory=list)
