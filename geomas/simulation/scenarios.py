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

def trigger_separatist_insurrection(world: WorldState, context_manager: ContextManager, turn: int) -> Dict[str, Any]:
    """
    Executes the Separatist Insurrection Scenario.
    - Finds the nation with the lowest public satisfaction.
    - Steals 1-3 provinces to form a new rebel state.
    - Transfers units and recalibrates resource statistics.
    - Updates Trust & Relationship matrices to WAR state.
    """
    import random
    from geomas.schemas.world import NationState, RelationshipState
    from geomas.agents.schemas.protocol import GovernmentType
    from geomas.agents.schemas import GlobalStrategy
    from geomas.calculators.analytics import calculate_nation_aggregates, calculate_power_projection
    
    rng = random.Random(turn + 142)
    
    # 1. Find Motherland (lowest satisfaction)
    nations_with_provinces = [n for n in world.nations.values() if len(n.province_ids) > 1]
    if not nations_with_provinces:
        return {"logs": ["⚠️ [SCENARIO FAILED] No nation found with enough provinces to rebel."]}
        
    motherland = min(nations_with_provinces, key=lambda n: n.public_satisfaction)
    
    # 2. Pick target provinces using BFS for adjacency
    all_mother_provinces = set(motherland.province_ids)
    
    # NEW LOGIC: Steal 25% of provinces (minimum 1)
    target_num = max(1, int(len(all_mother_provinces) * 0.25))
    num_to_steal = min(len(all_mother_provinces) - 1, target_num)
    
    # Start from a random province
    start_prov_id = rng.choice(list(all_mother_provinces))
    stolen_ids = {start_prov_id}
    queue = [start_prov_id]
    
    while queue and len(stolen_ids) < num_to_steal:
        curr_id = queue.pop(0)
        curr_prov = world.provinces[curr_id]
        neighbors = [n_id for n_id in curr_prov.neighbors if n_id in all_mother_provinces and n_id not in stolen_ids]
        rng.shuffle(neighbors)
        for n_id in neighbors:
            if len(stolen_ids) < num_to_steal:
                stolen_ids.add(n_id)
                queue.append(n_id)
                
    if not stolen_ids:
        return {"logs": ["⚠️ [SCENARIO FAILED] Rebellion failed to secure adjacent provinces."]}
        
    # 3. Create Rebel State
    # A distinct color
    colors = ['#FF4136', '#FF851B', '#FFDC00', '#2ECC40', '#0074D9', '#B10DC9', '#E0A899', '#AAAAAA']
    color = rng.choice(colors)
    
    rebel_id = f"{motherland.id}_FREE"
    rebel_name = f"Free State of {motherland.name}"
    
    rebel_nation = NationState(
        id=rebel_id,
        name=rebel_name,
        color=color,
        province_ids=list(stolen_ids),
        total_budget=0, total_food=0, total_energy=0, total_materials=0,
        total_population=0, power_projection=0.0,
        public_satisfaction=80.0, # High early enthusiasm
        cultural_traits=motherland.cultural_traits.copy()
    )
    
    # Transfer provinces
    for p_id in stolen_ids:
        motherland.province_ids.remove(p_id)
        world.provinces[p_id].owner_id = rebel_id
        # Note: soldiers, aircraft, and navy are native attributes of the ProvinceState.
        # By changing the owner_id, they automatically belong to the new nation.
        # Guest troops from allies are cleared to reflect the chaos of rebellion.
        world.provinces[p_id].guest_troops = {}
    
    # Recalculate Aggregates
    for target_nation in [motherland, rebel_nation]:
        aggr = calculate_nation_aggregates(target_nation, world)
        target_nation.total_population = aggr["total_population"]
        target_nation.total_soldiers = aggr["total_soldiers"]
        target_nation.total_aircraft = aggr["total_aircraft"]
        target_nation.total_navy = aggr["total_navy"]
        target_nation.power_projection = calculate_power_projection(target_nation)
        
    # Give rebels a small stash stolen from motherland
    stolen_share = len(stolen_ids) / (len(stolen_ids) + len(motherland.province_ids))
    rebel_nation.total_budget = motherland.total_budget * stolen_share
    rebel_nation.total_food = motherland.total_food * stolen_share
    rebel_nation.total_energy = motherland.total_energy * stolen_share
    rebel_nation.total_materials = motherland.total_materials * stolen_share
    
    motherland.total_budget *= (1 - stolen_share)
    motherland.total_food *= (1 - stolen_share)
    motherland.total_energy *= (1 - stolen_share)
    motherland.total_materials *= (1 - stolen_share)
    
    world.nations[rebel_id] = rebel_nation
    
    # 4. Determine New Attributes
    # Opposing Government
    gov_map = {
        GovernmentType.DEMOCRACY.value: GovernmentType.AUTHORITARIAN,
        GovernmentType.AUTHORITARIAN.value: GovernmentType.DEMOCRACY,
        GovernmentType.THEOCRACY.value: GovernmentType.DEMOCRACY,
    }
    mother_gov_str = getattr(motherland, "government_type", GovernmentType.DEMOCRACY.value)
    rebel_gov = gov_map.get(mother_gov_str, GovernmentType.AUTHORITARIAN)
    rebel_nation.government_type = rebel_gov.value
    
    # Strategy
    rebel_strategy = GlobalStrategy.SCORCHED_EARTH if rng.random() > 0.5 else GlobalStrategy.ARMED_ISOLATIONISM
    
    # 5. Trust and Relationships
    # Trust is normalized to a 0-100 scale.
    world.trust_matrix[rebel_id] = {}
    world.relationship_matrix[rebel_id] = {}
    
    for other_id, other_nation in world.nations.items():
        if other_id == rebel_id:
            continue
            
        if other_id == motherland.id:
            # Active civil war: absolute minimum trust (0.0)
            world.trust_matrix[rebel_id][other_id] = 0.0
            world.trust_matrix[other_id][rebel_id] = 0.0
            world.relationship_matrix[rebel_id][other_id] = RelationshipState.WAR
            world.relationship_matrix[other_id][rebel_id] = RelationshipState.WAR
        else:
            # Baseline neutral trust: 50.0 for both directions
            base_trust = 50.0
            
            # --- Direction 1: Observer -> Rebel ---
            # How much the existing nation trusts the new rebel state
            other_gov_str = getattr(other_nation, "government_type", GovernmentType.DEMOCRACY.value)
            gov_affinity_to_rebel = 15.0 if other_gov_str == rebel_gov.value else -15.0
            
            trust_in_mother = world.trust_matrix.get(other_id, {}).get(motherland.id, 50.0)
            proxy_to_rebel = 0.0
            if trust_in_mother < 40.0:
                proxy_to_rebel = 20.0  # Enemy of my enemy is my friend
            elif trust_in_mother > 60.0:
                proxy_to_rebel = -20.0 # Friend of my enemy is my enemy
                
            final_trust_to_rebel = min(100.0, max(0.0, base_trust + gov_affinity_to_rebel + proxy_to_rebel))
            
            # --- Direction 2: Rebel -> Observer ---
            # How much the new rebel state trusts the existing nation
            # Rebels trust those who share their ideology
            gov_affinity_from_rebel = 15.0 if rebel_gov.value == other_gov_str else -15.0
            
            # Rebels trust those who are hostile to their Motherland (their oppressor)
            proxy_from_rebel = 0.0
            if trust_in_mother < 40.0:
                proxy_from_rebel = 20.0  # They hate our oppressor, we trust them
            elif trust_in_mother > 60.0:
                proxy_from_rebel = -20.0 # They are allies of our oppressor, we distrust them
                
            # Rebels might be slightly more paranoid overall (baseline - 5.0) due to their illegitimacy
            paranoid_baseline = base_trust - 5.0
            
            final_trust_from_rebel = min(100.0, max(0.0, paranoid_baseline + gov_affinity_from_rebel + proxy_from_rebel))
            
            # Apply to matrix
            world.trust_matrix[other_id][rebel_id] = float(final_trust_to_rebel)
            world.trust_matrix[rebel_id][other_id] = float(final_trust_from_rebel)
            
            world.relationship_matrix[rebel_id][other_id] = RelationshipState.PEACE
            world.relationship_matrix[other_id][rebel_id] = RelationshipState.PEACE

    # 6. Global Event
    event_msg = f"🔥 [CIVIL WAR] Separatists in {motherland.name} have violently seceded, forming the {rebel_name}! The newly independent state has seized {len(stolen_ids)} provinces and local military assets."
    world.global_events.append(f"T{turn}: {event_msg}")
    
    event = NotableEvent(
        turn=turn,
        event_type=EventType.GLOBAL_SCENARIO,
        actors=[motherland.id, rebel_id],
        summary=event_msg,
        relevance_to=None  # Global
    )
    context_manager.global_events.append(event)
    
    logs = [f"🔥 [SCENARIO DETECTED] Insurrection triggered in {motherland.name}. {rebel_name} formed."]
    
    # Return instructions for the Engine to instantiate the new agent
    return {
        "logs": logs,
        "new_nation": {
            "id": rebel_id,
            "strategy": rebel_strategy,
            "government_type": rebel_gov
        }
    }

def check_and_trigger_scenario(world: WorldState, context_manager: ContextManager, current_turn: int, scenario_trigger: Dict[str, Any]) -> Dict[str, Any]:
    """
    Router for executing a scenario if conditions match.
    Returns a dictionary which can contain 'logs' and other scenario-specific commands for the engine.
    """
    if scenario_trigger.get("turn") != current_turn:
        return {"logs": []}
        
    s_type = scenario_trigger.get("type", "").upper()
    
    if s_type == "PANDEMIA":
        logs = trigger_pandemic(world, context_manager, current_turn)
        return {"logs": logs}
    elif s_type == "RESOURCE_DISCOVERY" or s_type == "SCOPERTA RISORSE":
        logs = trigger_resource_discovery(world, context_manager, current_turn)
        return {"logs": logs}
    elif s_type == "INSURREZIONE" or s_type == "SEPARATIST_INSURRECTION":
        return trigger_separatist_insurrection(world, context_manager, current_turn)
        
    return {"logs": []}
