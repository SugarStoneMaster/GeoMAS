"""
Consumption Calculators.

Defines the base consumption rates for population and military units.
"""

# --- CONSTANTS ---
FOOD_PER_PERSON = 1.0
ENERGY_PER_PERSON = 0.5

# Military maintenance costs per unit per turn
MAINTENANCE_SOLDIER = 0.1  # materials
MAINTENANCE_AIRCRAFT = 2.0 # materials
MAINTENANCE_NAVY = 1.5     # materials


def calculate_food_consumption(total_population: int) -> float:
    """Calculate food consumption for a nation."""
    return total_population * FOOD_PER_PERSON


def calculate_energy_consumption(total_population: int) -> float:
    """Calculate energy consumption for a nation."""
    return total_population * ENERGY_PER_PERSON


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
