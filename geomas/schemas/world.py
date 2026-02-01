from typing import List, Dict, Tuple, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class TerrainType(str, Enum):
    OCEAN = "OCEAN"
    LAND = "LAND"       # Generic flat land (Plains)
    COASTAL = "COASTAL" # Land touching Ocean
    MOUNTAIN = "MOUNTAIN" # High defense bonus, movement penalty


class RelationshipState(str, Enum):
    """Diplomatic relationship state between two nations."""
    PEACE = "PEACE"       # Default, can trade normally
    WAR = "WAR"           # Cannot trade, combat enabled
    ALLIANCE = "ALLIANCE" # Mutual defense, preferred trade


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
    
    # --- CIVIL STATUS ---
    in_revolt: bool = False   # True if province is in civil unrest (no production)


class NationState(BaseModel):
    """
    Represents a nation in the simulation.
    
    Contains identity, territory, resources, military, and satisfaction metrics.
    """
    id: str
    name: str
    color: str  # Hex code or Matplotlib color
    capital_province_id: Optional[int] = None
    province_ids: List[int] = Field(default_factory=list)
    
    # --- TERRITORIAL WATERS ---
    # Ocean provinces adjacent to owned coastal provinces (exclusive economic zone)
    territorial_water_ids: List[int] = Field(default_factory=list)
    
    # --- PUBLIC SATISFACTION (0-100) ---
    public_satisfaction: float = 50.0  # 0 to 100
    
    # --- POPULATION OPINION (LLM-driven multipliers) ---
    # Multipliers range 0.1 to 2.0, applied to satisfaction changes
    population_multiplier_increase: float = 1.0  # Applied when satisfaction goes up
    population_multiplier_decrease: float = 1.0  # Applied when satisfaction goes down
    cultural_traits: List[str] = Field(default_factory=list)  # Seed-generated traits
    civil_unrest_active: bool = False  # True when satisfaction < 10, ends at > 50
    
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
    
    # --- AGGREGATE POPULATION ---
    total_population: int = 0
    total_workers: int = 0  # Sum of workers across all provinces
    
    # --- POWER PROJECTION (calculated from resources + military) ---
    # Formula: weighted sum of budget, resources, and military assets
    power_projection: float = 0.0
    
    # --- DIPLOMACY ---
    # Pending proposals received from other nations (alliance/peace requests)
    # Format: [{"type": "ALLIANCE"|"PEACE", "from": nation_id, "turn": int}, ...]
    pending_proposals: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Message cooldown: tracks last turn a message was sent to each nation
    # message_cooldown[target_id] = last_turn_sent
    # Must wait MESSAGE_COOLDOWN_TURNS before sending another to same target
    message_cooldown: Dict[str, int] = Field(default_factory=dict)


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
    
    # Relationship Matrix: relationship_matrix[A][B] = RelationshipState.WAR
    relationship_matrix: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    
    # Global Event Log for the current simulation run
    global_events: List[str] = Field(default_factory=list)
