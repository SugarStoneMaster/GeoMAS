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
    3. Calculate unified production multiplier (Elasticity + Energy + Workforce)
    4. Add production to stockpiles (Non-destructive)
    5. Calculate and apply consumption (Population + Military Maintenance)
    6. Handle deficits (starvation)
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
        
        # 3. Calculate unified production multiplier
        # Check current energy balance to see if there's a deficit
        # (Deficit from PREVIOUS turn's consumption)
        energy_deficit = min(0.0, nation.total_energy)
        prod_multiplier = economy.calculate_nation_production_multiplier(
            nation, 
            energy_deficit=energy_deficit
        )
        
        if prod_multiplier < 1.0:
            turn_logs.append(
                f"[ECONOMY] {nation_id}: Production efficiency at {prod_multiplier*100:.1f}%"
            )
        
        # 4. Add production to resource stockpiles (Applying the multiplier on-the-fly)
        nation.total_food += aggregates["total_food_production"] * prod_multiplier
        nation.total_energy += aggregates["total_energy_production"] * prod_multiplier
        nation.total_materials += aggregates["total_materials_production"] * prod_multiplier
        
        # 5. Calculate consumption & Upkeep
        food_consumed = economy.calculate_food_consumption(nation.total_population)
        energy_consumed = economy.calculate_energy_consumption(
            nation.total_population,
            total_aircraft=nation.total_aircraft,
            total_navy=nation.total_navy
        )
        materials_consumed = economy.calculate_materials_consumption(
            nation.total_soldiers,
            nation.total_aircraft,
            nation.total_navy
        )
        budget_consumed = economy.calculate_budget_upkeep(
            nation.total_soldiers,
            nation.total_aircraft,
            nation.total_navy
        )
        
        # Apply consumption
        nation.total_food -= food_consumed
        nation.total_energy -= energy_consumed
        nation.total_materials -= materials_consumed
        nation.total_budget -= budget_consumed
        
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
            nation.total_food = 0 
        
        # Energy and Materials can be negative at this point (representing missing services/upkeep)
        # but we clamp them to zero for the next cycle after logging shortages
        if nation.total_energy < 0:
            turn_logs.append(f"[CRISIS] {nation_id}: Energy shortage! Industry will suffer next turn.")
            nation.total_energy = 0
            
        if nation.total_materials < 0:
            turn_logs.append(f"[CRISIS] {nation_id}: Materials shortage! Military maintenance failing.")
            nation.total_materials = 0

        if nation.total_budget < 0:
             turn_logs.append(f"[CRISIS] {nation_id}: Bankruptcy! Military salaries unpaid.")
             nation.total_budget = 0
        
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
            province.tax_revenue = province.population * 1.0  # Aligned with TAX_RATE


def run_opinion_phase(
    world: WorldState,
    turn_logs: List[str],
    opinion_agents: dict,
    envelopes: list,
    turn: int = 0
) -> None:
    """
    Runs the Opinion phase after government actions.
    
    1. Runs Opinion agent to update multipliers (based on current state)
    2. Calculates satisfaction delta using centralized logic
    3. Triggers events (Strikes, Unrest)
    """
    from geomas.actions.opinion.handler import calculate_turn_satisfaction_delta, check_triggers
    
    for nation_id, nation in world.nations.items():
        if nation_id not in opinion_agents:
            continue
        
        opinion_agent = opinion_agents[nation_id]
        
        # --- 1. Agent Perception & Reaction ---
        at_war = any(
            status == "WAR" 
            for status in world.relationship_matrix.get(nation_id, {}).values()
        )
        events = [e for e in world.global_events[-20:] if nation_id in e or nation.name in e]
        
        gov_actions = []
        for env in envelopes:
            if env.sender_id == nation_id:
                if env.defense_payload and env.defense_payload.moves:
                    for move in env.defense_payload.moves:
                        if hasattr(move, 'action_type') and move.action_type:
                            gov_actions.append(f"Defense: {move.action_type.value if hasattr(move.action_type, 'value') else move.action_type}")
                if env.economic_payload and hasattr(env.economic_payload, 'action_type') and env.economic_payload.action_type:
                    action_str = f"Economy: {env.economic_payload.action_type.value if hasattr(env.economic_payload.action_type, 'value') else env.economic_payload.action_type}"
                    if hasattr(env.economic_payload, 'message') and env.economic_payload.message:
                        action_str += f" (Message to citizens: '{env.economic_payload.message}')"
                    gov_actions.append(action_str)
                if env.foreign_payload and hasattr(env.foreign_payload, 'action_type') and env.foreign_payload.action_type:
                    gov_actions.append(f"Foreign: {env.foreign_payload.action_type.value if hasattr(env.foreign_payload.action_type, 'value') else env.foreign_payload.action_type}")
        
        # Opinion agent reacts to provide NEW multipliers
        opinion_response = opinion_agent.react(
            events=events,
            government_actions=gov_actions,
            current_satisfaction=nation.public_satisfaction,
            at_war=at_war,
            turn=turn
        )
        
        # Update nation multipliers
        nation.population_multiplier_increase = opinion_response.multiplier_increase
        nation.population_multiplier_decrease = opinion_response.multiplier_decrease
        
        # --- 2. Satisfaction Delta (Centralized) ---
        old_sat = nation.public_satisfaction
        delta = calculate_turn_satisfaction_delta(
            nation, world, events, gov_actions, at_war
        )
        
        # Apply to nation
        new_sat = max(0.0, min(100.0, old_sat + delta))
        nation.public_satisfaction = new_sat
        
        if abs(delta) > 0.1:
            turn_logs.append(
                f"[OPINION] {nation_id}: Satisfaction {old_sat:.0f} -> {new_sat:.0f} (delta {delta:+.1f})"
            )
            
        # --- 3. Triggers (Strikes, Unrest) ---
        # Note: we use a mock engine interface or a simpler direct call
        class MockEngine:
            def __init__(self, world, logs):
                self.world = world
                self.logs = logs
        
        check_triggers(MockEngine(world, turn_logs), nation_id)

