"""
Production Calculators.

Handles production penalties and tax calculations.
"""

from typing import TYPE_CHECKING
from geomas.schemas.world import WorldState, NationState

# Production penalty thresholds
MIN_WORKFORCE_RATIO = 0.5  # Below this, production suffers


def calculate_production_penalty(workers: int, population: int) -> float:
    """
    Calculate production penalty based on workforce availability.
    When too many people are in the military, production suffers.
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
    """Calculate total tax revenue from all provinces."""
    total_tax = 0.0
    for p_id in nation.province_ids:
        province = world.provinces.get(p_id)
        if province:
            total_tax += province.tax_revenue
    return total_tax
