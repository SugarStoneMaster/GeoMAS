"""
Simulation Phases.

Logic for specific phases of the turn (Economy, Crisis, etc.).
"""

from typing import List
from geomas.schemas.world import WorldState
from geomas import calculators as economy


def run_upkeep_phase(world: WorldState, turn_logs: List[str]):
    """
    Updates economic state for all nations at the start of each turn.
    
    1. Calculate aggregates from provinces
    2. Collect taxes
    3. Calculate production
    4. Calculate consumption
    5. Apply resource changes
    6. Handle deficits (starvation, energy penalties)
    7. Update power projection
    """
    for nation_id, nation in world.nations.items():
        # 1. Calculate aggregates
        aggregates = economy.calculate_nation_aggregates(nation, world)
        nation.total_population = aggregates["total_population"]
        nation.total_workers = aggregates["total_workers"]
        nation.total_soldiers = aggregates["total_soldiers"]
        nation.total_aircraft = aggregates["total_aircraft"]
        nation.total_navy = aggregates["total_navy"]
        
        # 2. Collect taxes (adds to budget)
        tax_collected = economy.calculate_tax_collection(nation, world)
        nation.total_budget += tax_collected
        
        # 3. Add production to resource stockpiles
        nation.total_food += aggregates["total_food_production"]
        nation.total_energy += aggregates["total_energy_production"]
        nation.total_materials += aggregates["total_materials_production"]
        
        # 4. Calculate consumption
        food_consumed = economy.calculate_food_consumption(nation.total_population)
        energy_consumed = economy.calculate_energy_consumption(nation.total_population)
        materials_consumed = economy.calculate_materials_consumption(
            nation.total_soldiers,
            nation.total_aircraft,
            nation.total_navy
        )
        
        # 5. Apply consumption (subtract from stockpiles)
        nation.total_food -= food_consumed
        nation.total_energy -= energy_consumed
        nation.total_materials -= materials_consumed
        
        # 6. Handle deficits
        if nation.total_food < 0:
            casualties = economy.calculate_starvation_casualties(
                nation.total_food,
                nation.total_population
            )
            if casualties > 0:
                apply_population_loss(world, nation_id, casualties)
                turn_logs.append(
                    f"[CRISIS] {nation_id}: {casualties} died from starvation!"
                )
            nation.total_food = 0  # Can't go negative
        
        if nation.total_energy < 0:
            penalty = economy.calculate_energy_penalty(nation.total_energy)
            turn_logs.append(
                f"[CRISIS] {nation_id}: Energy shortage! Production penalty: {1 - penalty:.0%}"
            )
            # Apply penalty to next turn's production (stored in provinces)
            apply_production_penalty(world, nation_id, penalty)
            nation.total_energy = 0
        
        if nation.total_materials < 0:
            turn_logs.append(
                f"[CRISIS] {nation_id}: Materials shortage! Military maintenance failing."
            )
            nation.total_materials = 0
        
        # 7. Update power projection
        nation.power_projection = economy.calculate_power_projection(nation)
        
        # Log economy summary
        turn_logs.append(
            f"[ECONOMY] {nation_id}: Budget={nation.total_budget:.0f}, "
            f"Food={nation.total_food:.0f}, Energy={nation.total_energy:.0f}, "
            f"Materials={nation.total_materials:.0f}, Power={nation.power_projection:.1f}"
        )


def apply_population_loss(world: WorldState, nation_id: str, casualties: int):
    """Distributes population loss across provinces proportionally."""
    nation = world.nations[nation_id]
    total_pop = nation.total_population
    
    if total_pop == 0:
        return
    
    for p_id in nation.province_ids:
        province = world.provinces.get(p_id)
        if province and province.population > 0:
            # Proportional loss
            province_loss = int(casualties * (province.population / total_pop))
            province.population = max(0, province.population - province_loss)
            # Workers decrease proportionally
            province.workers = max(0, province.workers - province_loss)
            # Update tax revenue
            province.tax_revenue = province.population * 0.1


def apply_production_penalty(world: WorldState, nation_id: str, penalty_multiplier: float):
    """Applies production penalty to all provinces of a nation."""
    nation = world.nations[nation_id]
    
    for p_id in nation.province_ids:
        province = world.provinces.get(p_id)
        if province:
            province.food_production *= penalty_multiplier
            province.energy_production *= penalty_multiplier
            province.materials_production *= penalty_multiplier
