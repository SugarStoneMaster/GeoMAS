"""
Consumption Calculators.

Defines the base consumption rates for population and military units.
"""

# --- CONSTANTS ---
FOOD_PER_PERSON = 1.0
ENERGY_PER_PERSON = 0.5

# --- MILITARY MAINTENANCE COSTS (per unit per turn) ---

# MATERIALS (Hardware/Supplies)
MAINTENANCE_SOLDIER = 0.1
MAINTENANCE_AIRCRAFT = 2.0
MAINTENANCE_NAVY = 1.5

# BUDGET (Salaries/Operational)
SALARY_SOLDIER = 0.2
SALARY_AIRCRAFT = 5.0
SALARY_NAVY = 4.0

# ENERGY (Fuel/Operations)
ENERGY_MAINTENANCE_SOLDIER = 0.0
ENERGY_MAINTENANCE_AIRCRAFT = 5.0
ENERGY_MAINTENANCE_NAVY = 3.0


def calculate_food_consumption(total_population: int) -> float:
    """Calculate food consumption for a nation."""
    return total_population * FOOD_PER_PERSON


def calculate_energy_consumption(
    total_population: int,
    total_aircraft: int = 0,
    total_navy: int = 0
) -> float:
    """Calculate total energy consumption (Population + Military)."""
    pop_consumption = total_population * ENERGY_PER_PERSON
    mil_consumption = (
        total_aircraft * ENERGY_MAINTENANCE_AIRCRAFT +
        total_navy * ENERGY_MAINTENANCE_NAVY
    )
    return pop_consumption + mil_consumption


def calculate_materials_consumption(
    total_soldiers: int,
    total_aircraft: int,
    total_navy: int
) -> float:
    """Calculate materials consumption for military maintenance."""
    return (
        total_soldiers * MAINTENANCE_SOLDIER +
        total_aircraft * MAINTENANCE_AIRCRAFT +
        total_navy * MAINTENANCE_NAVY
    )


def calculate_budget_upkeep(
    total_soldiers: int,
    total_aircraft: int,
    total_navy: int
) -> float:
    """Calculate budget consumption for military salaries/upkeep."""
    return (
        total_soldiers * SALARY_SOLDIER +
        total_aircraft * SALARY_AIRCRAFT +
        total_navy * SALARY_NAVY
    )
