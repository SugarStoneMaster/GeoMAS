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


def run_opinion_phase(
    world: WorldState,
    turn_logs: List[str],
    opinion_agents: dict,
    envelopes: list
) -> None:
    """
    Runs the Opinion phase after government actions.
    
    1. Calculate base satisfaction delta from events/actions
    2. Run Opinion agent to get multipliers
    3. Apply modifiers to satisfaction
    
    Args:
        world: Current world state
        turn_logs: Log list for this turn
        opinion_agents: Dict[nation_id, OpinionAgent]
        envelopes: Actions executed this turn
    """
    from geomas.agents.opinion import apply_opinion_modifiers
    
    for nation_id, nation in world.nations.items():
        # Skip if no opinion agent for this nation
        if nation_id not in opinion_agents:
            continue
        
        opinion_agent = opinion_agents[nation_id]
        
        # Gather context
        at_war = any(
            status == "WAR" 
            for status in world.relationship_matrix.get(nation_id, {}).values()
        )
        
        # Get recent events from global events
        events = [e for e in world.global_events[-20:] if nation_id in e or nation.name in e]
        
        # Get government actions from envelopes
        gov_actions = []
        for env in envelopes:
            if env.sender_id == nation_id:
                # Defense has a list of moves
                if env.defense_payload and env.defense_payload.moves:
                    for move in env.defense_payload.moves:
                        if hasattr(move, 'action_type') and move.action_type:
                            gov_actions.append(f"Defense: {move.action_type.value if hasattr(move.action_type, 'value') else move.action_type}")
                # Economy has single action_type
                if env.economic_payload and hasattr(env.economic_payload, 'action_type') and env.economic_payload.action_type:
                    gov_actions.append(f"Economy: {env.economic_payload.action_type.value if hasattr(env.economic_payload.action_type, 'value') else env.economic_payload.action_type}")
                # Foreign has single action_type
                if env.foreign_payload and hasattr(env.foreign_payload, 'action_type') and env.foreign_payload.action_type:
                    gov_actions.append(f"Foreign: {env.foreign_payload.action_type.value if hasattr(env.foreign_payload.action_type, 'value') else env.foreign_payload.action_type}")
        
        # Calculate base satisfaction delta from this turn's events
        base_delta = _calculate_base_satisfaction_delta(
            nation, world, events, gov_actions, at_war
        )
        
        # Get opinion reaction
        opinion_response = opinion_agent.react(
            events=events,
            government_actions=gov_actions,
            current_satisfaction=nation.public_satisfaction,
            at_war=at_war
        )
        
        # Apply modifiers
        final_delta = apply_opinion_modifiers(nation, base_delta, opinion_response)
        
        # Log
        if abs(final_delta) > 0.1:
            turn_logs.append(
                f"[OPINION] {nation_id}: Satisfaction {final_delta:+.1f} "
                f"(mult_inc={opinion_response.multiplier_increase:.1f}, "
                f"mult_dec={opinion_response.multiplier_decrease:.1f})"
            )


def _calculate_base_satisfaction_delta(
    nation,
    world: WorldState,
    events: List[str],
    gov_actions: List[str],
    at_war: bool
) -> float:
    """
    Calculate base satisfaction change from events and actions.
    
    This is the raw delta before opinion multipliers are applied.
    """
    delta = 0.0
    
    # War impact
    if at_war:
        delta -= 2.0  # War is stressful
    
    # Event-based impacts
    for event in events:
        event_upper = event.upper()
        
        # Positive events
        if "ALLIANCE_FORMED" in event_upper:
            delta += 3.0
        if "PEACE_SIGNED" in event_upper:
            delta += 5.0
        if "TRADE_DEAL" in event_upper:
            delta += 2.0
        if "TERRITORY_GAINED" in event_upper:
            delta += 4.0
        
        # Negative events
        if "WAR_DECLARED" in event_upper and nation.name in event:
            delta -= 5.0  # Someone declared war on us
        if "ALLIANCE_BROKEN" in event_upper:
            delta -= 3.0
        if "TERRITORY_LOST" in event_upper:
            delta -= 6.0
        if "NUCLEAR_STRIKE" in event_upper:
            delta -= 10.0  # Catastrophic
    
    # Action-based impacts
    for action in gov_actions:
        action_upper = action.upper()
        
        if "INVEST_WELFARE" in action_upper:
            delta += 3.0  # Government is helping
        if "RAISE_WAR_TAX" in action_upper or "WAR_TAX" in action_upper:
            delta -= 5.0  # Hurts population
    
    # Resource shortages
    if nation.total_food < 50:
        delta -= 3.0
    if nation.total_energy < 50:
        delta -= 2.0
    
    return delta

