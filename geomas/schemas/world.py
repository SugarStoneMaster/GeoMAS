from typing import List, Dict, Tuple, Optional
from pydantic import BaseModel, Field
from enum import Enum

class TerrainType(str, Enum):
    OCEAN = "OCEAN"
    LAND = "LAND"       # Generic flat land (Plains)
    COASTAL = "COASTAL" # Land touching Ocean
    MOUNTAIN = "MOUNTAIN" # High defense bonus, movement penalty

class ResourceBundle(BaseModel):
    energy: float = 0.0
    materials: float = 0.0
    food: float = 0.0

class ProvinceState(BaseModel):
    id: int
    owner_id: Optional[str] = None  # None if Ocean or Unclaimed
    terrain: TerrainType
    coordinates: Tuple[float, float]  # Centroid (x, y)
    vertices: List[Tuple[float, float]] = Field(default_factory=list) # Polygon vertices for rendering
    resources: ResourceBundle = Field(default_factory=ResourceBundle)
    population: int = 0
    neighbors: List[int] = Field(default_factory=list)  # Adjacency list (Province IDs)

class MinisterialState(BaseModel):
    """Represents the internal metrics managed by the Cabinet."""
    budget: float = 1000.0
    public_satisfaction: float = 0.5  # 0.0 to 1.0
    military_readiness: float = 0.5   # 0.0 to 1.0
    tech_level: float = 1.0

class NationState(BaseModel):
    id: str
    name: str
    color: str  # Hex code or Matplotlib color
    capital_province_id: Optional[int] = None
    province_ids: List[int] = Field(default_factory=list)
    internal_state: MinisterialState = Field(default_factory=MinisterialState)

class WorldState(BaseModel):
    turn: int = 0 # FIX: Start at 0 (Genesis state)
    provinces: Dict[int, ProvinceState] = Field(default_factory=dict)
    nations: Dict[str, NationState] = Field(default_factory=dict)
    
    # Trust Matrix: trust_matrix[NationA][NationB] = 0.5 (A trusts B)
    trust_matrix: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    
    # Global Event Log for the current simulation run
    global_events: List[str] = Field(default_factory=list)
