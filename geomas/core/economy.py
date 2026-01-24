"""
Economy Module - Pure deterministic functions for economic calculations.

All functions in this module are stateless and deterministic.
They take state as input and return calculated values, never modifying state directly.
"""

from typing import Dict, Tuple
from geomas.schemas.world import WorldState, NationState, ProvinceState


# --- CONSUMPTION CONSTANTS ---
FOOD_PER_PERSON = 1.0  # 1 food per person per turn
ENERGY_PER_PERSON = 0.5  # 0.5 energy per person per turn

# Military maintenance costs per unit per turn
MAINTENANCE_SOLDIER = 0.1  # materials per soldier
MAINTENANCE_AIRCRAFT = 2.0  # materials per aircraft
MAINTENANCE_NAVY = 1.5  # materials per navy ship

# Production penalty thresholds
MIN_WORKFORCE_RATIO = 0.5  # Below this, production suffers


# --- CONSUMPTION CALCULATIONS ---

def calculate_food_consumption(total_population: int) -> float:
    """
    Calculate food consumption for a nation.
    
    Args:
        total_population: Total population of the nation
        
    Returns:
        Total food consumed per turn
    """
    return total_population * FOOD_PER_PERSON


def calculate_energy_consumption(total_population: int) -> float:
    """
    Calculate energy consumption for a nation.
    
    Args:
        total_population: Total population of the nation
        
    Returns:
        Total energy consumed per turn
    """
    return total_population * ENERGY_PER_PERSON


def calculate_materials_consumption(
    total_soldiers: int,
    total_aircraft: int,
    total_navy: int
) -> float:
    """
    Calculate materials consumption for military maintenance.
    
    Args:
        total_soldiers: Total ground troops
        total_aircraft: Total air units
        total_navy: Total naval units
        
    Returns:
        Total materials consumed per turn for military upkeep
    """
    return (
        total_soldiers * MAINTENANCE_SOLDIER +
        total_aircraft * MAINTENANCE_AIRCRAFT +
        total_navy * MAINTENANCE_NAVY
    )


# --- PRODUCTION CALCULATIONS ---

def calculate_production_penalty(workers: int, population: int) -> float:
    """
    Calculate production penalty based on workforce availability.
    
    When too many people are in the military, production suffers.
    
    Args:
        workers: Active workers (non-military population)
        population: Total population
        
    Returns:
        Multiplier between 0.0 and 1.0 (1.0 = no penalty)
    """
    if population == 0:
        return 0.0
    
    workforce_ratio = workers / population
    
    if workforce_ratio >= MIN_WORKFORCE_RATIO:
        return 1.0
    else:
        # Linear penalty below threshold
        return workforce_ratio / MIN_WORKFORCE_RATIO


def calculate_tax_collection(nation: NationState, world: WorldState) -> float:
    """
    Calculate total tax revenue from all provinces.
    
    Args:
        nation: The nation collecting taxes
        world: Current world state
        
    Returns:
        Total tax collected this turn
    """
    total_tax = 0.0
    for p_id in nation.province_ids:
        province = world.provinces.get(p_id)
        if province:
            total_tax += province.tax_revenue
    return total_tax


# --- AGGREGATE CALCULATIONS ---

def calculate_nation_aggregates(nation: NationState, world: WorldState) -> Dict[str, float]:
    """
    Calculate all aggregate values for a nation from its provinces.
    
    Args:
        nation: The nation to calculate for
        world: Current world state
        
    Returns:
        Dictionary with aggregate values
    """
    total_pop = 0
    total_soldiers = 0
    total_aircraft = 0
    total_navy = 0
    total_food_prod = 0.0
    total_energy_prod = 0.0
    total_materials_prod = 0.0
    
    for p_id in nation.province_ids:
        prov = world.provinces.get(p_id)
        if prov:
            total_pop += prov.population
            total_soldiers += prov.soldiers
            total_aircraft += prov.aircraft
            total_navy += prov.navy
            total_food_prod += prov.food_production
            total_energy_prod += prov.energy_production
            total_materials_prod += prov.materials_production
    
    # Also count navy in territorial waters
    for p_id in nation.territorial_water_ids:
        prov = world.provinces.get(p_id)
        if prov:
            total_navy += prov.navy
    
    return {
        "total_population": total_pop,
        "total_soldiers": total_soldiers,
        "total_aircraft": total_aircraft,
        "total_navy": total_navy,
        "total_food_production": total_food_prod,
        "total_energy_production": total_energy_prod,
        "total_materials_production": total_materials_prod,
    }


def calculate_power_projection(nation: NationState) -> float:
    """
    Calculate a nation's power projection score.
    
    Weighted sum of economic and military strength.
    
    Args:
        nation: The nation to evaluate
        
    Returns:
        Power projection score
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


# --- RESOURCE BALANCE ---

def calculate_resource_balance(nation: NationState, world: WorldState) -> Dict[str, float]:
    """
    Calculate net resource balance for a nation (production - consumption).
    
    Args:
        nation: The nation to evaluate
        world: Current world state
        
    Returns:
        Dictionary with net balance for each resource type
    """
    aggregates = calculate_nation_aggregates(nation, world)
    
    # Consumption
    food_consumed = calculate_food_consumption(aggregates["total_population"])
    energy_consumed = calculate_energy_consumption(aggregates["total_population"])
    materials_consumed = calculate_materials_consumption(
        aggregates["total_soldiers"],
        aggregates["total_aircraft"],
        aggregates["total_navy"]
    )
    
    # Net balance
    return {
        "food_balance": aggregates["total_food_production"] - food_consumed,
        "energy_balance": aggregates["total_energy_production"] - energy_consumed,
        "materials_balance": aggregates["total_materials_production"] - materials_consumed,
    }


# --- STARVATION & CRISIS ---

def calculate_starvation_casualties(food_deficit: float, total_population: int) -> int:
    """
    Calculate population loss due to food shortage.
    
    Args:
        food_deficit: Negative food balance (should be negative)
        total_population: Current population
        
    Returns:
        Number of people who die from starvation
    """
    if food_deficit >= 0:
        return 0
    
    # Starvation rate: 1% of population per unit of deficit
    deficit_ratio = abs(food_deficit) / max(1, total_population)
    starvation_rate = min(0.1, deficit_ratio * 0.01)  # Cap at 10% per turn
    
    return int(total_population * starvation_rate)


def calculate_energy_penalty(energy_deficit: float) -> float:
    """
    Calculate production penalty due to energy shortage.
    
    Args:
        energy_deficit: Negative energy balance
        
    Returns:
        Production multiplier (< 1.0 means reduced production)
    """
    if energy_deficit >= 0:
        return 1.0
    
    # Each unit of deficit reduces production by 1%, up to 50%
    penalty = 1.0 - min(0.5, abs(energy_deficit) * 0.01)
    return max(0.5, penalty)
