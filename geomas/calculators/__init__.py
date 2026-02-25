"""
Calculators Package — The Physics Engine.

Pure, stateless, deterministic functions for economic and physical
world calculations. All functions take state as input and return
calculated values without side effects. These embody the immutable
natural laws of the GeoMAS simulation world.

Design Principle:
    Calculators NEVER modify state. They compute a value from inputs.
    The caller (SimulationEngine, ActionEngine) decides what to do with
    the result. This separation ensures testability and predictability.

Modules:
    - consumption.py (97 lines): Resource consumption rates.
      Constants:
        FOOD_PER_PERSON = 1.0 (per turn)
        ENERGY_PER_PERSON = 0.5 (per turn)
        Military Maintenance (per unit per turn):
          SOLDIER: budget=0.2, materials=0.1, energy=0.0
          AIRCRAFT: budget=5.0, materials=2.0, energy=5.0
          NAVY: budget=4.0, materials=1.5, energy=3.0
      Functions: calculate_food_consumption(), calculate_energy_consumption(),
        calculate_materials_consumption(), calculate_budget_upkeep().
      Bureaucracy: cost multiplier = max(1.0, 1.0 + (provinces - 5) × 0.10).
        Each province beyond 5 adds 10% unit creation cost (empire overstretch).

    - production.py (68 lines): Output multipliers and tax collection.
      Unified Production Multiplier (multiplicative stacking):
        final_mult = workforce_mult × satisfaction_mult × energy_mult.
        If ANY pillar fails (revolution, no energy), production halts.
      Workforce Penalty: Linear decay below MIN_WORKFORCE_RATIO=0.5.
        If 50% of population is military, production = 0%.
      Satisfaction Elasticity: Via opinion handler's death spiral curve.
      Energy Penalty: Via crisis.calculate_energy_penalty().
      Tax Collection: Sum of province.tax_revenue for all owned provinces.

    - analytics.py (79 lines): Nation aggregates and power projection.
      calculate_nation_aggregates(): Sums population, soldiers, aircraft,
        navy (including territorial waters), food/energy/materials production
        across all owned provinces.
      Power Projection Formula:
        Score = Budget×0.001 + Food×0.01 + Energy×0.02 + Materials×0.03
              + Soldiers×0.1 + Aircraft×0.5 + Navy×0.3 + Nukes×50.0.
        Nukes dominate the formula by design (deterrence thesis).

    - crisis.py (58 lines): Resource shortage consequences.
      Starvation: casualties = population × min(0.1, |deficit|/pop × 0.01).
        Capped at 10% population loss per turn.
      Energy Penalty: mult = 1.0 - min(0.5, |deficit| × 0.01).
        Each unit of deficit = -1% production, floor at 50%.
      Resource Balance: net = production - consumption for food/energy/materials.

    - metrics.py (146 lines): Simulation metrics extraction for Analytics DB.
      Extracts per-nation per-turn: deception (overall/defense/foreign),
        coherence, budget, food, energy, materials, population, workers,
        satisfaction, civil_unrest, soldiers/aircraft/navy, power_projection,
        trade_volume, military_spending. Powers post-simulation Jupyter analysis.
"""

from geomas.calculators.consumption import (
    calculate_food_consumption,
    calculate_energy_consumption,
    calculate_materials_consumption,
    calculate_budget_upkeep,
    FOOD_PER_PERSON,
    ENERGY_PER_PERSON,
    MAINTENANCE_SOLDIER,
    MAINTENANCE_AIRCRAFT,
    MAINTENANCE_NAVY,
    SALARY_SOLDIER,
    SALARY_AIRCRAFT,
    SALARY_NAVY
)
from geomas.calculators.production import (
    calculate_production_penalty,
    calculate_nation_production_multiplier,
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
    "calculate_budget_upkeep",
    "FOOD_PER_PERSON",
    "ENERGY_PER_PERSON",
    "MAINTENANCE_SOLDIER",
    "MAINTENANCE_AIRCRAFT",
    "MAINTENANCE_NAVY",
    "SALARY_SOLDIER",
    "SALARY_AIRCRAFT",
    "SALARY_NAVY",
    "calculate_production_penalty",
    "calculate_nation_production_multiplier",
    "calculate_tax_collection",
    "MIN_WORKFORCE_RATIO",
    "calculate_nation_aggregates",
    "calculate_power_projection",
    "calculate_resource_balance",
    "calculate_starvation_casualties",
    "calculate_energy_penalty"
]
