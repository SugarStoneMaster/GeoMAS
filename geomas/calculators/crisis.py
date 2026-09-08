"""
Crisis Calculators.

Handles resource balances, starvation, and penalties.
"""

from typing import Dict
from geomas.schemas.world import WorldState, NationState
from geomas.calculators.analytics import calculate_nation_aggregates
from geomas.calculators.consumption import (
    calculate_food_consumption,
    calculate_energy_consumption,
    calculate_materials_consumption
)


def calculate_resource_balance(nation: NationState, world: WorldState) -> Dict[str, float]:
    """Calculate net resource balance for a nation (production - consumption)."""
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


def calculate_starvation_casualties(food_deficit: float, total_population: int) -> int:
    """Calculate population loss due to food shortage."""
    if food_deficit >= 0:
        return 0
    
    # Starvation rate: 1% of population per unit of deficit
    deficit_ratio = abs(food_deficit) / max(1, total_population)
    starvation_rate = min(0.1, deficit_ratio * 0.01)  # Cap at 10% per turn
    
    return int(total_population * starvation_rate)


def calculate_energy_penalty(energy_deficit: float) -> float:
    """Calculate production penalty due to energy shortage."""
    if energy_deficit >= 0:
        return 1.0
    
    # Each unit of deficit reduces production by 1%, up to 50%
    penalty = 1.0 - min(0.5, abs(energy_deficit) * 0.01)
    return max(0.5, penalty)
