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
    if population <= 0:
        return 0.0
    
    workforce_ratio = workers / population
    
    if workforce_ratio >= MIN_WORKFORCE_RATIO:
        return 1.0
    else:
        # Linear penalty below threshold: 0.5 ratio = 1.0 mult, 0.0 ratio = 0.0 mult
        return max(0.0, workforce_ratio / MIN_WORKFORCE_RATIO)


def calculate_nation_production_multiplier(
    nation: NationState,
    energy_deficit: float = 0.0
) -> float:
    """
    Unified production multiplier for a nation.
    Combines:
    1. Workforce availability (military mobilization)
    2. Public Satisfaction (Death Spiral elasticity)
    3. Energy shortages
    
    Returns a float (typically 1.0 to 0.0).
    """
    # 1. Workforce Penalty
    workforce_mult = calculate_production_penalty(nation.total_workers, nation.total_population)
    
    # 2. Satisfaction Elasticity
    from geomas.actions.opinion.handler import get_production_multiplier
    satisfaction_mult = get_production_multiplier(nation)
    
    # 3. Energy Penalty
    from geomas.calculators.crisis import calculate_energy_penalty
    energy_mult = calculate_energy_penalty(energy_deficit)
    
    # Multiplicative stacking (not additive) ensures that if any one pillar 
    # fails completely (e.g. Revolution or 0 Energy), production stops.
    return workforce_mult * satisfaction_mult * energy_mult


def calculate_tax_collection(nation: NationState, world: WorldState) -> float:
    """Calculate total tax revenue from all provinces."""
    total_tax = 0.0
    for p_id in nation.province_ids:
        province = world.provinces.get(p_id)
        if province:
            total_tax += province.tax_revenue
    return total_tax
