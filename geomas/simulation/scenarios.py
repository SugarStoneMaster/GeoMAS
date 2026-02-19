"""
Simulation Scenarios.

Handles mid-simulation trigger events and their effects on the WorldState.
"""

from typing import Dict, Any
from geomas.schemas.world import WorldState
from geomas.agents.context.events.context_manager import ContextManager
from geomas.agents.context.events.schemas import NotableEvent, EventType

def trigger_pandemic(world: WorldState, context_manager: ContextManager, turn: int):
    """
    Executes the Pandemic Scenario.
    - Halves production yields across all provinces.
    - Kills 10% of the population and workforce.
    - Increases public unrest sensitivity to negative events.
    - Triggers a global critical alert.
    """
    affected_provinces = 0
    total_deaths = 0

    # 1. Structural Damage to Provinces
    for province_id, province in world.provinces.items():
        if province.population > 0:
            # Halve production capacity
            province.food_production = province.food_production * 0.5
            province.energy_production = province.energy_production * 0.5
            province.materials_production = province.materials_production * 0.5
            
            # Immediate mortality rate
            deaths = int(province.population * 0.10)
            worker_deaths = int(province.workers * 0.10)
            
            province.population = max(0, province.population - deaths)
            province.workers = max(0, province.workers - worker_deaths)
            province.tax_revenue = province.population * 1.0
            
            affected_provinces += 1
            total_deaths += deaths

    # 2. Nation-level Impacts (Unrest & Panic)
    for nation_id, nation in world.nations.items():
        # Immediate panic drop in public satisfaction
        nation.public_satisfaction = max(0.0, nation.public_satisfaction - 20.0)

    # 3. Global Notification
    if affected_provinces > 0:
        event_msg = f"🌍 [GLOBAL CRISIS] A deadly Pandemic has swept the globe! Production is halved and millions have died ({total_deaths:,})."
        
        # Add to raw world events
        world.global_events.append(f"T{turn}: {event_msg}")
        
        # Add to ContextManager structured events
        event = NotableEvent(
            turn=turn,
            event_type=EventType.GLOBAL_SCENARIO,
            actors=[],
            summary=event_msg,
            relevance_to=None  # Global
        )
        context_manager.global_events.append(event)
        
        return [f"🦠 [SCENARIO DETECTED] Pandemic Triggered! {total_deaths:,} dead. Global yields have been permanently halved."]
    return []

def check_and_trigger_scenario(world: WorldState, context_manager: ContextManager, current_turn: int, scenario_trigger: Dict[str, Any]):
    """
    Router for executing a scenario if conditions match.
    """
    if scenario_trigger.get("turn") != current_turn:
        return []
        
    s_type = scenario_trigger.get("type", "").upper()
    
    if s_type == "PANDEMIA":
        return trigger_pandemic(world, context_manager, current_turn)
        
    return []
