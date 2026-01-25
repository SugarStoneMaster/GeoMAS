"""
Calculators Package.

Pure, stateless, deterministic functions for economic and physical
world calculations. All functions take state as input and return
calculated values without side effects.

Modules:
    - consumption: Resource consumption rates per unit/population
    - production: Production penalties and tax collection
    - analytics: Nation aggregates and power projection scoring
    - crisis: Starvation casualties and energy shortage effects

Design Principle:
    These functions embody the "physics" of the simulation world.
    They are separated from the simulation loop to enable:
    - Unit testing in isolation
    - Reuse across different contexts (trade evaluation, AI reasoning)
    - Clear separation between calculation and state mutation
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
