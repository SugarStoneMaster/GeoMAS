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

    Improvements over flat-rate version:
    - Mortality scales with province population density (dense areas hit harder).
    - Military units suffer attrition (soldiers get sick too).
    - Satisfaction penalty scales inversely with food stockpiles (rich nations absorb shock better).
    - Global trust drops slightly (border closures and resource competition).
    """
    affected_provinces = 0
    total_deaths = 0

    # Pre-compute average population density for density-scaling mortality
    inhabited = [p for p in world.provinces.values() if p.population > 0]
    avg_population = (sum(p.population for p in inhabited) / len(inhabited)) if inhabited else 1.0

    # 1. Province-level structural damage
    for province_id, province in world.provinces.items():
        if province.population <= 0:
            continue

        # Density ratio: provinces denser than average suffer more deaths (max 25%, min 5%)
        density_ratio = province.population / avg_population
        death_rate = min(0.25, max(0.05, 0.10 * density_ratio))

        deaths = int(province.population * death_rate)
        worker_deaths = int(province.workers * death_rate)

        province.population = max(0, province.population - deaths)
        province.workers = max(0, province.workers - worker_deaths)
        province.tax_revenue = province.population * 1.0

        # Production halved (disease disrupts supply chains and workforce)
        province.food_production *= 0.5
        province.energy_production *= 0.5
        province.materials_production *= 0.5

        # Military attrition: soldiers and aircraft crews fall ill (5% losses)
        soldier_losses = int(province.soldiers * 0.05)
        aircraft_losses = int(province.aircraft * 0.05)
        province.soldiers = max(0, province.soldiers - soldier_losses)
        province.aircraft = max(0, province.aircraft - aircraft_losses)

        affected_provinces += 1
        total_deaths += deaths

    # 2. Nation-level impacts — satisfaction scales with food buffer
    avg_food = (
        sum(n.total_food for n in world.nations.values()) / len(world.nations)
        if world.nations else 1.0
    )

    for nation_id, nation in world.nations.items():
        # Recalibrate total soldiers/aircraft to match province losses
        from geomas.calculators.analytics import calculate_nation_aggregates
        aggr = calculate_nation_aggregates(nation, world)
        nation.total_soldiers = aggr["total_soldiers"]
        nation.total_aircraft = aggr["total_aircraft"]

        # Satisfaction penalty: food-rich nations weather the crisis better
        food_ratio = nation.total_food / avg_food if avg_food > 0 else 1.0
        # Penalty: -30 for food-poor (<0.5x avg), -15 for food-rich (>1.5x avg), -20 baseline
        if food_ratio < 0.5:
            sat_penalty = 30.0
        elif food_ratio > 1.5:
            sat_penalty = 15.0
        else:
            sat_penalty = 20.0

        nation.public_satisfaction = max(0.0, nation.public_satisfaction - sat_penalty)

    # 3. Global trust penalty (border closures, resource competition, blame)
    for nation_id in world.nations:
        for other_id in world.nations:
            if nation_id == other_id:
                continue
            current = world.trust_matrix.get(nation_id, {}).get(other_id, 50.0)
            world.trust_matrix.setdefault(nation_id, {})[other_id] = max(0.0, current - 10.0)

    # 4. Global notification
    if affected_provinces > 0:
        event_msg = (
            f"🌍 [GLOBAL CRISIS] A deadly Pandemic has swept the globe! "
            f"Production is halved, {total_deaths:,} have died, armies are depleted, "
            f"and international trust has collapsed."
        )

        world.global_events.append(f"T{turn}: {event_msg}")

        event = NotableEvent(
            turn=turn,
            event_type=EventType.GLOBAL_SCENARIO,
            actors=[],
            summary=event_msg,
            relevance_to=None  # Global
        )
        context_manager.global_events.append(event)

        return [f"🦠 [SCENARIO DETECTED] Pandemic Triggered! {total_deaths:,} dead. Global yields halved, trust dropped, armies weakened."]
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
    
    # Compute world averages first — used both for candidate filtering and final target value.
    land_provinces = [p for p in world.provinces.values() if p.owner_id is not None]
    if land_provinces:
        avg_energy = sum(p.energy_production for p in land_provinces) / len(land_provinces)
        avg_materials = sum(p.materials_production for p in land_provinces) / len(land_provinces)
    else:
        avg_energy, avg_materials = 10.0, 10.0

    # 1. Identify border provinces in four tiers (progressively relaxed filters).
    # Tier 1 (ideal): border between peaceful nations + below-avg production + NOT top power nation.
    # Tier 2: any border province + below-avg production + NOT top power nation.
    # Tier 3: any border province + NOT top power nation.
    # Tier 4: any border province (last resort — guarantees the scenario can always fire).
    tier1, tier2, tier3, tier4 = [], [], [], []

    # Identify the strongest nation to avoid giving them even more resources
    active_nations = [n for n in world.nations.values() if n.is_active]
    top_power_id = max(active_nations, key=lambda n: n.power_projection).id if active_nations else None

    for p_id, province in world.provinces.items():
        if province.owner_id is None:
            continue

        border_neighbor_ids = []
        for neighbor_id in province.neighbors:
            neighbor = world.provinces.get(neighbor_id)
            if neighbor and neighbor.owner_id and neighbor.owner_id != province.owner_id:
                border_neighbor_ids.append(neighbor.owner_id)

        if not border_neighbor_ids:
            continue  # Not a border province at all

        is_underexploited = (
            province.energy_production < avg_energy
            and province.materials_production < avg_materials
        )

        # Check if any bordering nation is at peace with the province owner
        has_peaceful_border = any(
            world.relationship_matrix.get(province.owner_id, {}).get(n_id, "PEACE") != "WAR"
            for n_id in border_neighbor_ids
        )

        tier4.append(province)

        if province.owner_id != top_power_id:
            tier3.append(province)
            if is_underexploited:
                tier2.append(province)
                if has_peaceful_border:
                    tier1.append(province)

    # Pick from the best available tier
    candidates = tier1 or tier2 or tier3 or tier4

    if not candidates:
        return ["⚠️ [SCENARIO FAILED] No border provinces found to trigger discovery."]

    # 2. Pick one deterministically
    target = rng.choice(candidates)
    owner = world.nations.get(target.owner_id)
    owner_name = owner.name if owner else "Unknown"

    # 3. Set production to 10x the world average — a truly significant economic event.
    target.energy_production = avg_energy * 50.0
    target.materials_production = avg_materials * 50.0
    
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
    
    # 1. Find Motherland using a composite score:
    # A candidate must be both large (many provinces) and unstable (low satisfaction).
    # Scoring formula: S = (1 - norm_satisfaction) * 0.5 + norm_province_count * 0.5
    # This prevents targeting small, moribund nations that generate no interesting dynamics.
    nations_with_provinces = [n for n in world.nations.values() if len(n.province_ids) > 1]
    if not nations_with_provinces:
        return {"logs": ["⚠️ [SCENARIO FAILED] No nation found with enough provinces to rebel."]}

    max_sat = max(n.public_satisfaction for n in nations_with_provinces) or 1.0
    max_provs = max(len(n.province_ids) for n in nations_with_provinces) or 1

    def insurrection_score(n):
        # Normalize each metric to [0, 1] and combine with equal weights
        norm_instability = (max_sat - n.public_satisfaction) / max_sat
        norm_size = len(n.province_ids) / max_provs
        return 0.5 * norm_instability + 0.5 * norm_size

    motherland = max(nations_with_provinces, key=insurrection_score)

    
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
    # Initialize the matrices for the new nation, including the self-entry (diagonal)
    world.trust_matrix[rebel_id] = {rebel_id: 100.0}
    world.relationship_matrix[rebel_id] = {rebel_id: "SELF"}
    
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
    
    return {
        "logs": logs,
        "new_nation": {
            "id": rebel_id,
            "strategy": rebel_strategy,
            "government_type": rebel_gov
        }
    }

def trigger_regime_change(world: WorldState, context_manager: ContextManager, turn: int, trigger: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes the Regime Change scenario.
    - Forces a nation to immediately adopt a new GovernmentType and GlobalStrategy.
    - Broadcasts a neutral global event.
    - Injects a private event for the new administration.
    """
    from geomas.agents.context.events.schemas import EventType, NotableEvent
    from geomas.agents.schemas.protocol import GovernmentType
    from geomas.agents.schemas import GlobalStrategy
    
    target_id = trigger.get("target_id")
    raw_gov = trigger.get("new_gov")
    raw_strat = trigger.get("new_strategy")
    
    if not target_id or target_id not in world.nations:
        return {"logs": ["⚠️ [SCENARIO FAILED] Target nation for Regime Change is invalid or missing."]}
        
    nation = world.nations[target_id]
    
    # Parse Enums
    try:
        new_gov = GovernmentType(raw_gov)
        new_strat = GlobalStrategy(raw_strat)
    except ValueError as e:
        return {"logs": [f"⚠️ [SCENARIO FAILED] Invalid ENUM for Regime Change: {e}"]}
        
    # Update NationState Backend
    nation.government_type = new_gov.value
    
    # 1. Neutral Global Notification
    global_msg = f"🏛️ [GLOBAL EVENT] A new government has been formed in {nation.name}. The transition of political power is complete."
    world.global_events.append(f"T{turn}: {global_msg}")
    
    global_event = NotableEvent(
        turn=turn,
        event_type=EventType.GLOBAL_SCENARIO,
        actors=[target_id],
        summary=global_msg,
        relevance_to=None  # Global
    )
    context_manager.global_events.append(global_event)
    
    # 2. Private Ideological Directive
    private_msg = f"⚖️ [REGIME CHANGE] The government of {nation.name} has changed. You are the newly installed administration. Your new Government type is {new_gov.value} and your new Global Strategy is {new_strat.value}. Act exclusively according to these new parameters."
    private_event = NotableEvent(
        turn=turn,
        event_type=EventType.REGIME_CHANGE,
        actors=[target_id],
        summary=private_msg,
        relevance_to=[target_id]  # Private
    )
    context_manager.global_events.append(private_event)
    
    logs = [f"⚖️ [SCENARIO DETECTED] Regime Change in {nation.name}. Now {new_gov.value} / {new_strat.value}."]
    
    # Instruct the Engine to call NationAgent.change_regime
    return {
        "logs": logs,
        "modified_nation": {
            "id": target_id,
            "strategy": new_strat,
            "government_type": new_gov
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
    elif s_type == "REGIME_CHANGE" or s_type == "CAMBIO GOVERNO":
        return trigger_regime_change(world, context_manager, current_turn, scenario_trigger)
        
    return {"logs": []}
