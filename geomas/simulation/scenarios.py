"""
Simulation Scenarios.

Handles mid-simulation trigger events and their effects on the WorldState.
"""

import random
from typing import Dict, Any, List
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

def trigger_resource_discovery(world: WorldState, context_manager: ContextManager, turn: int):
    """
    Executes the Resource Discovery Scenario.
    - Picks a random border province.
    - Drastically increases Energy (x10) and Materials (x5) production.
    - Logs a neutral, objective global event.
    """
    # Deterministic selection based on turn
    rng = random.Random(turn + 42)
    
    # 1. Identify all border provinces
    border_provinces = []
    for p_id, province in world.provinces.items():
        if province.owner_id is None:
            continue
            
        is_border = False
        for neighbor_id in province.neighbors:
            neighbor = world.provinces.get(neighbor_id)
            if neighbor and neighbor.owner_id and neighbor.owner_id != province.owner_id:
                is_border = True
                break
        
        if is_border:
            border_provinces.append(province)
            
    if not border_provinces:
        return ["⚠️ [SCENARIO FAILED] No border provinces found to trigger discovery."]
        
    # 2. Pick one
    target = rng.choice(border_provinces)
    owner = world.nations.get(target.owner_id)
    owner_name = owner.name if owner else "Unknown"
    
    # 3. Apply Multipliers
    target.energy_production = target.energy_production * 10.0
    target.materials_production = target.materials_production * 5.0
    
    # 4. Global Notification
    event_msg = (
        f"📜 [GLOBAL EVENT] Official report: A major mineral deposit has been identified "
        f"in province #{target.id} ({owner_name}). Environmental surveys confirm a "
        f"significant increase in local energy and materials production capacity."
    )
    
    # Add to raw world events
    world.global_events.append(f"T{turn}: {event_msg}")
    
    # Add to ContextManager structured events
    event = NotableEvent(
        turn=turn,
        event_type=EventType.GLOBAL_SCENARIO,
        actors=[target.owner_id],
        summary=event_msg,
        relevance_to=None  # Global
    )
    context_manager.global_events.append(event)
    
    return [f"💎 [SCENARIO DETECTED] Resource Discovery in province #{target.id} ({owner_name})! Production skyrocketed."]

def check_and_trigger_scenario(world: WorldState, context_manager: ContextManager, current_turn: int, scenario_trigger: Dict[str, Any]):
    """
    Router for executing a scenario if conditions match.
    """
    if scenario_trigger.get("turn") != current_turn:
        return []
        
    s_type = scenario_trigger.get("type", "").upper()
    
    if s_type == "PANDEMIA":
        return trigger_pandemic(world, context_manager, current_turn)
    elif s_type == "RESOURCE_DISCOVERY" or s_type == "SCOPERTA RISORSE":
        return trigger_resource_discovery(world, context_manager, current_turn)
        
    return []
