"""
Calculators Package.

Functional logic for economic and physical world calculations.
- consumption: Resource consumption rates
- production: Production logic and penalties
- analytics: Aggregation and scoring
- crisis: Starvation and shortage effects
"""

from geomas.calculators.consumption import (
    calculate_food_consumption,
    calculate_energy_consumption,
    calculate_materials_consumption,
    FOOD_PER_PERSON,
    ENERGY_PER_PERSON,
    MAINTENANCE_SOLDIER,
    MAINTENANCE_AIRCRAFT,
    MAINTENANCE_NAVY
)
from geomas.calculators.production import (
    calculate_production_penalty,
    calculate_tax_collection,
    MIN_WORKFORCE_RATIO
)
from geomas.calculators.analytics import (
    calculate_nation_aggregates,
    calculate_power_projection
)
from geomas.calculators.crisis import (
    calculate_resource_balance,
    calculate_starvation_casualties,
    calculate_energy_penalty
)

__all__ = [
    "calculate_food_consumption",
    "calculate_energy_consumption",
    "calculate_materials_consumption",
    "FOOD_PER_PERSON",
    "ENERGY_PER_PERSON",
    "MAINTENANCE_SOLDIER",
    "MAINTENANCE_AIRCRAFT",
    "MAINTENANCE_NAVY",
    "calculate_production_penalty",
    "calculate_tax_collection",
    "MIN_WORKFORCE_RATIO",
    "calculate_nation_aggregates",
    "calculate_power_projection",
    "calculate_resource_balance",
    "calculate_starvation_casualties",
    "calculate_energy_penalty"
]
