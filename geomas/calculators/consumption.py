"""
Consumption Calculators.

Defines the base consumption rates for population and military units.
"""

# --- CONSTANTS ---
FOOD_PER_PERSON = 1.0
ENERGY_PER_PERSON = 0.5

# --- MILITARY MAINTENANCE COSTS (per unit per turn) ---
# Centralized source of truth for all unit maintenance
MAINTENANCE_DATA = {
    "SOLDIER": {
        "budget": 0.2,
        "materials": 0.05,
        "energy": 0.0,
    },
    "AIRCRAFT": {
        "budget": 5.0,
        "materials": 1.0,
        "energy": 5.0,
    },
    "NAVY": {
        "budget": 4.0,
        "materials": 0.75,
        "energy": 3.0,
    }
}

# Legacy flat constants (derived from dictionary for compatibility)
MAINTENANCE_SOLDIER = MAINTENANCE_DATA["SOLDIER"]["materials"]
MAINTENANCE_AIRCRAFT = MAINTENANCE_DATA["AIRCRAFT"]["materials"]
MAINTENANCE_NAVY = MAINTENANCE_DATA["NAVY"]["materials"]

SALARY_SOLDIER = MAINTENANCE_DATA["SOLDIER"]["budget"]
SALARY_AIRCRAFT = MAINTENANCE_DATA["AIRCRAFT"]["budget"]
SALARY_NAVY = MAINTENANCE_DATA["NAVY"]["budget"]

ENERGY_MAINTENANCE_SOLDIER = MAINTENANCE_DATA["SOLDIER"]["energy"]
ENERGY_MAINTENANCE_AIRCRAFT = MAINTENANCE_DATA["AIRCRAFT"]["energy"]
ENERGY_MAINTENANCE_NAVY = MAINTENANCE_DATA["NAVY"]["energy"]


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


def calculate_bureaucracy_multiplier(nation: 'NationState') -> float:
    """
    Calculate the bureaucratic cost multiplier based on empire size.
    Base size is 5 provinces. Each additional province adds 10% cost to unit creation.
    """
    num_provinces = len(nation.province_ids)
    return max(1.0, 1.0 + (num_provinces - 5) * 0.10)
