"""
Analytics Calculators.

Calculates aggregated stats and power projection scores.
"""

from typing import Dict
from geomas.schemas.world import WorldState, NationState


def calculate_nation_aggregates(nation: NationState, world: WorldState) -> Dict[str, float]:
    """Calculate all aggregate values for a nation from its provinces."""
    total_pop = 0
    total_workers = 0
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
            total_workers += prov.workers
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
        "total_workers": total_workers,
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
